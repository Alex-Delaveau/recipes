# Décisions

Journal des choix faits en autonomie, à relire par Alex. Le plus récent en haut.
Format : `## AAAA-MM-JJ — Mx — titre` puis **Contexte**, **Choix**, **Alternative écartée**, **Réversible ?**

## 2026-10-20 — cadrage — M2 non modifié, ajustements proposés
**Contexte** : SPEC.md retient deux parcours que M2 ne couvre pas explicitement :
- P1, la recherche par ingrédients sous la main ;
- P3, l'envoi aux courses en décochant ce qu'on a.

Le mode cuisine voulu est en outre « une étape à la fois ».
**Choix** : seuls M3 et M4 ont été réécrits, comme demandé. Proposition pour M2, à valider par Alex :
- ajouter le filtre par ingrédients et les raccourcis « récentes / pas faites depuis longtemps / au hasard » ;
- ajouter la feuille « Ajouter aux courses » avec décochage ;
- passer le mode cuisine en une étape par écran.

Le Wake Lock est gardé (peu coûteux), même s'il n'a pas été cité comme prioritaire.
**Alternative écartée** : réécrire M2 dès maintenant sans validation.
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
