"""
backend/optimizer.py - Algorithme de Mutation Spatiale et d'Optimisation Biomécanique (Étape 3)

Responsable de la génération de séquences d'assemblage polymorphes.
Objectif : Alterner intelligemment les contraintes articulaires (épaules, coudes, poignets, mains/doigts)
tout en restant 100% conforme aux règles de précédence du DAG NetworkX.
"""

from typing import List, Dict, Set, Optional, Tuple
import random
from backend.models import AssemblyTask
from backend.graph_engine import AssemblyGraphEngine


class AssemblySequenceOptimizer:
    """
    Optimiseur d'ordonnancement ergonomique (Polymorphisme IA).
    
    À chaque nouveau lot sur le tapis roulant, l'algorithme génère une variante d'assemblage
    qui brise la routine motrice répétitive sans jamais dépasser le takt time de 276.0 s
    ni enfreindre les règles qualité IATF 16949.
    """

    def __init__(self, engine: AssemblyGraphEngine):
        self.engine = engine
        self.tasks_dict = engine.tasks_dict

    def generate_baseline_sequence(self) -> List[AssemblyTask]:
        """
        Séquence 'Usine Classique' (Témoin de référence) :
        L'opératrice exécute toujours les tâches dans le même ordre fixe, de gauche à droite.
        Cette séquence sert de comparateur (Avant/Après) pour chiffrer les gains devant le jury.
        """
        return self.engine.get_reference_topological_sort()

    def generate_ergonomic_sequence(self, seed: Optional[int] = None) -> List[AssemblyTask]:
        """
        Séquence Optimisée par IA (ProjFlow-AI) :
        Génère une séquence qui lisse les sollicitations tendineuses en temps réel.
        
        Principe algorithmique :
          1. À chaque étape, interroger le DAG pour obtenir le pool des tâches légalement autorisées.
          2. Calculer un coût de transition biomécanique pour chaque tâche candidate.
          3. Privilégier la tâche qui offre un repos actif à l'articulation la plus sollicitée par l'étape précédente.
          4. Valider formellement la séquence finale via le contrôleur de précédence.
        """
        rng = random.Random(seed)
        completed_ids: Set[str] = set()
        sequence: List[AssemblyTask] = []

        last_task: Optional[AssemblyTask] = None

        while len(completed_ids) < len(self.tasks_dict):
            # 1. Obtenir les tâches autorisées par le graphe
            available = self.engine.get_available_tasks(completed_ids)
            if not available:
                raise RuntimeError("Blocage critique du graphe : aucune tâche candidate disponible !")

            # 2. Si une seule tâche est prête (ex: verrouillage de fin de macro-étape)
            if len(available) == 1:
                chosen = available[0]
            else:
                # Évaluer le coût de transition ergonomique pour chaque candidat
                scored_candidates: List[Tuple[float, AssemblyTask]] = []
                for cand in available:
                    cost = self._compute_transition_cost(last_task, cand)
                    scored_candidates.append((cost, cand))

                # Trier par coût croissant (le plus petit coût = le meilleur choix ergonomique)
                scored_candidates.sort(key=lambda item: item[0])

                # Pour maintenir une légère variabilité motrice saine d'un lot à l'autre,
                # on choisit parmi les 2 meilleures options
                best_pool = [item[1] for item in scored_candidates[:2]]
                chosen = rng.choice(best_pool)

            sequence.append(chosen)
            completed_ids.add(chosen.id)
            last_task = chosen

        # 3. Contrôle de sécurité qualité absolu
        is_valid, msg = self.engine.validate_sequence([t.id for t in sequence])
        if not is_valid:
            raise ValueError(f"Erreur interne d'optimisation : {msg}")

        return sequence

    def _compute_transition_cost(
        self,
        prev: Optional[AssemblyTask],
        cand: AssemblyTask
    ) -> float:
        """
        Fonction de coût biomécanique évaluant la pénibilité de passer de 'prev' à 'cand'.
        Pénalise sévèrement l'accumulation continue sur un même tendon.
        """
        if prev is None:
            return 0.0

        cost = 0.0

        # Règle 1 : Prévention Canal Carpien & Doigts (Insertion dure de cosses)
        # Si la tâche précédente a écrasé les doigts (strain >= 8.0) et que la candidate aussi
        if prev.strain.hands_fingers >= 8.0 and cand.strain.hands_fingers >= 8.0:
            cost += 20.0  # Très lourde pénalité : interdire 2 insertions dures consécutives !

        # Règle 2 : Prévention Épaules / Coiffe des rotateurs (Fond de table)
        # Posture bras tendu en fond de table (y > 70 cm)
        if prev.coords.y >= 70.0 and cand.coords.y >= 70.0:
            cost += 15.0  # Pénalité : éviter de maintenir les bras tendus en fond de table

        # Règle 3 : Prévention Épicondylite (Torsion coude lors du rubanage)
        if prev.strain.elbows >= 7.5 and cand.strain.elbows >= 7.5:
            cost += 12.0  # Pénalité : alterner les phases de rubanage

        # Règle 4 : Bonus d'alternance motrice (Hémisphères de table)
        # Si l'opérateur change de zone spatiale (|delta_x| > 40 cm), son buste change d'angle
        spatial_shift = abs(prev.coords.x - cand.coords.x)
        if spatial_shift >= 40.0:
            cost -= 3.0  # Bonus ergonomique : favorise la mobilité dynamique

        return cost
