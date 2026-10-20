# Spécification du fork

État : **validé lors de l'entretien de cadrage du 2026-10-20**.
Ce fichier est la source de vérité produit : en cas de doute pendant un jalon, c'est lui qui tranche.

## Utilisateur et contexte d'usage
- Un couple : Alex et une deuxième personne du foyer, **deux comptes qui éditent tous les deux** (recettes, aliments, liste de courses).
  Le partage passe par le « foyer » de Tandoor (2.6+).
- Téléphone pour la cuisine, les courses et le choix du repas.
- Ordinateur pour la planification (plan de repas) et le gros ménage (aliments, doublons). Le desktop doit rester
  confortable, mais il ne pilote pas les choix de design.
- Langue : français. Toute chaîne nouvelle existe en `fr` et en `en`.
- Instance auto-hébergée sur le homelab. **Peu de données réelles** aujourd'hui (moins de 30 recettes) : on peut
  réorganiser librement les aliments et les rayons, sans outil de migration de données.

## Problèmes à résoudre
1. **UI datée et peu adaptée au smartphone.**
   - Constat sur les captures `m0-preview` : tableaux paginés à colonnes serrées (Aliments, Garde-manger), barre du bas
     sans libellés qui recouvre le contenu, éditeur de recette à onglets avec onglets tronqués, beaucoup de petites
     zones tactiles.
2. **Organisation des aliments.** Trois gênes concrètes :
   - des doublons et des noms sales créés par les imports (« oignons », « oignon jaune », « 1 oignon émincé ») ;
   - des rayons à attribuer à la main pour chaque nouvel aliment, d'où une liste de courses mal triée ;
   - pas de vue de la hiérarchie : l'arbre existe dans les données, mais l'écran est un tableau plat paginé.
3. **Création de recettes.**
   - L'import par URL est jugé la partie la mieux faite de l'application. Son défaut : **les ingrédients français sont
     mal reconnus** (unités, articles, précisions, pluriels).
   - La saisie manuelle sur téléphone est pénible (formulaire long à onglets, ingrédients rattachés à chaque étape).

## Parcours prioritaires (téléphone)

### P1 — Choisir quoi manger (téléphone, le soir ou avant les courses)
1. J'ouvre l'application, et l'onglet Recettes est l'écran d'accueil. Champ de recherche visible tout de suite.
2. Je filtre selon un ou plusieurs critères, dans une feuille du bas :
   - **ingrédients que j'ai sous la main** (« courgette, riz ») : les recettes qui en utilisent le plus d'abord ;
   - **temps disponible** (≤ 15, 30 ou 60 min, temps total) ;
   - **mot-clé** (végé, soupe, curry…).
3. Ou je **feuillette**, sans filtre : grandes cartes avec photo, raccourcis « récentes », « pas faites depuis longtemps »
   et « au hasard ».
4. Je touche une carte et la recette s'ouvre.

### P2 — Cuisiner une recette (téléphone posé sur le plan de travail)
1. La recette s'ouvre sur une photo, le temps, les portions et la liste d'ingrédients.
2. J'ajuste les portions (3 → 5) : **toutes les quantités sont recalculées**, dans la liste comme dans les étapes.
3. Je lance le **mode cuisine** :
   - **une étape à la fois**, en plein écran et en gros caractères ;
   - on avance et on recule par un balayage ou de grands boutons en bas ;
   - les ingrédients utiles à l'étape sont rappelés quand la recette les rattache à l'étape ;
   - l'écran reste allumé.
4. À la fin, je reviens à la recette (note et commentaire facultatifs).

### P3 — Recette → courses (téléphone)
1. Depuis une recette, j'ouvre « Ajouter aux courses ».
2. Une feuille du bas liste les ingrédients, aux portions choisies, tous cochés.
3. Je décoche ce que j'ai déjà (pas de stock tenu : c'est ce décochage qui en tient lieu).
4. Je valide. Les articles rejoignent la liste partagée du foyer, rangés par rayon.

### P4 — Faire les courses (téléphone, en magasin, une main)
1. La liste est partagée et remplie à deux pendant la semaine. Une seule personne fait les courses.
2. La liste est **groupée par rayon**, dans un ordre de rayons générique.
3. Je coche un article d'**un tap**. Il descend dans « dans le panier ». Je peux annuler.
4. J'ajoute un oubli en texte libre (« 2 citrons ») : il est reconnu et prend son rayon.
5. Quand tout est coché, j'ai un message de fin simple, sans animation.

## Organisation des aliments — attendu

### Ce que Tandoor sait déjà faire (à réutiliser, pas à refaire)
- **Arbre d'aliments** (treebeard), API de déplacement `PUT /api/food/{id}/move/{parent}`, héritage de champs
  (`inherit_fields`).
- **Rayon** `supermarket_category`, ordre des rayons par magasin (`Supermarket` + `SupermarketCategoryRelation.order`).
- **Fusion** de doublons `PUT /api/food/{id}/merge/{target}` : les ingrédients et articles de courses passent sur la cible.
- **Automatisations** `FOOD_ALIAS` / `UNIT_ALIAS` (`cookbook/helper/automation_helper.py`) : elles réécrivent les noms à
  l'import et au parsing. Aujourd'hui, elles se créent à la main dans un écran peu visible.
- **Édition groupée** `BatchEditFoodDialog.vue` (rayon, parent, substituts, « ignorer en courses »).
- **Open Data** : import communautaire d'aliments, d'unités et de rayons.
- **Substituts** (manuels, frères ou enfants dans l'arbre), « ne jamais mettre en courses » (sel, eau).

### Ce que le fork ajoute
1. **Vue arbre à 2 niveaux** : famille > aliment (Légumes > Courgette).
   - Familles repliables, recherche instantanée, filtre « sans rayon ».
   - Déplacer un aliment vers une autre famille en deux taps.
   - Un aliment hérite du rayon de sa famille par défaut.
2. **Rayon suggéré, puis confirmé.** À la création d'un aliment, quelle que soit sa source (import, saisie, liste de
   courses), le fork propose un rayon dans cet ordre :
   - le rayon de la famille parente ;
   - sinon un dictionnaire français d'aliments courants, propre au fork (`kitchen/`) ;
   - sinon un aliment existant au nom proche.

   On confirme ou on corrige en un tap. Les aliments non confirmés forment une **file « à ranger »**, qu'on vide en
   rafale (un tap par rayon).
3. **Doublons évités à l'import.** Pendant la relecture d'un import URL, pour chaque ingrédient dont l'aliment est inconnu :
   - le fork propose l'aliment existant le plus proche (pluriel, accents, mots en plus) ;
   - le choisir crée automatiquement un alias `FOOD_ALIAS`, pour que l'import suivant ne recrée pas le doublon.
4. **Écran de ménage « doublons probables »**, plutôt sur desktop :
   - paires de noms proches, avec un aperçu de la fusion (nombre de recettes et d'articles concernés) ;
   - fusion après confirmation, qui crée l'alias correspondant.
5. **Ordre de rayons générique** en français, pré-rempli et réglable une fois. Rien par magasin : il n'y a pas de magasin fixe.
   L'ordre suit le parcours type : fruits et légumes → boulangerie → frais → boucherie/poisson → épicerie salée →
   épicerie sucrée → boissons → surgelés → hygiène/maison.
6. **Édition rapide** d'un aliment dans une feuille du bas (nom, pluriel, famille, rayon, « jamais en courses »), sans
   changer de page.

### Ce qu'on ne fait pas côté aliments
- Pas de stock : ni case « en stock », ni garde-manger. `food_onhand` et l'inventaire restent upstream, non mis en avant.
- Pas d'arbre à plus de 2 niveaux dans l'UI du fork. Les données plus profondes restent lisibles, sans être encouragées.

## Création de recettes — attendu

### Ce que Tandoor sait déjà faire
- **Import URL** (`RecipeImportPage.vue`, recipe-scrapers) : un assistant de relecture qui alerte sur les doublons et
  permet de corriger l'image, les mots-clés, les étapes et les ingrédients avant d'enregistrer. **On le garde.**
- **Parseur d'ingrédients** (`cookbook/helper/ingredient_parser.py`), plus un collage multi-ligne dans `StepEditor.vue`.
- **Éditeur** à 4 onglets (Recette, Étapes, Propriétés, Divers) : ingrédients rattachés à chaque étape, instructions en
  Markdown, sous-recettes, minuteur par étape.
- Import IA (photo/PDF) et import depuis environ 25 applications : présents, mais **hors périmètre**.

### Ce que le fork ajoute
1. **Reconnaissance des ingrédients en français**, sans modifier `ingredient_parser.py` (alias d'unités, plus un
   prétraitement dans `kitchen/`). Les cas à traiter :
   - Unités : c. à soupe, càs, cs, CS, c. à café, càc, cc, pincée, gousse, sachet, brin, botte, tranche, verre, noisette, filet…
   - « de / d' / des » retirés entre la quantité et l'aliment.
   - Précisions (« émincées », « T55 », « bien mûres ») placées en note, pas dans le nom de l'aliment.
   - Pluriels : « oignons » retrouve « Oignon ».
   - Fractions et formes courantes : ½, 1/2, « 1,5 », « 2-3 ».

   Le tout est mesuré sur un jeu d'au moins 30 lignes réelles en tests pytest.
2. **Saisie manuelle guidée** sur téléphone, un écran par étape, avec un brouillon conservé si l'on quitte :
   1. Nom et portions.
   2. Ingrédients : collage multi-ligne ou une ligne à la fois. Reconnaissance en direct, puis correction d'une ligne
      dans une feuille du bas.
   3. Étapes : un paragraphe par étape. On peut réordonner.
   4. Détails : temps de préparation et de cuisson, mots-clés, photo **depuis la galerie**. On enregistre ensuite.
3. **Liste unique d'ingrédients** pour les recettes créées dans le fork : une seule liste en haut, des étapes en texte.
   Stockage : tous les ingrédients dans la première étape (voir DECISIONS.md). Les recettes importées déjà découpées
   par étape **gardent leur découpage**.
4. **Bouton « Ajouter »** de la barre du bas : une feuille à deux choix, « Depuis un site (URL) » ou « Saisir une recette ».
5. Modifier une recette existante sur téléphone reste possible avec le même découpage en écrans.

## Hors périmètre
Les fonctions upstream suivantes restent intactes et accessibles via « Plus », mais le fork ne les refait pas :
- garde-manger / inventaire, stock (`food_onhand`) ;
- livres de recettes ;
- import IA (photo, PDF, texte) et import depuis d'autres applications ;
- nutrition, propriétés, prix et base USDA (les écrans restent en l'état) ;
- plan de repas : utilisé sur desktop, sans refonte mobile prévue (il gagne seulement le thème et la coquille de M1).

S'y ajoutent :
- pas de changement du modèle de données upstream : les extensions vivent uniquement dans `kitchen/` ;
- pas de dépendance à un service externe (pas de Google Fonts, pas d'API IA).

## Contraintes
- Rester synchronisable avec les releases upstream (`master`). La divergence reste **minimale** : nouvelles pages dans
  `vue3/src/fork/`, backend dans `kitchen/`, upstream retouché le moins possible.
- Mobile d'abord : 360 px de large minimum, utilisable à une main, zones tactiles ≥ 44 px.
- Deux utilisateurs simultanés : rien ne doit reposer sur un état local à un seul appareil, sauf les brouillons.

## Critères de succès
1. **Des courses sans friction.** Après une semaine d'usage réel, la liste est entièrement triée par rayon et aucun
   article n'est « sans rayon ».
2. **Zéro doublon.** L'écran « doublons probables » est vide après le premier ménage, et il le reste après 10 imports URL.
3. **On l'utilise vraiment.** Le couple cuisine avec l'application plusieurs fois par semaine pendant un mois, sans
   revenir au papier ni à une autre application.
