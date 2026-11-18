"""
backend/leoni_data.py - Modélisation des tâches réelles du Poste LEONI 3.2 (Micro-étape 1.2)

Conforme au Cahier des Charges SSTHack 2026 (Track 3, p.5) :
- Faisceau de 430 fils.
- Takt time nominal imposé par le tapis : 276.0 secondes.
- 4 zones ciblées : Épaules, Coudes, Poignets, Mains & Doigts.
- Tâches : Raccordement composants gabarit, Encliquetage cosses (tâche la plus pénible), Enrubannage.
"""

from typing import List
from backend.models import (
    AssemblyTask,
    SpatialCoordinates,
    BiomechanicalStrain,
    TaskCategory
)

# Takt time imposé par le tapis roulant (Page 5 du cahier des charges)
TAKT_TIME_NOMINAL_SEC = 276.0


def get_leoni_reference_tasks() -> List[AssemblyTask]:
    """
    Retourne l'ensemble des 21 tâches opérationnelles du Poste 3.2 de LEONI.
    La somme totale des durées est rigoureusement égale à 276.0 secondes.
    """
    tasks: List[AssemblyTask] = []

    # =========================================================================
    # MACRO-ÉTAPE 1 : Raccordement composants sur le gabarit & Bridage maître (45.0 s)
    # Tâche Cahier des charges : "Raccorder les composants sur le gabarit"
    # Protocole IATF : Le tronc principal DOIT être bridé avant d'insérer les cosses.
    # =========================================================================
    tasks.append(AssemblyTask(
        id="M1_FETCH_MAIN",
        name="Prélèvement faisceau brut (Bac supérieur)",
        macro_step_id=1,
        macro_step_name="1. Raccordement gabarit & Bridage",
        duration_sec=8.0,
        coords=SpatialCoordinates(x=100.0, y=95.0, zone_label="Bac supérieur étagère"),
        # Bras levé en hauteur -> forte sollicitation de l'épaule (douleurs H.A.)
        strain=BiomechanicalStrain(shoulders=8.5, elbows=4.0, wrists=3.5, hands_fingers=3.0),
        category=TaskCategory.ROUTING_COMPONENTS,
        quality_critical=True,
        dependencies=[]
    ))

    tasks.append(AssemblyTask(
        id="M1_LAY_TRUNK_LEFT",
        name="Cheminement branche moteur sur gabarit (Zone Gauche)",
        macro_step_id=1,
        macro_step_name="1. Raccordement gabarit & Bridage",
        duration_sec=10.0,
        coords=SpatialCoordinates(x=35.0, y=50.0, zone_label="Gabarit Moteur Gauche"),
        strain=BiomechanicalStrain(shoulders=5.0, elbows=4.5, wrists=4.0, hands_fingers=3.5),
        category=TaskCategory.ROUTING_COMPONENTS,
        quality_critical=False,
        dependencies=["M1_FETCH_MAIN"]
    ))

    tasks.append(AssemblyTask(
        id="M1_LAY_TRUNK_RIGHT",
        name="Cheminement branche habitacle sur gabarit (Zone Droite)",
        macro_step_id=1,
        macro_step_name="1. Raccordement gabarit & Bridage",
        duration_sec=10.0,
        coords=SpatialCoordinates(x=165.0, y=50.0, zone_label="Gabarit Habitacle Droit"),
        strain=BiomechanicalStrain(shoulders=5.0, elbows=4.5, wrists=4.0, hands_fingers=3.5),
        category=TaskCategory.ROUTING_COMPONENTS,
        quality_critical=False,
        dependencies=["M1_FETCH_MAIN"]
    ))

    tasks.append(AssemblyTask(
        id="M1_CLAMP_PRIMARY",
        name="Enclenchement des 4 brides maîtresses du gabarit",
        macro_step_id=1,
        macro_step_name="1. Raccordement gabarit & Bridage",
        duration_sec=17.0,
        coords=SpatialCoordinates(x=100.0, y=40.0, zone_label="Axe central gabarit"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=5.5, wrists=6.5, hands_fingers=6.0),
        category=TaskCategory.ROUTING_COMPONENTS,
        quality_critical=True, # Verrouillage obligatoire de fin de Macro 1
        dependencies=["M1_LAY_TRUNK_LEFT", "M1_LAY_TRUNK_RIGHT"]
    ))

    # =========================================================================
    # MACRO-ÉTAPE 2 : Encliquetage des cosses dans les connecteurs (110.0 s)
    # Tâche Cahier des charges : "Encliqueter les cosses dans les connecteurs (tâche la plus pénible)"
    # Sollicitation : Pression axiale très dure au pouce (Canal carpien & Doigts)
    # =========================================================================
    
    # --- Branche 1 : Compartiment Moteur (Zone Gauche) ---
    tasks.append(AssemblyTask(
        id="M2_CONN_ENG_01",
        name="Encliquetage cosses Connecteur Alternateur (2 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=11.0,
        coords=SpatialCoordinates(x=25.0, y=60.0, zone_label="Compartiment Moteur"),
        strain=BiomechanicalStrain(shoulders=4.5, elbows=5.0, wrists=8.5, hands_fingers=9.0),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_ENG_02",
        name="Encliquetage cosses Capteur Pression (3 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=11.0,
        coords=SpatialCoordinates(x=40.0, y=75.0, zone_label="Compartiment Moteur"),
        # Fond de table (y=75) -> épaule plus sollicitée
        strain=BiomechanicalStrain(shoulders=6.5, elbows=5.0, wrists=8.0, hands_fingers=8.5),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_ENG_03",
        name="Encliquetage cosse Démarreur de puissance (1 voie forte section)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=10.0,
        coords=SpatialCoordinates(x=20.0, y=35.0, zone_label="Compartiment Moteur"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=6.0, wrists=8.5, hands_fingers=9.0),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    # --- Branche 2 : Boîte Fusibles Centrale (Fond de table -> Épaules en tension) ---
    tasks.append(AssemblyTask(
        id="M2_CONN_FUSE_01",
        name="Encliquetage boîtier fusible primaire A (6 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=90.0, y=85.0, zone_label="Boîte Fusibles Centrale"),
        strain=BiomechanicalStrain(shoulders=7.5, elbows=5.5, wrists=9.0, hands_fingers=9.5),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_FUSE_02",
        name="Encliquetage boîtier fusible primaire B (6 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=110.0, y=85.0, zone_label="Boîte Fusibles Centrale"),
        strain=BiomechanicalStrain(shoulders=7.5, elbows=5.5, wrists=9.0, hands_fingers=9.5),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_FUSE_03",
        name="Encliquetage relais principal injection (4 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=100.0, y=60.0, zone_label="Boîte Fusibles Centrale"),
        strain=BiomechanicalStrain(shoulders=5.5, elbows=4.5, wrists=8.5, hands_fingers=8.5),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    # --- Branche 3 : Faisceau Habitacle (Zone Droite) ---
    tasks.append(AssemblyTask(
        id="M2_CONN_CAB_01",
        name="Encliquetage connecteur combiné bord (18 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=14.0,
        coords=SpatialCoordinates(x=160.0, y=40.0, zone_label="Faisceau Habitacle"),
        strain=BiomechanicalStrain(shoulders=4.0, elbows=6.0, wrists=9.0, hands_fingers=9.0),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_CAB_02",
        name="Encliquetage commande climatisation (8 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=175.0, y=65.0, zone_label="Faisceau Habitacle"),
        strain=BiomechanicalStrain(shoulders=6.0, elbows=5.0, wrists=8.5, hands_fingers=8.5),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    tasks.append(AssemblyTask(
        id="M2_CONN_CAB_03",
        name="Encliquetage connecteur portière droite (12 voies)",
        macro_step_id=2,
        macro_step_name="2. Encliquetage des cosses",
        duration_sec=16.0,
        coords=SpatialCoordinates(x=185.0, y=30.0, zone_label="Faisceau Habitacle"),
        strain=BiomechanicalStrain(shoulders=3.0, elbows=5.5, wrists=8.0, hands_fingers=8.0),
        category=TaskCategory.CLICK_IN_TERMINALS,
        dependencies=["M1_CLAMP_PRIMARY"]
    ))

    # =========================================================================
    # MACRO-ÉTAPE 3 : Enrubannage du faisceau (65.0 s)
    # Tâche Cahier des charges : "Enrubanner le faisceau"
    # Sollicitation : Torsion rapide et continue des coudes (épicondylite) et poignets.
    # Repos actif pour les doigts (pas d'effort de poussée axiale).
    # =========================================================================
    tasks.append(AssemblyTask(
        id="M3_TAPE_NODE_LEFT",
        name="Enrubannage dérivation branche moteur gauche",
        macro_step_id=3,
        macro_step_name="3. Enrubannage du faisceau",
        duration_sec=16.0,
        coords=SpatialCoordinates(x=35.0, y=45.0, zone_label="Gabarit Moteur Gauche"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=8.0, wrists=7.5, hands_fingers=4.0),
        category=TaskCategory.TAPING_HARNESS,
        # Dépend uniquement des connecteurs moteur gauche
        dependencies=["M2_CONN_ENG_01", "M2_CONN_ENG_02", "M2_CONN_ENG_03"]
    ))

    tasks.append(AssemblyTask(
        id="M3_TAPE_NODE_CENTER",
        name="Enrubannage sortie boîte à fusibles centrale",
        macro_step_id=3,
        macro_step_name="3. Enrubannage du faisceau",
        duration_sec=18.0,
        coords=SpatialCoordinates(x=100.0, y=55.0, zone_label="Boîte Fusibles Centrale"),
        strain=BiomechanicalStrain(shoulders=5.0, elbows=8.5, wrists=8.0, hands_fingers=4.5),
        category=TaskCategory.TAPING_HARNESS,
        dependencies=["M2_CONN_FUSE_01", "M2_CONN_FUSE_02", "M2_CONN_FUSE_03"]
    ))

    tasks.append(AssemblyTask(
        id="M3_TAPE_NODE_RIGHT",
        name="Enrubannage dérivation branche habitacle droite",
        macro_step_id=3,
        macro_step_name="3. Enrubannage du faisceau",
        duration_sec=16.0,
        coords=SpatialCoordinates(x=160.0, y=45.0, zone_label="Faisceau Habitacle"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=8.0, wrists=7.5, hands_fingers=4.0),
        category=TaskCategory.TAPING_HARNESS,
        dependencies=["M2_CONN_CAB_01", "M2_CONN_CAB_02", "M2_CONN_CAB_03"]
    ))

    tasks.append(AssemblyTask(
        id="M3_TAPE_PROTECT_TRUNK",
        name="Enrubannage feutrine acoustique sur tronc central",
        macro_step_id=3,
        macro_step_name="3. Enrubannage du faisceau",
        duration_sec=15.0,
        coords=SpatialCoordinates(x=120.0, y=35.0, zone_label="Axe central gabarit"),
        strain=BiomechanicalStrain(shoulders=3.0, elbows=6.5, wrists=6.5, hands_fingers=3.5),
        category=TaskCategory.TAPING_HARNESS,
        dependencies=["M3_TAPE_NODE_LEFT", "M3_TAPE_NODE_CENTER", "M3_TAPE_NODE_RIGHT"]
    ))

    # =========================================================================
    # MACRO-ÉTAPE 4 : Verrouillages de sécurité CPA & Clips gabarit (56.0 s)
    # Norme IATF : Sécurisation finale des connecteurs avant libération du tapis.
    # Sollicitation : Effort léger à modéré sur le bord proche de l'opérateur.
    # =========================================================================
    tasks.append(AssemblyTask(
        id="M4_CPA_ENG",
        name="Verrouillage secondaire CPA connecteurs moteur",
        macro_step_id=4,
        macro_step_name="4. Sécurité CPA & Clips",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=30.0, y=50.0, zone_label="Compartiment Moteur"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=4.0, wrists=6.5, hands_fingers=6.0),
        category=TaskCategory.SECONDARY_LOCK,
        dependencies=["M3_TAPE_NODE_LEFT"]
    ))

    tasks.append(AssemblyTask(
        id="M4_CPA_FUSE",
        name="Verrouillage secondaire CPA boîte à fusibles",
        macro_step_id=4,
        macro_step_name="4. Sécurité CPA & Clips",
        duration_sec=14.0,
        coords=SpatialCoordinates(x=100.0, y=70.0, zone_label="Boîte Fusibles Centrale"),
        strain=BiomechanicalStrain(shoulders=6.0, elbows=4.5, wrists=7.0, hands_fingers=6.5),
        category=TaskCategory.SECONDARY_LOCK,
        dependencies=["M3_TAPE_NODE_CENTER"]
    ))

    tasks.append(AssemblyTask(
        id="M4_CPA_CAB",
        name="Verrouillage secondaire CPA connecteurs habitacle",
        macro_step_id=4,
        macro_step_name="4. Sécurité CPA & Clips",
        duration_sec=12.0,
        coords=SpatialCoordinates(x=170.0, y=40.0, zone_label="Faisceau Habitacle"),
        strain=BiomechanicalStrain(shoulders=3.5, elbows=4.0, wrists=6.5, hands_fingers=6.0),
        category=TaskCategory.SECONDARY_LOCK,
        dependencies=["M3_TAPE_NODE_RIGHT"]
    ))

    tasks.append(AssemblyTask(
        id="M4_MOUNT_CLIPS_FINAL",
        name="Pose finale des 5 clips de carrosserie sur gabarit",
        macro_step_id=4,
        macro_step_name="4. Sécurité CPA & Clips",
        duration_sec=18.0,
        coords=SpatialCoordinates(x=100.0, y=20.0, zone_label="Bord proche opérateur"),
        strain=BiomechanicalStrain(shoulders=2.0, elbows=4.5, wrists=5.5, hands_fingers=5.0),
        category=TaskCategory.ROUTING_COMPONENTS,
        quality_critical=True, # Dernière étape du takt time
        dependencies=["M4_CPA_ENG", "M4_CPA_FUSE", "M4_CPA_CAB", "M3_TAPE_PROTECT_TRUNK"]
    ))

    return tasks
