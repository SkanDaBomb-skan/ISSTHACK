"""
backend/fatigue_twin.py - Jumeau Numérique de Fatigue Prédictive (Étape 4)

Conforme au Cahier des Charges SSTHack 2026 :
- Exigence M3 : Évaluation du risque selon la méthode normalisée OCRA (ISO 11228-3).
- Exigence M1 : Approche multisite (épaules, coudes, poignets, mains/doigts).
- Exigences D1 & D3 : Zéro capteur corporel, zéro caméra de flicage. Modélisation purement physique.
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np
import pandas as pd
from backend.models import AssemblyTask


class BiomechanicalFatigueTwin:
    """
    Jumeau numérique modélisant l'accumulation et la dissipation de la charge tendineuse.
    Fondé sur les équations physiologiques de Rohmert et l'index de contrainte répétitive OCRA.
    """

    def __init__(
        self,
        decay_shoulder: float = 0.055,  # Taux de relaxation épaule (demi-vie ~12s)
        decay_elbow: float = 0.065,     # Taux de relaxation coude (demi-vie ~10s)
        decay_wrist: float = 0.060,     # Taux de relaxation poignet (demi-vie ~11s)
        decay_hands: float = 0.070      # Taux de relaxation doigts/cosses (demi-vie ~10s)
    ):
        self.decay_rates = {
            "shoulders": decay_shoulder,
            "elbows": decay_elbow,
            "wrists": decay_wrist,
            "hands_fingers": decay_hands
        }

    def simulate_sequence(
        self,
        sequence: List[AssemblyTask],
        initial_fatigue: Optional[Dict[str, float]] = None,
        time_step_sec: float = 1.0
    ) -> pd.DataFrame:
        """
        Simule seconde par seconde l'évolution de la tension musculaire et tendineuse sur un cycle de 276 s.
        Génère un DataFrame pandas directement exploitable par le Membre 2 (IHM Streamlit).
        """
        if initial_fatigue is None:
            current_fatigue = {k: 0.0 for k in self.decay_rates}
        else:
            current_fatigue = initial_fatigue.copy()

        records = []
        current_time = 0.0

        for task in sequence:
            duration = task.duration_sec
            strain = task.strain

            steps = int(max(1, round(duration / time_step_sec)))
            dt = duration / steps

            for _ in range(steps):
                current_time += dt

                # Calcul pour chacune des 4 zones du cahier des charges
                for joint, decay in self.decay_rates.items():
                    raw_intensity = getattr(strain, joint)

                    # Modèle d'influx biomécanique :
                    # Au-delà de 7.5/10, l'effort d'insertion écrase le flux sanguin (ischémie)
                    # et l'accumulation de fatigue devient super-linéaire (Rohmert)
                    if raw_intensity >= 7.5:
                        influx_rate = (raw_intensity ** 2.2) / 10.0
                    elif raw_intensity >= 5.0:
                        influx_rate = raw_intensity * 0.8
                    else:
                        influx_rate = raw_intensity * 0.2  # Effort léger = quasi-repos

                    prev_f = current_fatigue[joint]
                    influx = influx_rate * dt
                    # Récupération viscoélastique naturelle du tendon
                    recovery = prev_f * (1.0 - math.exp(-decay * dt))

                    new_f = max(0.0, prev_f - recovery + influx)
                    current_fatigue[joint] = new_f

                # Calcul instantané de l'index OCRA
                instant_ocra = strain.compute_instant_ocra_risk()

                records.append({
                    "time_sec": round(current_time, 2),
                    "task_id": task.id,
                    "task_name": task.name,
                    "macro_step": task.macro_step_name,
                    "shoulders_fatigue": round(current_fatigue["shoulders"], 3),
                    "elbows_fatigue": round(current_fatigue["elbows"], 3),
                    "wrists_fatigue": round(current_fatigue["wrists"], 3),
                    "hands_fingers_fatigue": round(current_fatigue["hands_fingers"], 3),
                    "ocra_risk_score": instant_ocra
                })

        return pd.DataFrame(records)

    def evaluate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule les indicateurs clés de performance ergonomique (KPIs) :
          - Pic maximal de fatigue (seuil de douleur aiguë).
          - Charge cumulative globale (intégrale sous la courbe).
          - Fatigue résiduelle en fin de cycle.
        """
        metrics = {}
        for joint in self.decay_rates:
            col = f"{joint}_fatigue"
            metrics[joint] = {
                "peak_fatigue": round(float(df[col].max()), 2),
                "mean_fatigue": round(float(df[col].mean()), 2),
                "final_fatigue": round(float(df[col].iloc[-1]), 2),
                "cumulative_auc": round(float(df[col].sum()), 2)
            }
        metrics["total_time_sec"] = float(df["time_sec"].iloc[-1])
        return metrics

    def compare_shift(
        self,
        baseline_sequence: List[AssemblyTask],
        polymorphic_sequences: List[List[AssemblyTask]]
    ) -> Dict[str, Any]:
        """
        Simule un poste de travail continu (shift) composé de N cycles successifs (ex: 5 lots = 23 min).
        Compare la routine classique (Baseline répétée N fois) avec la mutation IA (N séquences polymorphes).
        """
        num_cycles = len(polymorphic_sequences)

        # 1. Simulation Baseline répétée N fois (la fatigue résiduelle d'un lot se transmet au suivant)
        df_base = self._run_continuous_shift([baseline_sequence] * num_cycles)

        # 2. Simulation Polymorphe ProjFlow-AI
        df_poly = self._run_continuous_shift(polymorphic_sequences)

        comparison = {}
        for joint in self.decay_rates:
            col = f"{joint}_fatigue"
            b_peak = float(df_base[col].max())
            p_peak = float(df_poly[col].max())
            peak_gain = ((b_peak - p_peak) / b_peak) * 100.0 if b_peak > 0 else 0.0

            b_final = float(df_base[col].iloc[-1])
            p_final = float(df_poly[col].iloc[-1])
            final_gain = ((b_final - p_final) / b_final) * 100.0 if b_final > 0 else 0.0

            b_auc = float(df_base[col].sum())
            p_auc = float(df_poly[col].sum())
            auc_gain = ((b_auc - p_auc) / b_auc) * 100.0 if b_auc > 0 else 0.0

            comparison[joint] = {
                "baseline_peak": round(b_peak, 2),
                "polymorphic_peak": round(p_peak, 2),
                "peak_gain_pct": round(peak_gain, 1),
                "baseline_residual": round(b_final, 2),
                "polymorphic_residual": round(p_final, 2),
                "residual_gain_pct": round(final_gain, 1),
                "baseline_auc": round(b_auc, 2),
                "polymorphic_auc": round(p_auc, 2),
                "auc_gain_pct": round(auc_gain, 1)
            }

        return {
            "num_cycles": num_cycles,
            "total_shift_duration_sec": float(df_base["shift_time_sec"].iloc[-1]),
            "comparison": comparison,
            "df_baseline": df_base,
            "df_polymorphic": df_poly
        }

    def _run_continuous_shift(self, sequences_list: List[List[AssemblyTask]]) -> pd.DataFrame:
        """Exécute une chaîne de cycles continus en conservant la fatigue résiduelle."""
        records = []
        current_time = 0.0
        current_fatigue = {k: 0.0 for k in self.decay_rates}

        for cycle_num, seq in enumerate(sequences_list, start=1):
            for task in seq:
                duration = task.duration_sec
                strain = task.strain

                steps = int(max(1, round(duration)))
                dt = duration / steps

                for _ in range(steps):
                    current_time += dt

                    for joint, decay in self.decay_rates.items():
                        raw_intensity = getattr(strain, joint)

                        if raw_intensity >= 7.5:
                            influx_rate = (raw_intensity ** 2.2) / 10.0
                        elif raw_intensity >= 5.0:
                            influx_rate = raw_intensity * 0.8
                        else:
                            influx_rate = raw_intensity * 0.2

                        prev_f = current_fatigue[joint]
                        influx = influx_rate * dt
                        recovery = prev_f * (1.0 - math.exp(-decay * dt))

                        new_f = max(0.0, prev_f - recovery + influx)
                        current_fatigue[joint] = new_f

                    records.append({
                        "shift_time_sec": round(current_time, 2),
                        "cycle_num": cycle_num,
                        "task_id": task.id,
                        "shoulders_fatigue": round(current_fatigue["shoulders"], 3),
                        "elbows_fatigue": round(current_fatigue["elbows"], 3),
                        "wrists_fatigue": round(current_fatigue["wrists"], 3),
                        "hands_fingers_fatigue": round(current_fatigue["hands_fingers"], 3)
                    })

        return pd.DataFrame(records)
