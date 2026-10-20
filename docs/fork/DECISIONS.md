# Décisions

Journal des choix faits en autonomie, à relire par Alex. Le plus récent en haut.
Format : `## AAAA-MM-JJ — Mx — titre` puis **Contexte**, **Choix**, **Alternative écartée**, **Réversible ?**

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
connecteurs externes démarrent alors un thread qui bloque la sortie de pytest, et une vingtaine de tests échouent.
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
