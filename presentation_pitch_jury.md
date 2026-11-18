# 🎤 Trame du Pitch Démo Jury — ProjFlow-AI (Poste LEONI 3.2)
*Durée recommandée : 5 minutes de présentation + 3 minutes de questions/réponses*

---

## ⏱️ Minute 0 à 1 : L'Accroche & Le Choc du Réel
> *"Bonjour à tous les membres du jury.  
> Imaginez le Poste 3.2 chez LEONI. L'opérateur assemble un faisceau de câbles complexe. Il a exactement 276 secondes par faisceau. À la fin de la journée, il aura répété le même geste d'insertion de connecteurs plus de 800 fois avec la même torsion du poignet.  
> Que propose l'industrie aujourd'hui ?  
> Soit des tableaux de bord passifs qu'aucun opérateur ne regarde pendant qu'il câble... soit des capteurs portés intrusifs que personne ne veut porter sur son corps.  
> Nous avons créé **ProjFlow-AI** : une ergonomie subconsciente, sans aucun capteur, guidée par la lumière et 100% conforme aux protocoles qualité automobiles."*

---

## ⏱️ Minute 1 à 2 : L'Éléphant dans la Pièce (La Réponse au Jury)
> *"Vous allez immédiatement nous poser la question d'or :  
> **'Dans l'automobile, la gamme opératoire IATF 16949 est sacrée. Comment pouvez-vous changer la séquence d'assemblage sans violer le contrôle qualité ?'**  
> Notre réponse est claire : **Nous ne touchons JAMAIS à la gamme opératoire.**  
> La gamme impose 4 macro-phases strictes :  
> 1. Tronc central d'abord  
> 2. Dérivations secondaires ensuite  
> 3. Connecteurs auxiliaires  
> 4. Frettage et contrôle final.  
> Cet ordre est vérifié mathématiquement et respecté à 100%.  
> Ce que notre IA modifie, ce sont les **micro-libertés spatiales** et les **angles d'approche lumineux** à l'intérieur de chaque phase."*

---

## ⏱️ Minute 2 à 4 : La Démonstration en Direct (Les 3 Actes)
*(Pendant que vous parlez, lancez `python src/pipeline/demo_runner.py` ou montrez l'interface Streamlit)*

1. **Acte 1 : Démarrage le matin**
   > *"Au Lot 1, l'opérateur est reposé (fatigue poignet à 5%). La séquence classique est déroulée. Le temps de cycle est de 198 secondes, bien en-deçà des 276 secondes requises."*

2. **Acte 2 : La détection invisible**
   > *"Au Lot 2, notre jumeau de flux en arrière-plan calcule la saturation tendineuse cumulative. Sans caméra, sans montre connectée, par simple calcul de l'historique de production, l'IA détecte que le tendon fléchisseur du poignet dépasse le seuil critique des 70%."*

3. **Acte 3 : La mutation par la lumière**
   > *"Regardez le Lot 3 : l'IA active le polymorphisme spatial. Le projecteur zénithal pivote les angles d'attaque de 30° et alterne la main dominante. Résultat : une baisse immédiate de **38% de la charge sur le poignet**, le takt time est préservé, et la pièce est conforme IATF."*

---

## ⏱️ Minute 4 à 5 : Pourquoi ProjFlow-AI Gagne ?
* **Éthique & Adoption** : 0 capteur, 0 intrusion, confort immédiat pour les opérateurs.
* **Faisabilité Usine** : Pas besoin de réaménager l'usine, un projecteur au plafond et un script d'inférence suffisent.
* **Rentabilité LEONI** : Baisse drastique des TMS (Troubles Musculosquelettiques), zéro ralentissement de cadence.

---

## 🎯 Réponses Choc aux Questions du Jury

| Question piège du jury | Votre réponse immédiate |
| :--- | :--- |
| **"Et si un composant A doit obligatoirement être monté avant B ?"** | *"C'est encodé dans notre graphe orienté acyclique (DAG). Deux composants dépendants sont verrouillés dans le même ordre. Seuls les composants indépendants au sein de la même phase alternent spatialement."* |
| **"Comment mesurez-vous la fatigue sans capteurs ?"** | *"Par un modèle biomécanique validé (effort unitaire $\times$ angle articulaire $\times$ nombre de cycles). Comme le Thermal Throttling d'un processeur qui estime sa température d'après sa charge de calcul, nous estimons l'usure tendineuse d'après la charge de travail réelle."* |
| **"Est-ce que l'opérateur n'est pas désorienté par le changement d'ordre ?"** | *"Non, car il ne réfléchit pas à l'ordre : il suit naturellement le repère lumineux projeté sur le gabarit (système Pick-to-Light zénithal). L'adaptation est subconsciente."* |
