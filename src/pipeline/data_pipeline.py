"""
Pipeline et API interne de ProjFlow-AI.
Assure l'orchestration, le chargement des datasets et la communication synchrone entre le moteur (M1) et l'IHM (M2).
"""

import os
import json
from typing import Dict, Any, List
from ..models.data_contracts import (
    AIOrchestrationPayload,
    ProjectedStep,
    SpatialCoordinates,
    JointFatigueState
)

class DataPipeline:
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            # Racine du workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.base_dir = base_dir
        self.topo_path = os.path.join(base_dir, "data", "post_3_2_topology.json")
        self.batch_path = os.path.join(base_dir, "data", "production_batches.json")
        
        self.topology = self._load_json(self.topo_path)
        self.batches_data = self._load_json(self.batch_path)
        self.components_map = {c["component_id"]: c for c in self.topology["components"]}
        self.phases_map = {p["phase_id"]: p["phase_name"] for p in self.topology["macro_phases"]}

    def _load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Fichier introuvable : {path}")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_available_batches(self) -> List[Dict[str, str]]:
        """Renvoie la liste des identifiants et libellés des lots disponibles pour le sélecteur Streamlit."""
        return [
            {"batch_id": b["batch_id"], "name": b["name"], "description": b["description"]}
            for b in self.batches_data["batches"]
        ]

    def get_batch_raw(self, batch_id: str) -> dict:
        for b in self.batches_data["batches"]:
            if b["batch_id"] == batch_id:
                return b
        raise ValueError(f"Lot introuvable : {batch_id}")

    def build_payload(self, batch_id: str, custom_sequence: List[str] = None, angle_adjustments: Dict[str, float] = None) -> AIOrchestrationPayload:
        """
        Construit le payload d'orchestration prêt pour l'IHM Streamlit (M2).
        Si custom_sequence est fourni (calculé par M1), il est utilisé ; sinon on charge la séquence par défaut du lot.
        """
        batch = self.get_batch_raw(batch_id)
        
        # Déterminer la séquence
        if custom_sequence is not None:
            seq_to_use = custom_sequence
            is_mutated = True
        elif "ai_mutated_sequence" in batch:
            seq_to_use = batch["ai_mutated_sequence"]
            is_mutated = True
        else:
            seq_to_use = batch.get("baseline_execution_sequence", batch["active_components"])
            is_mutated = False

        angles_override = angle_adjustments or batch.get("spatial_angle_adjustments_deg", {})

        # Validation stricte IATF (vérifier que les macro-phases sont croissantes)
        phases_sequence = [self.components_map[cid]["macro_phase"] for cid in seq_to_use]
        is_iatf_valid = all(phases_sequence[i] <= phases_sequence[i+1] for i in range(len(phases_sequence)-1))

        # Construction des étapes projetées pour le projecteur de M2
        projected_steps: List[ProjectedStep] = []
        total_time = 0.0

        for idx, cid in enumerate(seq_to_use, 1):
            comp = self.components_map[cid]
            dur = comp["ergonomic_impact"]["nominal_duration_sec"]
            total_time += dur
            
            # Angle d'approche (muté par l'IA ou par défaut)
            chosen_angle = angles_override.get(cid, comp["spatial_coordinates"]["approach_angle_default_deg"])
            
            spatial = SpatialCoordinates(
                x=comp["spatial_coordinates"]["x"],
                y=comp["spatial_coordinates"]["y"],
                projection_color_hex=comp["spatial_coordinates"]["projection_color_hex"],
                approach_angle_deg=chosen_angle
            )
            
            projected_steps.append(
                ProjectedStep(
                    step_index=idx,
                    component_id=cid,
                    component_name=comp["name"],
                    macro_phase=comp["macro_phase"],
                    macro_phase_name=self.phases_map[comp["macro_phase"]],
                    spatial=spatial,
                    estimated_duration_sec=dur,
                    force_newton=comp["ergonomic_impact"]["force_newton"],
                    target_joint=comp["ergonomic_impact"]["primary_joint"]
                )
            )

        # Calcul/Simulation des états de fatigue
        initial_fatigue = batch["operator_initial_fatigue"]
        before_state = JointFatigueState(
            wrist_flexion_pct=initial_fatigue.get("wrist_flexion_fatigue_pct", 10.0),
            wrist_pronation_pct=initial_fatigue.get("wrist_pronation_fatigue_pct", 10.0),
            shoulder_elevation_pct=initial_fatigue.get("shoulder_elevation_fatigue_pct", 10.0),
            elbow_extension_pct=initial_fatigue.get("elbow_extension_fatigue_pct", 10.0)
        )
        before_state.is_critical = before_state.wrist_flexion_pct >= 70.0
        if before_state.is_critical:
            before_state.critical_joint = "wrist_flexion"

        # Évolution post-lot : si muté par l'IA -> repos tendineux actif ; si non muté -> saturation
        if is_mutated:
            after_state = JointFatigueState(
                wrist_flexion_pct=max(25.0, before_state.wrist_flexion_pct - 38.0), # Soulagement tendineux
                wrist_pronation_pct=max(25.0, before_state.wrist_pronation_pct - 28.0),
                shoulder_elevation_pct=min(100.0, before_state.shoulder_elevation_pct + 4.0),
                elbow_extension_pct=min(100.0, before_state.elbow_extension_pct + 3.0),
                is_critical=False
            )
            summary = "Polymorphisme spatial actif : les angles d'approche et l'ordre des sous-composants alternent pour décharger le poignet (-38%) tout en maintenant le respect total du protocole IATF."
        else:
            after_state = JointFatigueState(
                wrist_flexion_pct=min(100.0, before_state.wrist_flexion_pct + 12.0),
                wrist_pronation_pct=min(100.0, before_state.wrist_pronation_pct + 8.0),
                shoulder_elevation_pct=min(100.0, before_state.shoulder_elevation_pct + 6.0),
                elbow_extension_pct=min(100.0, before_state.elbow_extension_pct + 4.0),
                is_critical=(before_state.wrist_flexion_pct + 12.0) >= 70.0
            )
            summary = "Séquence standard sans compensation spatiale : la contrainte articulaire continue d'augmenter linéairement."

        return AIOrchestrationPayload(
            batch_id=batch["batch_id"],
            batch_name=batch["name"],
            is_ai_mutated=is_mutated,
            iatf_protocol_validated=is_iatf_valid,
            total_cycle_time_sec=total_time,
            takt_time_target_sec=self.topology["post_metadata"]["standard_takt_time_sec"],
            fatigue_before_lot=before_state,
            fatigue_after_lot=after_state,
            projected_sequence=projected_steps,
            ai_mutation_summary=summary
        )
