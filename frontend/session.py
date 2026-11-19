"""
frontend/session.py - Machine d'état du simulateur de projecteur (Membre 2).

Fait avancer le cycle, suit la fatigue (jumeau du Membre 1) et déclenche les mutations :
  1. auto     : un pic de fatigue est prévu au-dessus du seuil dans les 30 s à venir ;
  2. mode     : passage au mode ProjFlow-AI (et retour au protocole fixe, immédiat lui aussi).
Une mutation réordonne les étapes restantes (DAG respecté) et fait tourner les angles
d'approche de 15 à 30°, sans toucher au protocole (mêmes tâches, cibles et précédences).
"""

from __future__ import annotations

import time
from bisect import bisect_right
from typing import Dict, List, Optional

from frontend.adapter import SOURCES, protocol_fingerprint, wrist_deviation_deg

LOOKAHEAD_SEC = 30.0


class ProjectorSession:
    def __init__(self, source_key: str = "m1", ai: bool = True, threshold_pct: float = 75.0, src=None) -> None:
        self.source_key = source_key
        self.src = src if src is not None else SOURCES[source_key]()  # l'IHM partage une source mise en cache
        self.ai = ai
        self.threshold_pct = threshold_pct
        self.reset()

    # ------------------------------------------------------------------ cycle
    def reset(self) -> None:
        self.batch_no = 1
        self.events: List[dict] = []
        self.pending_anim: Optional[dict] = None
        self.protocol_initial = self.src.zero_fatigue()
        self.batch_initial = dict(self.protocol_initial)
        self._start_batch()

    def _start_batch(self) -> None:
        self.elapsed = 0.0
        self.mutations_in_batch = 0
        self.protocol = self.src.protocol_order()
        self.ghost_angles = self.src.default_angles()
        self.protocol_curve = self.src.fatigue_curve(self.protocol, self.protocol_initial)
        if self.ai and self.batch_no > 1:
            order = self.src.ai_batch_order(self.batch_no)
            angles = self.src.mutated_angles(order, self.batch_no, self.ghost_angles)
            self.mutated = True
            self._set_plan(order, angles)
            self.curve = self.src.fatigue_curve(order, self.batch_initial, mutated=True)
            self._log("lot", f"Nouveau lot n°{self.batch_no} : séquence polymorphe (seed {self.batch_no})",
                      self.ghost_angles, angles, order, self.protocol)
        else:
            self.mutated = False
            self._set_plan(self.protocol, dict(self.ghost_angles))
            self.curve = self.src.fatigue_curve(self.protocol, self.batch_initial)
            if self.batch_no > 1:
                self.events.insert(0, self._event("lot", f"Nouveau lot n°{self.batch_no} : protocole fixe standard"))
        self.curve_t0 = 0.0
        self.fingerprint_ref = self.fingerprint()

    def _set_plan(self, order: List[str], angles: Dict[str, float]) -> None:
        self.order = list(order)
        self.angles = dict(angles)
        self.starts, t = [], 0.0
        for i in self.order:
            self.starts.append(t)
            t += self.src.duration(i)
        self.total = t

    def index(self) -> int:
        return max(0, min(len(self.order) - 1, bisect_right(self.starts, self.elapsed) - 1))

    def done_ids(self) -> List[str]:
        return self.order[: self.index()]

    def step_remaining(self) -> float:
        i = self.index()
        return self.starts[i] + self.src.duration(self.order[i]) - self.elapsed

    def tick(self, dt: float) -> None:
        self.elapsed += max(0.0, dt)
        if self.elapsed >= self.total:
            self._finish_batch()
            return
        self._check_auto()

    def _finish_batch(self) -> None:
        """Clôt le lot : la fatigue résiduelle (réelle et protocole) est transmise au lot suivant."""
        self.protocol_initial = self._row(self.protocol_curve, self.protocol_curve["time_sec"].iloc[-1])
        self.batch_initial = self._row(self.curve, self.curve["time_sec"].iloc[-1])
        self.batch_no += 1
        self._start_batch()

    def next_batch(self) -> None:
        """Bouton « Simuler le lot suivant » : le reste du lot en cours est exécuté d'un coup
        par le jumeau de fatigue, puis un nouvel ordre de fabrication démarre."""
        self._finish_batch()

    def set_ai(self, ai: bool) -> None:
        """Bascule avant/après, effective tout de suite sur les étapes restantes du lot."""
        if ai == self.ai:
            return
        self.ai = ai
        if ai:
            self.trigger_mutation("Mode ProjFlow-AI activé : guidage subconscient", kind="mode")
            return
        i = self.index()
        current, done = self.order[i], self.order[:i]
        rest = [x for x in self.protocol if x not in set(done) | {current}]
        old_angles, old_order = dict(self.angles), list(self.order)
        remaining_cur, initial = self.step_remaining(), self.fatigue_now()
        new_angles = dict(self.angles)
        for k in [current] + rest:
            new_angles[k] = self.ghost_angles[k]
        self._set_plan(done + [current] + rest, new_angles)
        self.mutated = False
        self.curve = self.src.fatigue_curve([current] + rest, initial, first_remaining=remaining_cur)
        self.curve_t0 = self.elapsed
        self._log("mode", "Retour au protocole fixe standard", old_angles, new_angles, self.order, old_order, from_index=i)

    # ---------------------------------------------------------------- fatigue
    @staticmethod
    def _row(df, t: float) -> Dict[str, float]:
        times = df["time_sec"].tolist()
        k = max(0, min(len(times) - 1, bisect_right(times, t) - 1))
        r = df.iloc[k]
        return {c[: -len("_fatigue")]: float(r[c]) for c in df.columns if c.endswith("_fatigue")}

    def fatigue_now(self) -> Dict[str, float]:
        return self._row(self.curve, self.elapsed - self.curve_t0)

    def protocol_now(self) -> Dict[str, float]:
        return self._row(self.protocol_curve, self.elapsed)

    def pct(self, values: Dict[str, float]) -> Dict[str, float]:
        return {j: self.src.pct(j, v) for j, v in values.items()}

    def _predicted_peak(self) -> tuple:
        t0 = self.elapsed - self.curve_t0
        win = self.curve[(self.curve["time_sec"] >= t0) & (self.curve["time_sec"] <= t0 + LOOKAHEAD_SEC)]
        best = (None, 0.0)
        for j, _ in self.src.joints:
            if win.empty:
                continue
            v = self.src.pct(j, float(win[f"{j}_fatigue"].max()))
            if v > best[1]:
                best = (j, v)
        return best

    # -------------------------------------------------------------- triggers
    def _check_auto(self) -> None:
        if not self.ai or self.mutated:
            return
        joint, v = self._predicted_peak()
        if joint and v >= self.threshold_pct:
            label = dict(self.src.joints)[joint]
            self.trigger_mutation(f"Pic prévu {label} {v:.0f} % ≥ seuil {self.threshold_pct:.0f} % (fenêtre {LOOKAHEAD_SEC:.0f} s)", kind="auto")

    def trigger_mutation(self, reason: str, kind: str = "auto", seed: Optional[int] = None) -> Optional[dict]:
        i = self.index()
        current = self.order[i]
        done = self.order[:i]
        seed = int(seed) if seed is not None else self.batch_no * 100 + len(self.events) + 1
        rest = self.src.replan(done + [current], current, seed)
        new_order = done + [current] + rest
        ok, msg = self.src.validate(new_order)
        if not ok:
            self.events.insert(0, self._event("refusé", f"Mutation rejetée par le contrôleur IATF : {msg}"))
            return None
        remaining_cur = self.step_remaining()
        initial = self.fatigue_now()
        old_angles, old_order = dict(self.angles), list(self.order)
        # same parity for every mutation of a batch: repeated mutations re-order steps but do not
        # flip centred trajectories from +15° to -15° (that swing was the "jumping path" glitch)
        parity = self.batch_no
        new_angles = self.src.mutated_angles([current] + rest, parity, self.angles)
        self._set_plan(new_order, new_angles)
        self.mutated = True
        self.mutations_in_batch += 1
        self.curve = self.src.fatigue_curve([current] + rest, initial, first_remaining=remaining_cur, mutated=True)
        self.curve_t0 = self.elapsed
        ev = self._log(kind, reason, old_angles, new_angles, new_order, old_order, from_index=i)
        return ev

    # --------------------------------------------------------------- logging
    def _event(self, kind: str, text: str, **extra) -> dict:
        return {"id": len(self.events) + 1, "kind": kind, "text": text, "batch": self.batch_no,
                "t": round(self.elapsed, 1), "wall": time.strftime("%H:%M:%S"), **extra}

    def _log(self, kind, reason, old_angles, new_angles, new_order, old_order, from_index: int = 0) -> dict:
        ids = new_order[from_index:]
        deltas = [new_angles[k] - old_angles[k] for k in ids if abs(new_angles[k] - old_angles[k]) > 0.05]
        dev_before = [wrist_deviation_deg(old_angles[k], self.src.forearm(k)) for k in ids]
        dev_after = [wrist_deviation_deg(new_angles[k], self.src.forearm(k)) for k in ids]
        reordered = sum(1 for a, b in zip(new_order, old_order) if a != b)
        ok, msg = self.src.validate(new_order)
        ev = self._event(
            kind, reason,
            reordered=reordered,
            rotated=len(deltas),
            mean_rotation=round(sum(abs(d) for d in deltas) / len(deltas), 1) if deltas else 0.0,
            dev_before=round(sum(dev_before) / len(dev_before), 1) if ids else 0.0,
            dev_after=round(sum(dev_after) / len(dev_after), 1) if ids else 0.0,
            iatf_ok=ok, iatf_msg=msg,
            fingerprint_ok=self.fingerprint() == getattr(self, "fingerprint_ref", self.fingerprint()),
        )
        self.events.insert(0, ev)
        self.pending_anim = {"event": ev["id"], "from": old_angles, "to": dict(new_angles)}
        return ev

    # ------------------------------------------------------------------ views
    def fingerprint(self) -> str:
        return protocol_fingerprint(self.src.steps(self.order, self.angles), self.src.edges())

    def snapshot(self, playing: bool, speed: float) -> dict:
        """Données envoyées au composant navigateur. Ne change qu'aux événements (mutation, lot,
        pause, vitesse) : entre deux événements, le navigateur anime seul le cycle à 60 i/s."""
        steps = self.src.steps(self.order, self.angles)
        lay = self.src.layout
        joints = [j for j, _ in self.src.joints]

        def series(df, t_end):
            out = {j: [] for j in joints}
            for t in range(0, int(t_end) + 2):
                row = self._row(df, float(t))
                for j in joints:
                    out[j].append(round(self.src.pct(j, row[j]), 1))
            return out

        ok, msg = self.src.validate(self.order)
        pos = {x: n for n, x in enumerate(self.order)}
        edges = self.src.edges()
        edges_ok = sum(1 for u, v in edges if pos[u] < pos[v])
        locked = self.src.locked_ids()
        locked_ok = sum(1 for x in locked if pos[x] == self.protocol.index(x))
        anim = self.pending_anim["from"] if self.pending_anim else None
        self.pending_anim = None
        return {
            "layout": {"w": lay.width, "d": lay.depth, "op": list(lay.operator), "name": lay.name,
                       "zones": [{"label": z.label, "x0": z.x0, "y0": z.y0, "x1": z.x1, "y1": z.y1} for z in lay.zones]},
            "steps": [{"id": st.component_id, "short": self.src.short(st.component_id), "name": st.component_name,
                       "macro": st.macro_phase, "macroName": st.macro_phase_name, "color": st.spatial.projection_color_hex,
                       "x": st.spatial.x, "y": st.spatial.y, "dur": st.estimated_duration_sec, "joint": st.target_joint,
                       "angle": st.spatial.approach_angle_deg, "ghost": round(self.ghost_angles[st.component_id], 1),
                       "locked": self.src.is_locked(st.component_id)}
                      for st in steps],
            "protocol": list(self.protocol),
            "macroCount": len({st.macro_phase for st in steps}),
            "starts": [round(x, 3) for x in self.starts],
            "total": self.total, "takt": self.src.takt,
            "elapsed": round(self.elapsed, 3), "playing": playing, "speed": speed,
            "batch": self.batch_no, "ai": self.ai, "mutated": self.mutated, "threshold": self.threshold_pct,
            "joints": [{"key": j, "label": lbl} for j, lbl in self.src.joints],
            "fatigue": {"t0": round(self.curve_t0, 3), "live": series(self.curve, self.total - self.curve_t0),
                        "proto": series(self.protocol_curve, self.total)},
            "anim": anim,
            "iatf": {"ok": ok, "msg": msg, "fp": self.fingerprint(), "ref": self.fingerprint_ref,
                     "edges": len(edges), "edgesOk": edges_ok, "locked": len(locked), "lockedOk": locked_ok},
            "shift": self.src.shift_comparison(),
            "events": [{k: v for k, v in e.items()} for e in self.events[:5]],
            "source": self.src.title,
        }
