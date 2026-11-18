# ProjFlow-AI - Prévention des TMS Multisites (SSTHack 2026)

> **Solution logicielle et IA d'optimisation ergonomique par guidage visuel dynamique et polymorphisme procédural.**  
> Projet développé dans le cadre du **Hackathon SSTHack 2026** (ISST & IEEE ISTMT Student Branch).

---

## 🎯 Contexte & Niche Industrielle : LEONI Poste 3.2 (Track 3)

Le poste **LEONI 3.2** correspond au montage et à l'encliquetage de faisceaux électriques automobiles (430 fils) sur gabarit :
* **Cadence imposée :** 13 câblages par heure, tapis au **takt time de 276 secondes**.
* **Pathologies réelles constatées (Cahier des charges p.5) :** Douleurs aux épaules en fin de journée (H.A.), épicondylite bilatérale, syndrome du canal carpien, tendinites de la main et des doigts.
* **Tâches manuelles :**
  1. *Raccorder les composants sur le gabarit* (Macro 1 : 45 s)
  2. *Encliqueter les cosses dans les connecteurs - tâche la plus pénible* (Macro 2 : 110 s)
  3. *Enrubanner le faisceau* (Macro 3 : 65 s)
  4. *Verrouillage CPA & Clips carrosserie* (Macro 4 : 56 s)
  * **Total cumulé = 276.0 secondes pile.**

---

## 💡 Le Concept : ProjFlow-AI

Au lieu d'imposer à l'opératrice une routine motrice fixe et répétitive qui sature les mêmes tendons lot après lot :
1. **Guidage lumineux zénithal (simulé) :** L'opératrice est guidée tâche par tâche par un spot lumineux dynamique projeté sur l'établi.
2. **Moteur de Graphes DAG (NetworkX) :** Garantit le respect absolu des règles de précédence qualité **IATF 16949**.
3. **Polymorphisme IA & Alternance Motrice :** L'algorithme réordonne dynamiquement les micro-libertés d'un lot à l'autre pour intercaler des phases de repos tendineux sans jamais ralentir la cadence.
4. **Jumeau Numérique de Fatigue Prédictive :** Évalue la charge tendineuse et l'index **OCRA (ISO 11228-3)** sans **aucun capteur ni caméra invasive** (Exigences D1, D3).

---

## 🏗️ Architecture du Projet

```
ISSTHACK/
├── backend/                  # Membre 1 : Moteur IA, DAG & Jumeau de fatigue
│   ├── __init__.py
│   ├── models.py            # Modélisation biomécanique 4 zones & dataclasses de tâches
│   ├── leoni_data.py        # Dataset réaliste des 21 tâches du poste 3.2 (Takt time 276s)
│   ├── graph_engine.py      # Moteur DAG NetworkX (21 nœuds, 32 arcs, contrôleur IATF)
│   ├── optimizer.py         # Algorithme d'optimisation biomécanique (fonction de coût)
│   └── fatigue_twin.py      # Jumeau numérique de fatigue tendineuse (Rohmert / OCRA)
├── data/                    # Membre 3 : Topologie et lots de production
│   ├── post_3_2_topology.json
│   ├── production_batches.json
│   └── validate_datasets.py
└── src/                     # Membre 3 : Pipelines d'intégration & exécuteur de démo
    ├── models/
    │   └── data_contracts.py
    └── pipeline/
        ├── data_pipeline.py
        ├── demo_runner.py
        └── test_wiring.py
```

---

## 🚀 Installation & Exécution Rapide

### Prérequis
* Python 3.10+
* Dépendances : `networkx`, `numpy`, `pandas`

```bash
git clone https://github.com/SkanDaBomb-skan/ISSTHACK.git
cd ISSTHACK
pip install networkx numpy pandas
```

### Vérification de l'ordonnancement et du jumeau de fatigue :
```bash
python -c "
from backend.leoni_data import get_leoni_reference_tasks
from backend.graph_engine import AssemblyGraphEngine
from backend.optimizer import AssemblySequenceOptimizer
from backend.fatigue_twin import BiomechanicalFatigueTwin

tasks = get_leoni_reference_tasks()
engine = AssemblyGraphEngine(tasks)
opt = AssemblySequenceOptimizer(engine)
twin = BiomechanicalFatigueTwin()

base = opt.generate_baseline_sequence()
poly = [opt.generate_ergonomic_sequence(seed=i) for i in range(1, 6)]
res = twin.compare_shift(base, poly)
print('Validation OK. Takt time =', res['total_shift_duration_sec'] / 5, 's')
"
```
