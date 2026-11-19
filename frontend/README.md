# Membre 2 : établi virtuel & simulateur du projecteur zénithal

Application Streamlit (style rétro du tableau de bord ProjFlow) qui simule, vue de dessus, le
projecteur zénithal du poste LEONI 3.2 :
chemin lumineux cyan `#00F0FF` que la main doit suivre, cible active en vert `#10B981`,
et animation de rotation de la trajectoire (15 à 30°) quand le jumeau de fatigue déclenche une mutation.

## Lancer

```bash
pip install -r frontend/requirements.txt
streamlit run frontend/app.py          # depuis la racine du dépôt -> http://localhost:8501
python -m frontend.test_frontend       # tests
```

## Architecture

- `session.py` : machine d'état côté serveur (cycle, fatigue, déclenchement, mutations).
- `static/projector.html` : composant navigateur SVG + JS (établi, trajectoires, jauges, journal).
  Il anime seul le cycle à 60 i/s à partir d'un instantané (`ProjectorSession.snapshot`).
- `app.py` : toutes les 0,5 s, fait avancer la session et ne renvoie un instantané que si l'état
  visible change (mutation, lot, pause, vitesse). Sinon le HTML est identique et l'iframe n'est
  pas rechargée, ce qui évite le scintillement d'un graphique redessiné en boucle.

## Ce que montre l'écran (phases 3 et 4)

- **Badge vert « 🔒 IATF 16949 · Protocole verrouillé : 100 % conforme »** : calculé à chaque instant
  (32/32 règles de précédence du DAG, 3/3 positions verrouillées `quality_critical`, empreinte identique).
  Il passe au rouge « NON CONFORME » si l'une de ces vérifications échoue.
- **Temps de cycle en direct** (ex. « 214 s / 276 s limite ») + cycle planifié ≤ takt et retard dû à l'IA (0 s).
- **Jauges poignets, mains & doigts, coudes, épaules** : vert < 40 %, orange 40–75 %, rouge > 75 %
  (100 % = pic du protocole fixe sur un cycle) ; valeur barrée = protocole fixe au même instant.
- **Avant / après sur un shift** : `BiomechanicalFatigueTwin.compare_shift` du Membre 1
  (protocole répété 5 fois vs 5 lots polymorphes), fatigue résiduelle en fin de shift.
- **Barre latérale** : mode « Protocole fixe standard (fatigue élevée) » / « ProjFlow-AI · nudge
  subconscient (protégé) », bascule immédiate ; bouton « Simuler le lot suivant » (termine le lot dans le
  jumeau de fatigue et lance un nouvel ordre polymorphe) ; vitesse ; pause.

## Sources de données

Le simulateur affiche toujours des `ProjectedStep` (contrat `src/models/data_contracts.py`).

| Source | Contenu | Mutation |
|---|---|---|
| **Moteur IA Membre 1 (live)**, par défaut | 21 tâches de `backend/leoni_data.py`, DAG `AssemblyGraphEngine`, `AssemblySequenceOptimizer`, `BiomechanicalFatigueTwin` | réordonnancement des étapes restantes (même boucle que `generate_ergonomic_sequence`, depuis l'état en cours) + rotation des angles d'approche |
| **Lots scénarisés Membre 3 (rejeu)** | `DataPipeline.build_payload` sur la topologie (13 composants) | passage au `ai_mutated_sequence` et aux `spatial_angle_adjustments_deg` du lot 3 |

Le code des Membres 1 et 3 n'est pas modifié, seulement importé (`frontend/adapter.py`).

## Déclencher une mutation

1. **Auto** : le jumeau de fatigue prévoit, dans les 30 s, une articulation au-dessus du seuil
   (M1 : % du pic atteint par le protocole fixe ; M3 : % de fatigue du lot).
2. **Mode** : passage au mode ProjFlow-AI dans la barre latérale (le retour au protocole fixe est immédiat aussi).
3. **Nouveau lot** : en mode ProjFlow-AI, chaque lot démarre directement dans une séquence polymorphe.

## Conventions

- **Repère** : x, y en mm ; l'opérateur est sur le bord bas ; y croît vers l'opérateur
  (celui de la topologie M3). Données M1 converties : `x = x_cm*10`, `y = (100 - y_cm)*10`.
- **Angle d'approche** : degrés, repère écran (y vers le bas), vecteur cible → main ;
  90° = main qui arrive tout droit depuis l'opérateur (convention de `post_3_2_topology.json`).
- **Tâches M1** (pas d'angle dans le dataset) : protocole = 90°. Mutation = rotation de 15 à 30°
  vers l'axe de l'avant-bras (cible → épaule de l'opérateur) ; si la cible est déjà dans l'axe
  (< 15°), on alterne ±15° d'un lot à l'autre pour varier la sollicitation.
- **Trajectoire** : Bézier quadratique de la cible précédente à la cible active ; le point de
  contrôle suit l'angle d'approche. Tourner l'angle fait pivoter l'arrivée de la main, les deux
  extrémités restent fixes.
- **Preuve « protocole inchangé »** : `protocol_fingerprint` hache l'ensemble des tâches, de
  leurs cibles, de leurs macro-phases et des arcs de précédence, sans l'ordre ni les angles.
  L'empreinte doit être identique avant et après chaque mutation ; `validate_sequence` du DAG
  est aussi vérifié à chaque mutation.
