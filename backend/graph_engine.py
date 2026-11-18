"""
backend/graph_engine.py - Moteur de Graphes Orientés Acycliques (DAG) (Étape 2)

Utilise NetworkX pour formaliser mathématiquement les dépendances qualité IATF 16949.
Garantit qu'aucune séquence générée par l'IA ne peut violer l'ordre des opérations.
"""

from typing import List, Dict, Set, Tuple, Any, Optional
import networkx as nx
from backend.models import AssemblyTask


class AssemblyGraphEngine:
    """
    Moteur d'ordonnancement fondé sur la théorie des graphes.
    
    Représente le processus d'assemblage sous forme d'un DAG (Directed Acyclic Graph) :
      - Nœuds (Nodes) : Les 21 tâches d'assemblage (AssemblyTask).
      - Arcs orientés (Edges) : u -> v signifie 'La tâche u DOIT impérativement précéder v'.
    """

    def __init__(self, tasks: List[AssemblyTask]):
        self.tasks_dict: Dict[str, AssemblyTask] = {t.id: t for t in tasks}
        self.graph: nx.DiGraph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        """
        Construit le graphe orienté en injectant les métadonnées de chaque tâche
        et en créant les arcs de dépendance.
        """
        # 1. Ajout de tous les nœuds avec leurs propriétés
        for task in self.tasks_dict.values():
            self.graph.add_node(
                task.id,
                name=task.name,
                macro_step_id=task.macro_step_id,
                macro_step_name=task.macro_step_name,
                duration_sec=task.duration_sec,
                category=task.category.value,
                quality_critical=task.quality_critical,
                strain=task.strain.to_dict(),
                coords=task.coords.to_dict()
            )

        # 2. Ajout des arcs orientés u -> v à partir de task.dependencies
        # Si v dépend de u, alors u doit être terminée avant que v ne commence (arc u -> v)
        for task in self.tasks_dict.values():
            for dep_id in task.dependencies:
                if dep_id in self.tasks_dict:
                    self.graph.add_edge(dep_id, task.id)
                else:
                    raise ValueError(
                        f"Incohérence de données : la tâche '{task.id}' dépend d'un ID inexistant '{dep_id}'."
                    )

        # 3. Vérification mathématique d'acyclicité
        # Si un cycle existait (ex: A dépend de B qui dépend de A), la production serait bloquée !
        if not nx.is_directed_acyclic_graph(self.graph):
            cycle = nx.find_cycle(self.graph, orientation="original")
            raise ValueError(f"Erreur critique de conception : Cycle détecté dans le graphe ! {cycle}")

    def is_acyclic(self) -> bool:
        """Vérifie si le graphe est rigoureusement acyclique (garantie zéro blocage)."""
        return nx.is_directed_acyclic_graph(self.graph)

    def get_reference_topological_sort(self) -> List[AssemblyTask]:
        """
        Génère la séquence d'assemblage déterministe standard (Baseline Usine).
        Trie topologiquement les tâches en respectant l'ordre naturel des macro-étapes (1 -> 2 -> 3 -> 4).
        """
        node_ids = list(nx.lexicographical_topological_sort(
            self.graph,
            key=lambda nid: (self.tasks_dict[nid].macro_step_id, nid)
        ))
        return [self.tasks_dict[nid] for nid in node_ids]

    def validate_sequence(self, sequence_ids: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Vérification stricte de la conformité d'une séquence proposée :
          1. Exhaustivité : Toutes les 21 tâches doivent être présentes exactement une fois.
          2. Précédence : Aucun arc de dépendance u -> v ne doit être violé.
        
        Retourne (True, message_succes) ou (False, raison_violation).
        """
        # Vérification du nombre total de tâches
        if len(sequence_ids) != len(self.tasks_dict):
            return False, f"Taille invalide : {len(sequence_ids)} tâches au lieu de {len(self.tasks_dict)}."

        seen_tasks: Set[str] = set()

        for idx, task_id in enumerate(sequence_ids):
            if task_id not in self.tasks_dict:
                return False, f"Tâche inconnue '{task_id}' à l'indice {idx}."

            if task_id in seen_tasks:
                return False, f"Tâche dupliquée '{task_id}' à l'indice {idx}."

            # Vérification des prérequis : tous les prédécesseurs doivent être déjà complétés
            predecessors = list(self.graph.predecessors(task_id))
            for pred in predecessors:
                if pred not in seen_tasks:
                    pred_name = self.tasks_dict[pred].name
                    curr_name = self.tasks_dict[task_id].name
                    return False, (
                        f"Violation Qualité IATF à l'étape {idx + 1} : "
                        f"La tâche '{curr_name}' ({task_id}) a été exécutée "
                        f"avant son prérequis obligatoire '{pred_name}' ({pred}) !"
                    )

            seen_tasks.add(task_id)

        return True, "Séquence 100% conforme aux règles de précédence IATF 16949."

    def get_available_tasks(self, completed_task_ids: Set[str]) -> List[AssemblyTask]:
        """
        Moteur dynamique pour l'IA d'optimisation :
        À tout instant t du cycle, retourne la liste exacte de toutes les tâches qui peuvent
        être exécutées MAINTENANT (c'est-à-dire dont TOUS les prédécesseurs sont déjà terminés).
        """
        available: List[AssemblyTask] = []
        for task_id, task in self.tasks_dict.items():
            if task_id in completed_task_ids:
                continue
            preds = set(self.graph.predecessors(task_id))
            # Si l'ensemble des prédécesseurs est un sous-ensemble des tâches déjà faites
            if preds.issubset(completed_task_ids):
                available.append(task)
        return available

    def export_graph_data(self) -> Dict[str, Any]:
        """
        Exporte la structure du réseau au format JSON pour le Membre 2 (Frontend)
        et le Membre 3 (Pipeline & Tests).
        Permet d'afficher le diagramme de nœuds interactif sur l'interface utilisateur.
        """
        nodes = []
        for nid, data in self.graph.nodes(data=True):
            nodes.append({"id": nid, **data})

        edges = []
        for u, v in self.graph.edges():
            edges.append({"from": u, "to": v})

        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "nodes": nodes,
            "edges": edges
        }
