# Feuille de route du fork

Chaque jalon = une session Claude Code autonome = une PR. Les critères ci-dessous sont la définition de « fini ».
M2 à M4 découlent de SPEC.md (cadrage du 2026-10-20).
Statut : `[ ]` à faire, `[x]` fait. Un jalon est terminé quand sa PR est fusionnée.

## M0 — Socle et audit [ ]
Aucun changement visible pour l'utilisateur.
- [x] `docs/fork/gitignore.append` est intégré à `.gitignore`.
- [x] `scripts/fork/setup.sh` fonctionne dans la session cloud ; baseline enregistrée (`verify.sh --update-baseline`) et commitée dans `docs/fork/baseline/`.
- [x] Captures de référence publiées : `verify.sh --ui m0-baseline --publish`.
- [x] App Django `kitchen/` créée (vide, un test pytest trivial, enregistrée dans `INSTALLED_APPS`) ; `verify.sh` reste OK.
- [x] `docs/fork/AUDIT.md` rédigé :
  - carte de l'UI (pages, composants partagés, thème Vuetify, navigation mobile/desktop, stores Pinia) ;
  - ce qui existe déjà pour les aliments (arbre `Food`, catégories de rayon, substituts, propriétés, pantry/inventaire, éditeur d'ingrédients, open data) et pour la création de recettes (éditeur, parseur d'ingrédients, import) ;
  - points de friction mobile vus sur les captures `m0-baseline` ;
  - évaluation du système de plugins Tandoor (`recipes/plugins`, `vue3/src/plugins`) face à l'app `kitchen/` ;
  - ajustements proposés pour M1–M4 (ajoutés en fin de ce fichier, section « Propositions M0 », sans modifier les jalons).

## M1 — Fondations visuelles [ ]
- [x] Thème Vuetify clair et sombre construit à partir des tokens de DESIGN.md (couleurs, typographie, rayons, élévations, espacements).
- [x] Transitions en fondu entre les vues (≤ 200 ms), désactivées si `prefers-reduced-motion`.
- [x] Coquille d'application : barre du bas sur mobile (4–5 entrées max, **avec libellés**, hauteur réservée dans `v-main`
      pour ne pas recouvrir le contenu), en-tête compact, tiroir **dès 960 px** (`mdAndUp`) ; zones tactiles ≥ 44 px.
- [x] Aucune route de `routes.json` ne déborde horizontalement à 360 px ; toutes passent en `"strict": true`
      (exception justifiée dans DECISIONS.md si une erreur upstream ne peut pas être corrigée dans le fork).
      Les deux erreurs JS upstream vues en M0 (`POST /api/view-log/` en 403, `TypeError` dans `AccountSettings`) sont
      corrigées ou contournées dans le fork, au plus près du code concerné.
- [x] Captures fiables : capture « écran visible » en plus de la pleine page ; captures reproductibles (pas de contenu
      aléatoire, attente du chargement) ; les captures 360 px (`small`) sont publiées avec `--publish`.
- [x] Aucune régression : `verify.sh --ui m1` OK, rapport `ui-auditor` sans problème bloquant.

## M2 — Parcours cuisine sur mobile [ ]
Découle de SPEC.md, parcours P1 à P4.
- [x] P1 Choisir quoi manger : l'onglet Recettes est l'accueil, avec la recherche visible immédiatement.
  - Filtres en feuille du bas :
    - ingrédients sous la main, les recettes qui en utilisent le plus d'abord ;
    - temps total (≤ 15, 30 ou 60 min) ;
    - mots-clés.
  - Raccourcis « récentes », « pas faites depuis longtemps » et « au hasard ».
  - Grandes cartes avec photo, lisibles à une main.
- [x] P2 Cuisiner : la vue recette montre la photo, le temps, les portions et les ingrédients.
  - Les portions sont ajustables et recalculent toutes les quantités, dans la liste comme dans les étapes.
  - Le mode cuisine affiche **une étape par écran**, en plein écran et en gros caractères (DESIGN.md, « Mode cuisine »).
  - On avance et recule par balayage ou avec deux grands boutons en bas.
  - Les ingrédients de l'étape sont rappelés quand la recette les y rattache.
  - L'écran reste allumé (Wake Lock).
- [x] P3 Recette → courses : la feuille « Ajouter aux courses » liste les ingrédients aux portions choisies, tous cochés.
  - On décoche ce qu'on a déjà, puis on valide.
  - Les articles rejoignent la liste partagée du foyer.
- [x] P4 Courses : liste groupée par rayon.
  - Un tap coche un article, qui descend dans « dans le panier ».
  - L'annulation est possible.
  - Ajout rapide en texte libre (« 2 citrons »).
  - Message de fin simple, sans animation.
- [x] Les modifications faites par l'autre membre du foyer apparaissent sans recharger la page, au plus tard au retour
      sur l'écran. La synchro automatique existante de `ShoppingStore` (intervalle réglable, reprise au retour sur
      l'écran) suffit : pas de temps réel.
- [x] Pages refaites en `strict`. `verify.sh --ui m2` OK.

## M3 — Organisation des aliments [ ]
Découle de SPEC.md, section « Organisation des aliments — attendu ».
- [x] Écran Aliments en vue arbre à 2 niveaux (famille > aliment) :
  - familles repliables, recherche instantanée, filtre « sans rayon » ;
  - déplacement vers une autre famille en 2 taps ;
  - un aliment hérite du rayon de sa famille par défaut ;
  - aucun tableau à colonnes sur mobile.
- [x] Rayon suggéré à chaque création d'aliment (import, saisie, liste de courses), puis confirmé en un tap :
  - ordre de suggestion : rayon de la famille, puis dictionnaire français d'aliments courants dans `kitchen/`, puis
    aliment au nom proche ;
  - file « à ranger » à vider en rafale, un tap par rayon.
- [x] Ordre de rayons générique en français pré-rempli (fruits et légumes → … → hygiène/maison) et réglable. La liste de
      courses est groupée selon cet ordre.
- [x] Écran « doublons probables » (pluriels, accents, mots en plus) :
  - fusion avec aperçu (recettes et articles concernés) et confirmation, via l'API de fusion existante ;
  - création automatique d'un alias `FOOD_ALIAS`.
- [x] Relecture d'un import URL : pour chaque ingrédient d'aliment inconnu, proposition de l'aliment existant le plus
      proche. Le choisir crée un alias `FOOD_ALIAS`.
- [x] Édition rapide d'un aliment dans une feuille du bas (nom, pluriel, famille, rayon, « jamais en courses »), sans
      changer de page.
- [x] Rien n'est ajouté pour le stock ni le garde-manger (hors périmètre).
- [x] Toute donnée nouvelle vit dans `kitchen/`. Tests pytest pour chaque endpoint ajouté, dont un test qui fait
      détecter les doublons par la règle de similarité sur un jeu d'exemples français. `verify.sh --ui m3` OK.

## M4 — Création et édition de recettes [ ]
Découle de SPEC.md, section « Création de recettes — attendu ».
- [x] Reconnaissance des ingrédients en français, sans modifier `cookbook/helper/ingredient_parser.py` (alias d'unités et
      prétraitement dans `kitchen/`) :
  - unités françaises (c. à soupe, cs, càc, pincée, gousse, sachet, brin, botte…) ;
  - « de/d'/des » retirés ;
  - précisions placées en note ;
  - pluriels ramenés à l'aliment existant ;
  - fractions ½, 1/2, 1,5.

  Un jeu d'au moins 30 lignes réelles est testé en pytest. Il passe aussi par l'import URL et par la liste de courses.
- [x] L'assistant d'import URL existant est conservé. Il bénéficie de la reconnaissance française et de la proposition
      d'aliment proche de M3.
- [x] Saisie guidée sur mobile en 4 écrans :
  1. Nom et portions.
  2. Ingrédients (collage multi-ligne ou ligne à ligne, reconnaissance en direct, correction d'une ligne dans une
     feuille du bas).
  3. Étapes (un paragraphe chacune, réordonnables).
  4. Détails (temps, mots-clés, photo depuis la galerie).

  Navigation avant/arrière sans perte de saisie. Brouillon conservé si l'on quitte la page.
- [x] Liste unique d'ingrédients pour les recettes créées dans le fork, stockée dans la première étape.
  - La vue recette l'affiche en une seule liste en haut.
  - Les recettes importées déjà découpées par étape gardent leur découpage.
- [x] Bouton « Ajouter » de la barre du bas : une feuille à deux choix, « Depuis un site (URL) » et « Saisir une recette ».
- [x] Une recette existante se modifie sur mobile avec le même découpage en écrans.
- [x] Pages refaites en `strict`. `verify.sh --ui m4` OK.

## M5 — Cuisine et courses au quotidien (idées kitshn) [ ]
Découle de `docs/fork/AUDIT-KITSHN.md` (audit du 2026-10-21). Aucun changement backend attendu : tout passe par l'API
upstream existante (`/api/cook-log/`, `/api/meal-plan/`, courses) et par le front du fork.
- [x] Minuteurs dans les étapes :
  - les durées du texte des étapes sont repérées en français et deviennent touchables, dans le mode cuisine et dans la
    vue recette : « 10 min », « 1 h 30 », « 1 heure et demie », « 45 s », plages « 20 à 25 minutes » et « 2-3 min » ;
  - la puce du temps de l'étape (`step.time`) lance aussi un minuteur ;
  - une plage propose de choisir la durée (bas, haut ou entre les deux) ;
  - plusieurs minuteurs en même temps, visibles dans une barre compacte qui suit d'une page à l'autre (mode cuisine,
    recette), avec pause, +1 min et arrêt ;
  - les minuteurs reposent sur leur heure de fin et survivent à un rechargement ;
  - à la fin : son, vibration si disponible, et notification système si elle est autorisée (jamais exigée) ;
  - la détection est une fonction pure, testée automatiquement par `verify.sh` (pas de vitest dans `vue3` : petit test
    node ou test de parcours, choix noté dans DECISIONS.md) sur au moins 20 phrases françaises
    réelles (dont des faux positifs à éviter : « 4 personnes », « 180 °C », « farine T55 », « 2 œufs »).
- [x] Fin de cuisine : le bouton « Terminé » du mode cuisine ouvre un écran « Bon appétit » avec une note (étoiles) et
      un commentaire facultatifs, puis « Enregistrer » ou « Passer ». Les deux créent un `CookLog` (portions incluses),
      ce qui nourrit « récentes » et « pas faites depuis longtemps » sur l'accueil. Retour à la recette ensuite.
- [x] Courses en magasin :
  - l'écran reste allumé sur la liste de courses (réglable, actif par défaut), relâché en quittant la page ;
  - les coches faites sans réseau sont conservées sur l'appareil, même après fermeture de l'app, puis envoyées au
    retour du réseau ; un indicateur affiche « N modifications en attente » ;
  - la liste s'affiche hors ligne avec le dernier état connu ;
  - la correction de la file de synchro reste au plus près de `ShoppingStore` (diff minimal, noté dans DECISIONS.md).
- [x] « Au menu » sur l'accueil téléphone : carte compacte affichée seulement s'il y a un repas prévu, « Aujourd'hui » (ou
      « Demain » après 21 h) ; un tap ouvre la recette (ou montre le titre si l'entrée n'a pas de recette).
- [x] Partage vers l'app : un lien partagé à la PWA (`share_target` upstream) lance l'import sur la première URL trouvée
      dans `url`, `text` ou `title` (« Recette de tarte https://… » fonctionne).
- [x] Nouvelles chaînes en `fr` et `en`. Pages touchées en `strict`, zones tactiles ≥ 44 px, 360 px sans débordement.
      Parcours cliqués pour les minuteurs, la fin de cuisine et les coches hors ligne. `verify.sh --ui m5` OK.

## M6 — Livraison sur le homelab [x]
- [x] Workflow GitHub Actions qui construit l'image Docker du fork et la publie sur GHCR (tag = version upstream + suffixe fork).
- [x] `docs/fork/DEPLOY.md` : stack compose pour Komodo, sauvegarde de la base avant bascule, test sur une copie, retour arrière vers l'image upstream.
- [x] CI GitHub Actions : `verify.sh` complet sur chaque PR vers `main`, la porte reste `VERIFY: OK`.
- [x] Vérification que les migrations de `kitchen/` s'appliquent sur une base Postgres créée par l'image upstream (service Postgres de la session).

## Récurrent — synchronisation upstream
À chaque release Tandoor : `/upstream-sync` (branche `sync/upstream-<tag>`, PR dédiée).

## Propositions M0
Rédigées par la session M0 à partir de `docs/fork/AUDIT.md`. **Toutes validées par Alex le 2026-10-20.**
Celles qui changent un critère sont intégrées aux jalons ci-dessus : M1 (coquille, erreurs upstream, captures),
M2 (synchro) et M6, ex-M5 (CI). Les autres restent ici comme notes d'implémentation, à suivre par les sessions des jalons.

**M1 — Fondations visuelles**
- Ajouter à `screenshots.mjs` une capture « écran visible » (viewport seul) en plus de la pleine page. Elle permet de
  juger le recouvrement par la barre du bas, que la capture pleine page ne montre pas.
- Corriger ou contourner dans le fork les deux erreurs JS upstream vues en `m0-baseline` :
  - `POST /api/view-log/` en 403 sur la vue recette ;
  - `TypeError` dans `AccountSettings`.

  Sinon, ces pages ne pourront pas passer en `strict`. Le critère « toutes en strict » prévoit déjà l'exception.
- Rendre les captures reproductibles : graine fixe (ou bloc masqué) pour « Recettes aléatoires », attente de la fin du
  chargement utilisateur avant la capture des réglages. Publier aussi les captures 360 px (`small`), largeur de référence
  des règles du fork.
- Passer le seuil mobile de la coquille de `lgAndUp` (1280 px) à `mdAndUp` (960 px), pour que les tablettes en paysage
  aient le tiroir. C'est un réglage de `Tandoor.vue`.
- Réserver la hauteur de la barre du bas dans `v-main` et ajouter des libellés aux entrées.

**M2 — Parcours cuisine**
- P4 : s'appuyer sur `ShoppingStore`, qui fait déjà le regroupement, la synchro automatique et la pile d'annulation.
  Refaire l'affichage plutôt que le store.
- P1 : le filtre « ingrédients sous la main » existe en partie dans la recherche avancée (`food_availability_helper.py`),
  mais repose sur le stock (`onhand`). Prévoir un endpoint `kitchen/` de classement par nombre d'ingrédients
  correspondants, sans stock.
- Mettre le critère « modifications de l'autre membre du foyer » au niveau de ce que fait déjà la synchro automatique
  des courses (intervalle réglable), plutôt que du temps réel.

**M3 — Organisation des aliments**
- Ordre de rayons générique : réutiliser un `Supermarket` unique (« Ordre générique ») et
  `SupermarketCategoryRelation.order`, sélectionné par défaut, plutôt qu'un nouveau modèle. Le groupement existant de
  la liste de courses en profite sans changement.
- Héritage du rayon : activer `supermarket_category` dans `Space.food_inherit` (mécanisme upstream) plutôt que de le
  recoder.
- Ajouter au critère des doublons : réutiliser `ModelMergeDialog` / `MergeMixin`, qui créent déjà l'alias.

**M4 — Création de recettes**
- Le collage multi-ligne (`StepEditor.parseAndInsertIngredients`) et l'import URL passent tous deux par
  `IngredientParser`. Le prétraitement français doit donc être branché aux deux endroits (endpoint `kitchen/`
  équivalent à `/api/ingredient-parser/`, et relecture d'import côté front), sans toucher au parseur.
- Le jeu de 30 lignes peut partir des cas mesurés dans AUDIT.md § 3, qui échouent tous sauf les fractions.

**Outillage**
- Lancer `verify.sh` complet en CI GitHub Actions sur chaque PR, avec la même porte `VERIFY: OK` (à rattacher à M6, ex-M5).
