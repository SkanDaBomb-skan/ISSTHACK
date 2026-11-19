"""
frontend/adapter.py - Adaptateurs backend -> contrat de données (Membre 2).

Le simulateur affiche toujours des `ProjectedStep` (contrat de src/models/data_contracts.py).
Deux sources savent les produire :

  * Member1Source : moteur live du Membre 1 (21 tâches, DAG NetworkX, optimiseur,
                    jumeau de fatigue). C'est la source par défaut.
  * Member3Source : rejeu des lots scénarisés du Membre 3 (DataPipeline / topologie).

Repère de rendu commun (celui de la topologie du Membre 3) :
  x, y en mm ; l'opérateur est sur le bord BAS de l'établi ; y croît vers l'opérateur.

Convention d'angle d'approche (déduite de post_3_2_topology.json) :
  degrés dans le repère écran (y vers le bas), vecteur partant de la cible vers la main ;
  90° = main qui arrive tout droit depuis l'opérateur.
"""

from __future__ import annotations

import hashlib
import math
import os
import random
import sys
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Sequence, Tuple

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.fatigue_twin import BiomechanicalFatigueTwin  # noqa: E402
from backend.graph_engine import AssemblyGraphEngine  # noqa: E402
from backend.leoni_data import TAKT_TIME_NOMINAL_SEC, get_leoni_reference_tasks  # noqa: E402
from backend.optimizer import AssemblySequenceOptimizer  # noqa: E402
from src.models.data_contracts import ProjectedStep, SpatialCoordinates  # noqa: E402
from src.pipeline.data_pipeline import DataPipeline  # noqa: E402

DEFAULT_APPROACH_DEG = 90.0
MIN_ROTATION_DEG = 15.0
MAX_ROTATION_DEG = 30.0

MACRO_COLORS = {1: "#60A5FA", 2: "#F59E0B", 3: "#A78BFA", 4: "#F472B6"}


@dataclass
class Zone:
    label: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class BenchLayout:
    name: str
    width: float
    depth: float
    operator: Tuple[float, float]
    zones: List[Zone]


def forearm_axis_deg(x: float, y: float, operator: Tuple[float, float]) -> float:
    """Direction cible -> épaule de l'opérateur (repère écran, y vers le bas)."""
    return math.degrees(math.atan2(operator[1] - y, operator[0] - x))


def rotated_angle(default: float, forearm: float, parity: int) -> float:
    """Angle muté : on tourne de 15 à 30° vers l'axe de l'avant-bras.

    Si la cible est déjà dans l'axe (|écart| < 15°), on alterne ±15° d'un lot à l'autre
    (variation motrice : on ne sollicite pas toujours le même tendon).
    """
    diff = forearm - default
    if abs(diff) < MIN_ROTATION_DEG:
        sign = 1.0 if parity % 2 else -1.0
        return default + sign * MIN_ROTATION_DEG
    return default + math.copysign(min(max(abs(diff), MIN_ROTATION_DEG), MAX_ROTATION_DEG), diff)


def wrist_deviation_deg(approach: float, forearm: float) -> float:
    d = abs(approach - forearm) % 360
    return min(d, 360 - d)


def protocol_fingerprint(steps: Sequence[ProjectedStep], edges: Sequence[Tuple[str, str]]) -> str:
    """Empreinte du protocole qualité : quelles tâches, à quelles cibles, dans quelle macro-phase,
    avec quels arcs de précédence. Volontairement indépendante de l'ORDRE et des ANGLES :
    une mutation IA doit laisser cette empreinte inchangée."""
    parts = sorted(f"{s.component_id}@{s.spatial.x:.0f},{s.spatial.y:.0f}@P{s.macro_phase}" for s in steps)
    parts += sorted(f"{u}>{v}" for u, v in edges)
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]


class Member1Source:
    """Moteur live du Membre 1 converti vers le contrat ProjectedStep."""

    key = "m1"
    title = "Moteur IA Membre 1 (live)"
    joints = [("wrists", "Poignets"), ("hands_fingers", "Mains & doigts"), ("elbows", "Coudes"), ("shoulders", "Épaules")]
    SHIFT_BATCHES = 5

    def __init__(self) -> None:
        self.tasks = get_leoni_reference_tasks()
        self.engine = AssemblyGraphEngine(self.tasks)
        self.optimizer = AssemblySequenceOptimizer(self.engine)
        self.twin = BiomechanicalFatigueTwin()
        self.by_id = {t.id: t for t in self.tasks}
        self.takt = TAKT_TIME_NOMINAL_SEC
        self.layout = BenchLayout(
            name="LEONI Workstation 3.2 · établi 2000 × 1000 mm",
            width=2000.0,
            depth=1000.0,
            operator=(1000.0, 1000.0),
            zones=self._zones(),
        )
        base = self.protocol_order()
        df = self.twin.simulate_sequence([self.by_id[i] for i in base])
        # 100 % = pic atteint par le protocole fixe sur un cycle, opérateur reposé
        self.ref_peak = {j: float(df[f"{j}_fatigue"].max()) for j, _ in self.joints}

    # -- géométrie ---------------------------------------------------------------
    def xy(self, task_id: str) -> Tuple[float, float]:
        c = self.by_id[task_id].coords
        return c.x * 10.0, (100.0 - c.y) * 10.0

    def _zones(self) -> List[Zone]:
        groups: Dict[str, List[Tuple[float, float]]] = {}
        for t in self.tasks:
            groups.setdefault(t.coords.zone_label, []).append(self.xy(t.id))
        pad = 70.0
        zones = []
        for label, pts in groups.items():
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            zones.append(Zone(label, max(0, min(xs) - pad), max(0, min(ys) - pad), min(2000, max(xs) + pad), min(1000, max(ys) + pad)))
        return zones

    def forearm(self, task_id: str) -> float:
        return forearm_axis_deg(*self.xy(task_id), self.layout.operator)

    # -- séquences ---------------------------------------------------------------
    def protocol_order(self) -> List[str]:
        return [t.id for t in self.optimizer.generate_baseline_sequence()]

    def ai_batch_order(self, batch_no: int) -> List[str]:
        return [t.id for t in self.optimizer.generate_ergonomic_sequence(seed=batch_no)]

    def replan(self, done_ids: Sequence[str], last_id: Optional[str], seed: int) -> List[str]:
        """Même boucle que generate_ergonomic_sequence, mais depuis un état partiellement réalisé."""
        completed = set(done_ids)
        rng = random.Random(seed)
        last = self.by_id[last_id] if last_id else None
        out: List[str] = []
        while len(completed) < len(self.tasks):
            available = self.engine.get_available_tasks(completed)
            if not available:
                raise RuntimeError("Blocage du graphe : aucune tâche candidate.")
            if len(available) == 1:
                chosen = available[0]
            else:
                scored = sorted(((self.optimizer._compute_transition_cost(last, c), i, c) for i, c in enumerate(available)), key=lambda s: (s[0], s[1]))
                chosen = rng.choice([s[2] for s in scored[:2]])
            out.append(chosen.id)
            completed.add(chosen.id)
            last = chosen
        return out

    def validate(self, order: Sequence[str]) -> Tuple[bool, str]:
        ok, msg = self.engine.validate_sequence(list(order))
        return ok, msg or ""


    def edges(self) -> List[Tuple[str, str]]:
        return list(self.engine.graph.edges())

    def locked_ids(self) -> List[str]:
        return [t.id for t in self.tasks if t.quality_critical]

    def shift_comparison(self) -> dict:
        """Avant/après sur un shift : compare_shift du Membre 1 (protocole répété vs lots polymorphes,
        fatigue résiduelle transmise d'un lot à l'autre). Valeurs en % du pic du protocole fixe."""
        if getattr(self, "_shift", None) is None:
            base = self.optimizer.generate_baseline_sequence()
            poly = [self.optimizer.generate_ergonomic_sequence(seed=i) for i in range(1, self.SHIFT_BATCHES + 1)]
            res = self.twin.compare_shift(base, poly)
            rows = []
            for j, label in self.joints:
                c = res["comparison"][j]
                rows.append({"key": j, "label": label,
                             "before": round(self.pct(j, c["baseline_residual"]), 1), "after": round(self.pct(j, c["polymorphic_residual"]), 1),
                             "gain": c["residual_gain_pct"], "peakGain": c["peak_gain_pct"]})
            self._shift = {"title": f"Shift de {self.SHIFT_BATCHES} lots ({res['total_shift_duration_sec'] / 60:.0f} min) · jumeau de fatigue Membre 1",
                           "metric": "Fatigue résiduelle en fin de shift (% du pic du protocole fixe)", "rows": rows}
        return self._shift

    # -- angles ------------------------------------------------------------------
    def default_angles(self) -> Dict[str, float]:
        return {i: DEFAULT_APPROACH_DEG for i in self.by_id}

    def mutated_angles(self, ids: Sequence[str], parity: int, base: Dict[str, float]) -> Dict[str, float]:
        out = dict(base)
        for i in ids:
            out[i] = rotated_angle(DEFAULT_APPROACH_DEG, self.forearm(i), parity)
        return out

    # -- contrat -----------------------------------------------------------------
    def steps(self, order: Sequence[str], angles: Dict[str, float]) -> List[ProjectedStep]:
        res = []
        for n, i in enumerate(order, 1):
            t = self.by_id[i]
            x, y = self.xy(i)
            strain = t.strain.to_dict()
            res.append(ProjectedStep(
                step_index=n,
                component_id=i,
                component_name=t.name,
                macro_phase=t.macro_step_id,
                macro_phase_name=t.macro_step_name,
                spatial=SpatialCoordinates(x=x, y=y, projection_color_hex=MACRO_COLORS[t.macro_step_id], approach_angle_deg=round(angles[i], 1)),
                estimated_duration_sec=t.duration_sec,
                force_newton=round(strain["hands_fingers"] * 4.0, 1),  # estimation : le dataset M1 ne donne pas la force
                target_joint=max(strain, key=strain.get),
            ))
        return res

    def is_locked(self, task_id: str) -> bool:
        """quality_critical = position chronologique inchangeable (dataset du Membre 1)."""
        return bool(self.by_id[task_id].quality_critical)

    def short(self, task_id: str) -> str:
        return task_id.split("_", 1)[1].replace("CONN_", "").replace("TAPE_", "T·").replace("_", " ")

    def duration(self, task_id: str) -> float:
        return self.by_id[task_id].duration_sec

    # -- fatigue -----------------------------------------------------------------
    def fatigue_curve(self, order: Sequence[str], initial: Dict[str, float], first_remaining: Optional[float] = None, mutated: bool = False) -> pd.DataFrame:
        """Courbe seconde par seconde (jumeau du Membre 1). `first_remaining` raccourcit la 1re tâche (tâche en cours)."""
        seq = [self.by_id[i] for i in order]
        if seq and first_remaining is not None:
            seq[0] = replace(seq[0], duration_sec=max(0.5, first_remaining))
        if not seq:
            return pd.DataFrame([{"time_sec": 0.0, **{f"{j}_fatigue": initial[j] for j, _ in self.joints}}])
        df = self.twin.simulate_sequence(seq, initial_fatigue=dict(initial))
        start = pd.DataFrame([{"time_sec": 0.0, **{f"{j}_fatigue": initial[j] for j, _ in self.joints}}])
        return pd.concat([start, df[["time_sec"] + [f"{j}_fatigue" for j, _ in self.joints]]], ignore_index=True)

    def zero_fatigue(self) -> Dict[str, float]:
        return {j: 0.0 for j, _ in self.joints}

    def pct(self, joint: str, value: float) -> float:
        return 100.0 * value / self.ref_peak[joint]


class Member3Source:
    """Rejeu des lots du Membre 3 : lot 2 (saturation, protocole) -> lot 3 (mutation IA)."""

    key = "m3"
    title = "Lots scénarisés Membre 3 (rejeu)"
    joints = [("shoulder_elevation", "Élévation épaule"), ("elbow_extension", "Extension coude"),
              ("wrist_flexion", "Flexion poignet"), ("wrist_pronation", "Pronation poignet")]
    BASE_BATCH = "BATCH_002_PEAK_SATURATION"
    AI_BATCH = "BATCH_003_AI_OPTIMIZED_RECOVERY"

    def __init__(self) -> None:
        self.pipeline = DataPipeline()
        meta = self.pipeline.topology["post_metadata"]
        self.takt = float(meta["standard_takt_time_sec"])
        op = meta["operator_position"]
        dims = meta["bench_dimensions_mm"]
        self.comp = self.pipeline.components_map
        self.layout = BenchLayout(
            name=f"LEONI Workstation 3.2 · établi {dims['width']} × {dims['height']} mm (topologie M3)",
            width=float(dims["width"]),
            depth=float(dims["height"]),
            operator=(float(op["x"]), float(op["y"])),
            zones=self._zones(),
        )
        self.ai_raw = self.pipeline.get_batch_raw(self.AI_BATCH)
        self.base_payload = self.pipeline.build_payload(self.BASE_BATCH)
        self.ai_payload = self.pipeline.build_payload(self.BASE_BATCH, custom_sequence=self.ai_raw["ai_mutated_sequence"],
                                                      angle_adjustments=self.ai_raw["spatial_angle_adjustments_deg"])
        self.ref_peak = {j: 100.0 for j, _ in self.joints}

    def _zones(self) -> List[Zone]:
        zones = []
        for ph in self.pipeline.topology["macro_phases"]:
            pts = [(c["spatial_coordinates"]["x"], c["spatial_coordinates"]["y"]) for c in self.comp.values() if c["macro_phase"] == ph["phase_id"]]
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            zones.append(Zone(ph["phase_name"].split(":")[0].strip(), min(xs) - 50, min(ys) - 50, max(xs) + 50, max(ys) + 50))
        return zones

    def xy(self, cid: str) -> Tuple[float, float]:
        s = self.comp[cid]["spatial_coordinates"]
        return float(s["x"]), float(s["y"])

    def forearm(self, cid: str) -> float:
        return forearm_axis_deg(*self.xy(cid), self.layout.operator)

    def protocol_order(self) -> List[str]:
        return list(self.pipeline.get_batch_raw(self.BASE_BATCH)["baseline_execution_sequence"])

    def ai_batch_order(self, batch_no: int) -> List[str]:
        return list(self.ai_raw["ai_mutated_sequence"])

    def replan(self, done_ids: Sequence[str], last_id: Optional[str], seed: int) -> List[str]:
        done = set(done_ids)
        return [c for c in self.ai_raw["ai_mutated_sequence"] if c not in done]

    def validate(self, order: Sequence[str]) -> Tuple[bool, str]:
        phases = [self.comp[c]["macro_phase"] for c in order]
        ok = len(set(order)) == len(self.comp) and all(a <= b for a, b in zip(phases, phases[1:]))
        return ok, "Macro-phases IATF dans l'ordre" if ok else "Ordre des macro-phases IATF violé"


    def edges(self) -> List[Tuple[str, str]]:
        return []

    def locked_ids(self) -> List[str]:
        return []

    def shift_comparison(self) -> dict:
        b, a = self.base_payload.fatigue_after_lot, self.ai_payload.fatigue_after_lot
        rows = []
        for j, label in self.joints:
            before, after = float(getattr(b, f"{j}_pct")), float(getattr(a, f"{j}_pct"))
            rows.append({"key": j, "label": label, "before": before, "after": after,
                         "gain": round(100 * (before - after) / before, 1) if before else 0.0, "peakGain": None})
        return {"title": "Lot 2 (protocole) vs lot 3 (mutation IA) · pipeline Membre 3",
                "metric": "Fatigue en fin de lot (%)", "rows": rows}

    def default_angles(self) -> Dict[str, float]:
        return {c: float(v["spatial_coordinates"]["approach_angle_default_deg"]) for c, v in self.comp.items()}

    def mutated_angles(self, ids: Sequence[str], parity: int, base: Dict[str, float]) -> Dict[str, float]:
        out = dict(base)
        for c, a in self.ai_raw["spatial_angle_adjustments_deg"].items():
            if c in ids:
                out[c] = float(a)
        return out

    def steps(self, order: Sequence[str], angles: Dict[str, float]) -> List[ProjectedStep]:
        p = self.pipeline.build_payload(self.BASE_BATCH, custom_sequence=list(order), angle_adjustments=angles)
        return p.projected_sequence

    def is_locked(self, cid: str) -> bool:
        return False  # topologie M3 : liberté à l'intérieur de la macro-phase, macro-phases en ordre strict

    def short(self, cid: str) -> str:
        return cid.replace("COMP_", "")

    def duration(self, cid: str) -> float:
        return float(self.comp[cid]["ergonomic_impact"]["nominal_duration_sec"])

    def zero_fatigue(self) -> Dict[str, float]:
        f = self.base_payload.fatigue_before_lot
        return {j: float(getattr(f, f"{j}_pct")) for j, _ in self.joints}

    def fatigue_curve(self, order: Sequence[str], initial: Dict[str, float], first_remaining: Optional[float] = None, mutated: bool = False) -> pd.DataFrame:
        """Interpolation linéaire vers l'état post-lot calculé par le pipeline du Membre 3."""
        total = sum(self.duration(c) for c in order)
        if first_remaining is not None and order:
            total -= self.duration(order[0]) - first_remaining
        after = (self.ai_payload if mutated else self.base_payload).fatigue_after_lot
        target = {j: float(getattr(after, f"{j}_pct")) for j, _ in self.joints}
        n = max(1, int(round(total)))
        rows = [{"time_sec": float(k), **{f"{j}_fatigue": initial[j] + (target[j] - initial[j]) * k / n for j, _ in self.joints}} for k in range(n + 1)]
        return pd.DataFrame(rows)

    def pct(self, joint: str, value: float) -> float:
        return value


SOURCES = {"m1": Member1Source, "m3": Member3Source}
