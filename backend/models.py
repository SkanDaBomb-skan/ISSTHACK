"""
backend/models.py - Modélisation des données fondamentales (Micro-étape 1.1)

Conforme au Cahier des Charges SSTHack 2026 (Track 3 - Poste LEONI 3.2, Page 5) :
- Zones corporelles réelles : Épaules, coudes, poignets, mains et doigts.
- Tâches réelles : Encliquetage des cosses, raccordement sur gabarit, enrubannage.
- Takt time : 276 s.
- Norme d'évaluation (Exigence M3) : Index OCRA / RULA pour membres supérieurs répétitifs.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any


class TaskCategory(Enum):
    """
    Catégories d'opérations manuelles extraites textuellement du cahier des charges (p.5).
    Permet à l'IA d'alterner les natures de sollicitations physiques.
    """
    CLICK_IN_TERMINALS = "Encliqueter les cosses dans les connecteurs (tâche la plus pénible)"
    ROUTING_COMPONENTS = "Raccorder les composants sur le gabarit"
    TAPING_HARNESS     = "Enrubanner le faisceau"
    SECONDARY_LOCK     = "Verrouillage de sécurité CPA (Norme IATF 16949)"


@dataclass
class BiomechanicalStrain:
    """
    Contrainte biomécanique instantanée sur les 4 zones corporelles réelles
    déclarées dans le cahier des charges (Track 3 - Poste 3.2, p.5) :
    
    1. shoulders     : Épaules (Pathologie : tendinite des deux épaules, douleurs H.A. en fin de journée).
                       Facteur : Bras levé ou étiré vers le fond de table (y > 70 cm).
    2. elbows        : Coudes (Pathologie : épicondylite).
                       Facteur : Torsion répétée et prono-supination lors de l'enrubannage.
    3. wrists        : Poignets (Pathologie : syndrome du canal carpien).
                       Facteur : Flexion/déviation du poignet sous contrainte.
    4. hands_fingers : Mains et doigts (Pathologie : tendinites des doigts).
                       Facteur : Force d'insertion axiale et pincement dur ("pinch grip") sur les cosses.
    
    Échelle normalisée : de 0.0 (repos complet) à 10.0 (effort maximal admissible).
    """
    shoulders: float
    elbows: float
    wrists: float
    hands_fingers: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "shoulders": self.shoulders,
            "elbows": self.elbows,
            "wrists": self.wrists,
            "hands_fingers": self.hands_fingers
        }

    def compute_instant_ocra_risk(self) -> float:
        """
        Calcul d'un indice instantané inspiré de la méthode OCRA (Exigence M3, ISO 11228-3).
        Pondère la force et l'amplitude articulaire pour détecter les situations à risque critique.
        """
        # Le canal carpien et les doigts sont les plus à risque lors de l'insertion
        weighted_risk = (
            self.shoulders * 0.25 +
            self.elbows * 0.20 +
            self.wrists * 0.25 +
            self.hands_fingers * 0.30
        )
        return round(weighted_risk, 2)


@dataclass
class SpatialCoordinates:
    """
    Coordonnées spatiales de la tâche sur l'établi LEONI (200 cm de large x 100 cm de profondeur).
    
    Utilisation :
      Transmis au Membre 2 (Frontend) pour que la simulation du projecteur zénithal
      illumine le bon emplacement sur le gabarit au bon moment.
      
    Repère :
      - x (0 à 200 cm) : Largeur (0 = gauche/moteur, 100 = centre, 200 = droite/habitacle).
      - y (0 à 100 cm) : Profondeur (0 = bord proche de l'opérateur, 100 = fond de table).
      - zone_label     : Description textuelle de la zone pour l'opérateur.
    """
    x: float
    y: float
    zone_label: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "zone_label": self.zone_label
        }


@dataclass
class AssemblyTask:
    """
    Tâche unitaire d'assemblage du faisceau de 430 fils (Poste 3.2).
    
    Champs :
      - id : Identifiant unique (ex: 'M2_ENCLIQ_FUSIBLE_01').
      - name : Libellé clair de l'opération.
      - macro_step_id : Numéro de la macro-étape imposée par le protocole IATF (1, 2, 3, 4).
      - macro_step_name : Nom de la macro-étape.
      - duration_sec : Durée unitaire en secondes (la somme de toutes les tâches = 276.0 s).
      - coords : Position physique pour le projecteur.
      - strain : Profil de contrainte sur les 4 zones TMS du cahier des charges.
      - category : Nature du travail (Enum TaskCategory).
      - quality_critical : Si True, position chronologique strictement inchangeable.
      - dependencies : Liste des IDs de tâches qui doivent impérativement précéder celle-ci.
    """
    id: str
    name: str
    macro_step_id: int
    macro_step_name: str
    duration_sec: float
    coords: SpatialCoordinates
    strain: BiomechanicalStrain
    category: TaskCategory
    quality_critical: bool = False
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "macro_step_id": self.macro_step_id,
            "macro_step_name": self.macro_step_name,
            "duration_sec": self.duration_sec,
            "coords": self.coords.to_dict(),
            "strain": self.strain.to_dict(),
            "category": self.category.value,
            "quality_critical": self.quality_critical,
            "dependencies": self.dependencies
        }
