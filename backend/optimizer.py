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
          2. Calculer un coût de transition biomécanique pour chaque tâche candidate en intégrant :
             - La règle maîtresse IATF 16949 : la phase M4 (CPA et clips) ne démarre que quand tout le rubanage M3 est achevé.
             - Le repos actif intercalé : dès qu'une branche est insérée, le rubanage M3 est favorisé pour reposer les doigts.
             - Les pénalités d'accumulation consécutive sur une même articulation (épaules, coudes, poignets, doigts).
             - Le bonus spatial de mobilité posturale.
          3. Valider formellement la séquence finale via le contrôleur de précédence du DAG.
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
                    cost = self._compute_transition_cost(last_task, cand, completed_ids)
                    scored_candidates.append((cost, cand))

                # Trier par coût croissant (le plus petit coût = le meilleur choix ergonomique)
                scored_candidates.sort(key=lambda item: item[0])

                # Pour maintenir une variabilité motrice saine d'un lot à l'autre sans dégrader l'ergonomie,
                # on choisit parmi les 2 meilleures options dans un intervalle serré
                min_cost = scored_candidates[0][0]
                best_pool = [item[1] for item in scored_candidates if item[0] <= min_cost + 3.0]
                chosen = rng.choice(best_pool[:2])

            sequence.append(chosen)
            completed_ids.add(chosen.id)
            last_task = chosen

        # 3. Contrôle de sécurité qualité absolu (IATF 16949)
        is_valid, msg = self.engine.validate_sequence([t.id for t in sequence])
        if not is_valid:
            raise ValueError(f"Erreur interne d'optimisation : {msg}")

        return sequence

    def _compute_transition_cost(
        self,
        prev: Optional[AssemblyTask],
        cand: AssemblyTask,
        completed_ids: Optional[Set[str]] = None
    ) -> float:
        """
        Fonction de coût biomécanique multi-articulaire & contraintes IATF :
        Évalue la pertinence de passer de 'prev' à 'cand'.
        """
        cost = 0.0

        # Règle 0 : Qualité IATF 16949 & Cooldown Physiologique Final (Évite tout transfert de risque vers les coudes)
        # La phase M4 (sécurité CPA et clips carrosserie) ne doit JAMAIS démarrer tant que tout le rubanage M3 n'est pas terminé.
        if cand.id.startswith("M4") and completed_ids is not None:
            pending_m3 = any(tid.startswith("M3") and tid not in completed_ids for tid in self.tasks_dict)
            if pending_m3:
                return 50000.0  # Verrouillage strict : interdiction de clipser avant d'avoir rubanné !
            if cand.id == "M4_CPA_FUSE":
                cost -= 20.0  # Prioriser le connecteur fusible en début de M4 pour laisser les épaules récupérer ensuite

        # Règle 1 : Repos Actif Intercalé pour les Doigts (Canal carpien)
        # Dès qu'un nœud d'enrubannage M3 est libéré, l'intercaler offre un répit aux doigts (hf <= 4.5)
        # et brise la chaîne d'écrasement continu des 9 connecteurs M2.
        if cand.id.startswith("M3") and cand.id != "M3_TAPE_PROTECT_TRUNK":
            if prev and prev.strain.hands_fingers >= 8.0:
                cost -= 25.0  # Bonus de repos actif immédiat

        if prev is None:
            return cost

        # Règle 2 : Prévention Épaules / Coiffe des rotateurs (Douleurs H.A.)
        # Pénalise l'enchaînement de tâches à forte tension d'épaule ou en fond de gabarit (y >= 70 cm)
        if prev.strain.shoulders >= 6.5 and cand.strain.shoulders >= 6.5:
            cost += 35.0
        if prev.coords.y >= 70.0 and cand.coords.y >= 70.0:
            cost += 25.0

        # Règle 3 : Prévention Canal Carpien & Pression Axiale des Doigts
        # Interdire 2 insertions dures consécutives au pouce (strain >= 8.5)
        if prev.strain.hands_fingers >= 8.5 and cand.strain.hands_fingers >= 8.5:
            cost += 30.0

        # Règle 4 : Prévention Épicondylite (Torsion coude lors du rubanage)
        # Interdire 2 rubanages consécutifs pour éviter la surchauffe tendineuse du coude
        if prev.strain.elbows >= 7.5 and cand.strain.elbows >= 7.5:
            cost += 35.0

        # Règle 5 : Prévention Poignets (Flexions / Déviations extrêmes)
        if prev.strain.wrists >= 8.5 and cand.strain.wrists >= 8.5:
            cost += 20.0

        # Règle 6 : Mobilité posturale dynamique (Alternance spatiale gauche / centre / droite)
        # Quand l'opératrice change de zone sur le gabarit (|delta_x| >= 45 cm), son buste change d'angle
        dx = abs(prev.coords.x - cand.coords.x)
        if dx >= 45.0:
            cost -= 8.0

        return cost
