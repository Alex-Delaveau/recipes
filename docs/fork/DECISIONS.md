# Décisions

Journal des choix faits en autonomie, à relire par Alex. Le plus récent en haut.
Format : `## AAAA-MM-JJ — Mx — titre` puis **Contexte**, **Choix**, **Alternative écartée**, **Réversible ?**

## 2026-10-20 — M3 — Héritage du rayon géré par le fork, pas par `Space.food_inherit`
**Contexte** : les propositions M0 suggéraient d'activer `supermarket_category` dans `Space.food_inherit`. En pratique :
- ce réglage n'est appliqué à aucun aliment existant ou nouveau ;
- il faut passer par `Food.reset_inheritance`, qui efface les liens d'héritage de **tous** les espaces (bug upstream) ;
- un membre suit ensuite toujours sa famille et ne peut plus avoir un autre rayon.

**Choix** : le fork applique la règle « un aliment hérite du rayon de sa famille par défaut » dans `kitchen/services.py` :
- un aliment créé dans une famille prend son rayon ;
- un aliment déplacé dans une famille prend son rayon ;
- quand le rayon d'une famille change, ses membres le suivent, sauf ceux dont l'utilisateur a choisi le rayon.

Les champs upstream ne changent pas de sens.
**Alternative écartée** : `Space.food_inherit` + `reset_inheritance` (bug multi-espaces, pas d'exception possible).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Rayon suggéré appliqué tout de suite, puis confirmé
**Contexte** : SPEC.md veut un rayon suggéré à chaque création d'aliment, confirmé en un tap, et une file « à ranger ».
**Choix** :
- à la création d'un aliment (signal `post_save`, donc import, saisie, liste de courses et API), le fork calcule une
  suggestion : rayon de la famille, puis dictionnaire français (`kitchen/aisles.py`, environ 300 aliments courants),
  puis rayon d'un aliment au nom proche ;
- la suggestion est **appliquée aussitôt** : la liste de courses est triée sans attendre ;
- l'aliment reste « non confirmé » et entre dans la file « à ranger », où un tap confirme ou corrige le rayon.

Un aliment créé avec un rayon (choisi par l'utilisateur, ou venu de l'open data) est déjà confirmé. Les espaces qui
n'ont jamais ouvert les écrans du fork ne sont pas touchés, ce qui garde intacts les tests upstream.
**Alternative écartée** : ne rien écrire avant confirmation. Les articles resteraient « sans rayon » jusqu'au tri,
contre le critère de succès n° 1.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Ordre générique = un `Supermarket` upstream
**Choix** :
- un `Supermarket` « Ordre générique », créé au premier usage, ordonne les rayons
  (`SupermarketCategoryRelation.order`) ;
- les catégories existantes sont reprises quand leur nom correspond (« Crèmerie » tient lieu de « Frais »,
  « Fruits & légumes » de « Fruits et légumes ») ; les rayons manquants sont créés ; les autres catégories viennent
  après ;
- la liste de courses du fork suit cet ordre quand aucun magasin n'est choisi sur l'appareil. L'ordre se règle dans
  Aliments › Ordre des rayons (boutons monter/descendre, sans glisser-déposer).

**Alternative écartée** : une table d'ordre dans `kitchen/` (doublon de ce que fait upstream).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Familles
**Contexte** : dans l'arbre upstream, rien ne distingue une famille vide d'un aliment isolé.
**Choix** : une famille est un aliment de premier niveau qui a des enfants, ou qui est marqué « famille »
(`KitchenFood.is_family`, interrupteur dans la feuille d'édition). Les aliments de premier niveau qui ne sont pas des
familles sont regroupés sous « Sans famille ». Les niveaux plus profonds s'affichent dans leur famille de premier niveau.
Les familles sont dépliées par défaut tant qu'il y a 80 aliments au plus.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Règle de similarité des doublons
**Choix** : `kitchen/names.py`, une règle simple et explicable, testée sur des exemples français. Deux noms sont
probablement le même aliment dans trois cas :
- ils ne diffèrent que par les majuscules, les accents, le pluriel, une quantité ou un mot de préparation
  (« émincé », « frais », « bio ») ;
- les mots de l'un sont tous dans l'autre, avec au plus deux mots en plus (« oignon » / « oignon jaune ») ;
- leur orthographe est proche (≥ 88 %).

Les noms composés avec une préposition restent distincts : « pomme de terre », « lait de coco », « huile d'olive ».
Côté écran, on garde l'aliment le plus utilisé, puis le nom le plus court ; un bouton inverse le choix. « Pas un
doublon » mémorise la paire (`NotDuplicate`).
**Réversible ?** Oui.

## 2026-10-20 — M3 — Fusion upstream, alias côté client
**Choix** : la fusion appelle l'API upstream (`PUT /api/food/{id}/merge/{target}/`), puis crée l'alias `FOOD_ALIAS`
(nom fusionné → nom gardé), exactement comme `ModelMergeDialog`. Pour que la fusion générique upstream fonctionne
encore, la relation inverse de `KitchenFood` est masquée (`related_name='+'`) : sinon `MergeMixin` rencontre un
OneToOne qu'il ne sait pas traiter. Un test pytest le garantit.
**Réversible ?** Oui.

## 2026-10-20 — M3 — Relecture d'import : proposition d'aliment proche
**Choix** : un encart « Aliments inconnus » est inséré dans l'étape « Étapes » de l'assistant d'import upstream
(3 lignes dans `RecipeImportPage.vue`). Pour chaque aliment inconnu (nom, pluriel ou alias), il propose l'aliment
existant le plus proche :
- « Utiliser l'existant » renomme l'ingrédient et crée l'alias ;
- « Garder le nouveau » laisse créer l'aliment, qui recevra un rayon suggéré.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Branches par jalon
**Contexte** : l'objectif de session demande une branche et une PR par jalon (M2, M3, M4), chaque branche partant de
la précédente tant que sa PR n'est pas fusionnée. En M0 et M1, la session imposait une branche `claude/...`.
**Choix** : `fork/m2-cuisine`, puis `fork/m3-aliments` (depuis M2) et `fork/m4-recettes` (depuis M3), comme le prévoit
CLAUDE.md. Le push de ces branches est accepté par le dépôt.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Client des endpoints `kitchen/` écrit à la main
**Contexte** : le client TypeScript `vue3/src/openapi` est généré à partir du schéma OpenAPI. Le régénérer ajouterait
les endpoints du fork dans les fichiers générés upstream (conflits à chaque synchronisation).
**Choix** : un petit client à la main dans `vue3/src/fork/api.ts` (fetch + cookie CSRF), qui réutilise les
convertisseurs générés (`RecipeOverviewFromJSON`). Les endpoints du fork sont montés sous `/api/kitchen/`
(une ligne dans `recipes/urls.py`).
**Alternative écartée** : régénérer le client (diff dans des fichiers générés upstream).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Recherche de l'accueil : `GET /api/kitchen/recipes/`
**Contexte** : P1 demande les ingrédients sous la main (classement), un temps total maximal et trois raccourcis.
La recherche upstream n'a ni filtre de temps total ni classement sans stock (`makenow` repose sur `onhand`).
**Choix** : un endpoint `kitchen/` qui applique d'abord `RecipeSearch` upstream (texte, mots-clés…), puis :
- `have` : recettes utilisant au moins un des aliments (familles comprises : « Légumes » couvre « Courgette »),
  classées par nombre d'aliments trouvés, puis par nombre total d'aliments (les recettes courtes d'abord) ;
- `max_time` : temps de préparation + cuisson/repos ≤ N minutes ;
- `sort=recent` : seulement les recettes **consultées** par l'utilisateur, la plus récente d'abord ;
- `sort=forgotten` : jamais cuisinées d'abord, puis la date de dernière cuisine la plus ancienne ;
- `sort=random`.

**Alternative écartée** : modifier `RecipeSearch` upstream ; filtrer côté client (pagination fausse).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Filtres de l'accueil gardés en mémoire, pas dans l'URL
**Choix** : les filtres vivent dans un état du module (`vue3/src/fork/homeFilters.ts`). Revenir d'une recette retrouve
la même recherche ; un rechargement repart de zéro. Ils restent propres à l'appareil.
**Alternative écartée** : les mettre dans l'URL (il faudrait recharger les noms des aliments et mots-clés).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Bandeau du plan de repas sur l'accueil : desktop seulement
**Contexte** : le réglage upstream `start_showMealPlan` (activé par défaut) affiche le plan de la semaine sur l'accueil.
SPEC.md : le plan de repas sert sur ordinateur.
**Choix** : le bandeau reste affiché sur desktop (≥ 960 px) si le réglage est actif, jamais sur téléphone, où l'accueil
commence par la recherche.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Vue recette du fork
**Choix** :
- `ForkRecipeView` remplace la vue upstream, sauf en impression (mise en page upstream conservée).
- Les ingrédients sont en haut. Une recette dont plusieurs étapes ont des ingrédients les garde groupés par étape
  (en-têtes) ; sinon, une seule liste. Les étapes n'affichent que le texte, dont les quantités suivent les portions
  (gabarits upstream `{{ ingredients[0] }}`, `{{ scale(100) }}`).
- Les étapes avec sous-recette ou fichier gardent l'affichage upstream (`StepView`). Le menu ⋮ upstream (modifier,
  plan, partage…), les propriétés et l'activité (note, commentaire) sont conservés.
- Le Wake Lock est demandé sur la vue recette (comme upstream) et en mode cuisine ; un refus du navigateur est ignoré.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Mode cuisine en page plein écran
**Choix** : une route `/recipe/:id/cook?servings=N` (méta `forkFullscreen`, qui masque l'en-tête, le tiroir et la barre
du bas). Le retour arrière du téléphone ramène à la recette. Un premier écran « Préparez les ingrédients » liste tout
quand la recette a plusieurs étapes. Ensuite, chaque étape rappelle ses propres ingrédients, sauf pour une liste unique
(déjà vue au premier écran). Balayage gauche/droite, deux boutons de 56 px, flèches du clavier sur desktop.
**Alternative écartée** : un dialogue plein écran (pas d'URL, retour arrière qui quitte la recette).
**Réversible ?** Oui.

## 2026-10-20 — M2 — Feuille « Ajouter aux courses »
**Choix** :
- tous les ingrédients sont cochés, sauf les aliments marqués « jamais en courses » (sel, eau…), décochés et signalés ;
- les ingrédients sans aliment (titres, texte libre) ne sont pas proposés ;
- les portions de la recette sont reprises, et ajustables dans la feuille ;
- les articles vont dans la liste du foyer (aucune liste nommée) ; les sous-recettes sont ajoutées comme upstream.

**Alternative écartée** : cocher aussi les « jamais en courses » (le critère dit « tous cochés », mais ce drapeau
existe justement pour ne pas les acheter).
**Réversible ?** Oui. À valider par Alex.

## 2026-10-20 — M2 — Liste de courses du fork
**Choix** :
- l'affichage est refait (`ForkShoppingList.vue`) sur le `ShoppingStore` upstream (chargement, synchro, annulation) ;
- groupement par rayon dans l'ordre du magasin choisi, sinon alphabétique (M3 apporte l'ordre générique). Le groupe
  « Sans rayon » vient **en dernier** : en magasin, le parcours compte d'abord ;
- un tap sur la ligne coche tous les articles de l'aliment ; le bouton ⋮ ouvre le dialogue upstream (quantités,
  report, rayon) ; « Vue détaillée » (menu ⋮ de la page) rend la vue upstream complète ;
- l'ajout rapide est en haut de la liste, au-dessus des rayons ;
- synchro : la boucle upstream (5 s par défaut), plus une synchro immédiate au retour sur l'écran.

**Réversible ?** Oui.

## 2026-10-20 — M2 — Correctif upstream dans la file de synchro des courses
**Contexte** : `ShoppingStore._replaySyncQueue` envoie toutes les requêtes en attente en parallèle. Cocher puis annuler
vite envoie « coché » et « décoché » pour le même article, dans un ordre d'arrivée non garanti : la base pouvait garder
l'article coché (constaté par les tests de parcours). `splice(index)` retirait aussi le mauvais élément de la file.
**Choix** : correctif minimal et commenté dans le store : la file est fusionnée (dernier état par article) avant envoi,
et les requêtes terminées sont retirées par identité. À proposer upstream.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Tests de parcours dans `verify.sh --ui`
**Choix** : `scripts/fork/ui/flows.mjs` clique les parcours P1 à P4 sur un téléphone simulé (recherche, filtres,
portions, mode cuisine, balayage, ajout aux courses, coche, annulation, ajout rapide, synchro depuis un autre appareil,
message de fin) et remet les données en l'état. `verify.sh --ui` le lance après les captures.
**Réversible ?** Oui.

## 2026-10-20 — M2 — Photos du jeu de démo générées localement
**Choix** : `dev_seed.py` dessine une photo par recette avec Pillow (assiette vue de dessus), pour juger les grandes
cartes et la vue recette. Aucune image externe.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Thème « système » sans migration
**Contexte** : DESIGN.md veut le thème du système par défaut, forçable en clair ou en sombre. Le champ upstream
`UserPreference.theme` n'a pas de valeur « système », et en ajouter une créerait une migration dans `cookbook/`.
**Choix** : le fork réinterprète des valeurs existantes. `TANDOOR` (défaut upstream) suit le système, `TANDOOR_DARK`
force le sombre, `FLATLY` (valeur héritée, ignorée par vue3 et par `theming_tags`) force le clair. Code :
`vue3/src/fork/theme.ts`.
**Alternative écartée** : un modèle de préférences dans `kitchen/` (plus lourd pour un simple choix), ou un réglage par
appareil (localStorage), qui ne suivrait pas l'utilisateur d'un appareil à l'autre.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Primaire claire assombrie
**Contexte** : la primaire claire `#C2552D` donne 4,28:1 sur la surface et 3,89:1 sur `surface-variant`, sous 4,5:1.
**Choix** : `#AF4A26` (5,17:1 sur la surface, 4,7:1 sur `surface-variant`, 5,48:1 avec du texte blanc). Les autres
tokens passent tels quels.
**Alternative écartée** : garder `#C2552D` et ne pas l'employer pour du texte (règle impossible à tenir avec Vuetify).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Icônes Font Awesome conservées
**Contexte** : DESIGN.md cite Material Design Icons « déjà dans Vuetify ». En réalité, le projet n'embarque que
Font Awesome (`defaultSet: 'fa'`), et MDI n'est pas installé.
**Choix** : garder Font Awesome (style plein), déjà utilisé partout. Ajouter `@mdi/font` serait une dépendance de plus,
et il faudrait de toute façon reprendre toutes les icônes.
**Alternative écartée** : migrer vers MDI outlined en M1.
**Réversible ?** Oui. À valider par Alex.

## 2026-10-20 — M1 — Couleur d'en-tête
**Contexte** : l'en-tête upstream prend `navBgColor` (utilisateur ou espace), sable `#ddbf86` par défaut, hors tokens.
**Choix** : la valeur par défaut upstream est remplacée par le token `surface` avec un contour fin. Une couleur choisie
explicitement par l'utilisateur ou l'espace est respectée.
**Alternative écartée** : ignorer totalement `navBgColor` (retire une fonction upstream).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Entrées de la barre du bas et de « Plus »
**Contexte** : DESIGN.md fixe 4 entrées : Recettes, Courses, Ajouter, Plus.
**Choix** :
- « Recettes » mène à l'accueil actuel (StartPage), que M2 refera.
- « Plus » contient : plan de repas, aliments, recherche, livres, garde-manger, base de données, réglages, puis les
  entrées des plugins. La recherche y reste tant que l'accueil n'a pas de champ de recherche (M2). Les doublons arrivent
  en M3.
- Sur mobile, le « + » de l'en-tête est masqué (doublon d'« Ajouter »).

Le tiroir desktop gagne une entrée « Aliment » directe, et « Home » devient « Recettes » (traduit).
**Alternative écartée** : garder le plan de repas dans la barre du bas (5 entrées).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Le 403 sur `/api/view-log/`
**Contexte** : AUDIT.md signalait un 403 à l'ouverture d'une recette, et sur le plan de repas en desktop.
**Constat** : ce n'est pas un bug de permission. Les captures n'injectaient qu'un cookie `sessionid`, sans cookie
`csrftoken`, et DRF refusait donc les POST (CSRF). Un vrai utilisateur reçoit ce cookie en se connectant.
**Choix** :
- l'outil de captures obtient le cookie CSRF comme un vrai navigateur, sur le formulaire de connexion ;
- côté app, l'appel `view-log` (secondaire) est rendu silencieux en cas d'échec, au plus près de l'appel
  (`RecipeViewPage.vue`).

**Alternative écartée** : exempter l'endpoint du CSRF (affaiblit la sécurité).
**Réversible ?** Oui.

## 2026-10-20 — M1 — Page de connexion stylée par une feuille du fork
**Contexte** : la connexion est un template Django Bootstrap, avec un thème upstream minifié.
**Choix** : une feuille `kitchen/static/kitchen/login.css` (tokens, sombre via `prefers-color-scheme`, champ d'étoiles
statique en sombre) est chargée par une ligne dans `cookbook/templates/account/login.html`. Les sélecteurs sont
renforcés pour passer devant les règles `!important` du thème.
**Alternative écartée** : réécrire le template (gros diff upstream), ou surcharger `base.html` pour toutes les pages
Django.
**Réversible ?** Oui.

## 2026-10-20 — M1 — Branche
**Contexte** : CLAUDE.md prévoit `fork/m1-<slug>`, mais la session cloud impose `claude/busy-heisenberg-yf2zw3`.
**Choix** : travailler sur la branche imposée, comme en M0.
**Réversible ?** Oui.

## 2026-10-20 — M0 — Propositions M0 validées
**Contexte** : la session M0 a proposé des ajustements pour M1 à M5 (fin de ROADMAP.md). Alex les a toutes acceptées.
**Choix** : les propositions qui changent un critère sont intégrées aux jalons :
- M1 : tiroir dès 960 px, barre du bas avec libellés et hauteur réservée, correction ou contournement des deux erreurs
  JS upstream, captures fiables (écran visible, reproductibles, publication 360 px) ;
- M2 : la synchro automatique existante suffit pour voir les modifications de l'autre membre du foyer ;
- M5 : CI GitHub Actions avec `verify.sh`.

Les notes d'implémentation (réutiliser `ShoppingStore`, un `Supermarket` unique pour l'ordre des rayons,
`Space.food_inherit`, `ModelMergeDialog`, endpoint `kitchen/` sans stock pour P1, prétraitement branché au collage et à
l'import) restent dans la section « Propositions M0 ».
**Alternative écartée** : laisser chaque session de jalon trancher au cas par cas.
**Réversible ?** Oui.

## 2026-10-20 — M0 — Branche de travail imposée par la session cloud
**Contexte** : la règle du fork demande une branche `fork/m0-<slug>`, mais la session cloud impose de pousser sur
`claude/gifted-cerf-5458vi` et interdit toute autre branche sans permission.
**Choix** : le jalon M0 est développé sur `claude/gifted-cerf-5458vi`, partie de `origin/main` ; la PR vise `main`.
**Alternative écartée** : créer `fork/m0-socle` (refusé par la configuration de la session).
**Réversible ?** Oui : la branche peut être renommée avant fusion.

## 2026-10-20 — M0 — Libellé des captures finales
**Contexte** : la consigne de la session demande `verify.sh --ui m1 --publish` comme porte finale, alors que le skill
prévoit le libellé du jalon (`m0`).
**Choix** : la porte finale est lancée avec le libellé `m1`, comme demandé. M0 ne change rien de visible : ces captures
sont identiques à `m0-baseline`, et M1 les écrasera.
**Alternative écartée** : libellé `m0`.
**Réversible ?** Oui.

## 2026-10-20 — M0 — pytest avec `recipes.test_settings`
**Contexte** : avec `DJANGO_SETTINGS_MODULE=recipes.settings` exporté, pytest-django ignore `pytest.ini`. Les
connecteurs externes démarrent alors un thread qui bloque la sortie de pytest, et une quinzaine de tests échouent.
**Choix** : `verify.sh` passe `--ds recipes.test_settings`, ce qui reprend la configuration de test d'upstream.
**Alternative écartée** : modifier `pytest.ini` ou `recipes/settings.py` (fichiers upstream).
**Réversible ?** Oui.

## 2026-10-20 — M0 — `kitchen/` déclarée dans INSTALLED_APPS plutôt qu'en plugin
**Contexte** : le système de plugins de Tandoor charge des apps depuis `recipes/plugins/`, un dossier ignoré par git
(voir AUDIT.md § 5).
**Choix** : `kitchen/` est une app à la racine, ajoutée explicitement dans `INSTALLED_APPS`. Cela coûte une ligne de
diff upstream. Elle est versionnée et testée avec le fork.
**Alternative écartée** : un plugin, qui serait hors du dépôt, sans tests du fork et sans possibilité de refondre l'UI.
**Réversible ?** Oui.

## 2026-10-20 — cadrage — M2 aligné sur les parcours de SPEC.md
**Contexte** : la première version de M2 ne couvrait pas tous les parcours retenus dans SPEC.md :
- P1, la recherche par ingrédients sous la main ;
- P3, l'envoi aux courses en décochant ce qu'on a ;
- le mode cuisine « une étape à la fois ».

**Choix** : M2 est réécrit autour des parcours P1 à P4, ce qu'Alex a validé dans la PR de cadrage. Le Wake Lock est
gardé (peu coûteux), même s'il n'a pas été cité comme prioritaire. « Ingrédients cochables » est retiré : ce n'était
pas un besoin exprimé.
**Alternative écartée** : garder M2 générique et traiter ces parcours plus tard.
**Réversible ?** Oui.

## 2026-10-20 — cadrage — Liste unique d'ingrédients
**Contexte** : Alex veut une seule liste d'ingrédients. Or Tandoor stocke les ingrédients par étape.
**Choix** : pour les recettes créées dans le fork, tous les ingrédients sont stockés dans la première étape, et les
étapes suivantes n'ont que du texte. La vue recette affiche alors une liste unique en haut. Les recettes importées
gardent leur découpage d'origine. Aucun changement de modèle.
**Alternative écartée** : fusionner tous les ingrédients à l'affichage pour toutes les recettes (refusé par Alex), ou
un champ dédié dans `kitchen/` (inutile).
**Réversible ?** Oui.

## 2026-10-20 — cadrage — Reconnaissance des ingrédients en français hors du parseur upstream
**Contexte** : le parseur `cookbook/helper/ingredient_parser.py` reconnaît mal les unités, articles et pluriels français.
**Choix** : ne pas modifier le parseur. Le fork ajoute deux choses :
- des alias d'unités, via les automatisations `UNIT_ALIAS` existantes, semées par `kitchen/` ;
- un prétraitement dans `kitchen/`, appelé avant le parseur.

Le jeu d'exemples en pytest fait foi.
**Alternative écartée** : patcher le parseur upstream (conflits de merge à chaque release). Si un cas ne peut être traité
qu'en amont, proposer un patch upstream plutôt que de diverger.
**Réversible ?** Oui.

## 2026-10-20 — kit — Bases du fork
**Contexte** : fork personnel destiné à rester synchronisable avec Tandoor.
**Choix** : base `master` (releases) ; aucune migration dans `cookbook/` ; extensions backend dans l'app `kitchen/` ;
dépendances Python via uv ; contrôles UI headless hors de `vue3/` (`scripts/fork/ui`).
**Alternative écartée** : suivre `develop` (instable, tests parfois non lançables).
**Réversible ?** Oui.
