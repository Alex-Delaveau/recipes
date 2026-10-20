# Décisions

Journal des choix faits en autonomie, à relire par Alex. Le plus récent en haut.
Format : `## AAAA-MM-JJ — Mx — titre` puis **Contexte**, **Choix**, **Alternative écartée**, **Réversible ?**

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
