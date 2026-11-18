"""
Contrat de données standardisé pour ProjFlow-AI (Poste LEONI 3.2).
Définit les classes d'échange entre :
- Membre 1 (Moteur IA / DAG / Fatigue)
- Membre 2 (IHM Streamlit / Projecteur Zénithal)
- Membre 3 (Pipeline & Datasets)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import json

@dataclass
class SpatialCoordinates:
    x: float
    y: float
    projection_color_hex: str
    approach_angle_deg: float

@dataclass
class ProjectedStep:
    step_index: int
    component_id: str
    component_name: str
    macro_phase: int
    macro_phase_name: str
    spatial: SpatialCoordinates
    estimated_duration_sec: float
    force_newton: float
    target_joint: str

@dataclass
class JointFatigueState:
    wrist_flexion_pct: float
    wrist_pronation_pct: float
    shoulder_elevation_pct: float
    elbow_extension_pct: float
    is_critical: bool = False
    critical_joint: Optional[str] = None

@dataclass
class AIOrchestrationPayload:
    """
    Objet principal émis par le backend (M1) et consommé directement par l'IHM (M2).
    """
    batch_id: str
    batch_name: str
    is_ai_mutated: bool
    iatf_protocol_validated: bool
    total_cycle_time_sec: float
    takt_time_target_sec: float
    fatigue_before_lot: JointFatigueState
    fatigue_after_lot: JointFatigueState
    projected_sequence: List[ProjectedStep]
    ai_mutation_summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'AIOrchestrationPayload':
        data = data.copy()
        data['fatigue_before_lot'] = JointFatigueState(**data['fatigue_before_lot'])
        data['fatigue_after_lot'] = JointFatigueState(**data['fatigue_after_lot'])
        data['projected_sequence'] = [
            ProjectedStep(
                step_index=s['step_index'],
                component_id=s['component_id'],
                component_name=s['component_name'],
                macro_phase=s['macro_phase'],
                macro_phase_name=s['macro_phase_name'],
                spatial=SpatialCoordinates(**s['spatial']),
                estimated_duration_sec=s['estimated_duration_sec'],
                force_newton=s['force_newton'],
                target_joint=s['target_joint']
            )
            for s in data['projected_sequence']
        ]
        return cls(**data)
