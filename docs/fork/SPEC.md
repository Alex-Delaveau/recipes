# Spécification du fork

État : **à compléter lors de l'entretien de cadrage** (prompt 1 de `docs/fork/PROMPTS.md`).
Ce fichier est la source de vérité produit : en cas de doute pendant un jalon, c'est lui qui tranche.

## Utilisateur et contexte d'usage
- Utilisateur principal : Alex (un foyer). Usage majoritairement sur smartphone, en cuisine et en courses.
- Instance auto-hébergée sur le homelab, données réelles existantes à préserver.
- _À préciser : autres membres du foyer ? usage desktop (planification) ? langue : français._

## Problèmes à résoudre (tel qu'exprimé)
1. UI jugée datée et peu adaptée au smartphone → la rendre propre, moderne, responsive.
2. Organisation des aliments insatisfaisante → _à détailler : ce qui gêne concrètement aujourd'hui._
3. Création de recettes laborieuse → _à détailler : à quelle étape, sur quel appareil._

## Parcours prioritaires
_À remplir : 3 à 5 parcours décrits pas à pas, avec l'appareil utilisé._

## Organisation des aliments — attendu
_À remplir : comment Alex veut ranger, retrouver et maintenir ses aliments (rayons, hiérarchie, stocks, doublons…)._

## Création de recettes — attendu
_À remplir : sources des recettes (saisie, URL, photo, import Samsung Food…), informations indispensables, ce qui doit être rapide._

## Hors périmètre
- Fonctions upstream non utilisées : _à lister (elles restent intactes, on ne les refait pas)._
- Pas de changement du modèle de données upstream ; extensions uniquement dans `kitchen/`.

## Contraintes
- Rester synchronisable avec les releases upstream (`master`).
- Mobile d'abord : 360 px de large minimum, utilisable à une main.

## Critères de succès
_À remplir : comment Alex saura que le fork vaut le coup (ex. créer une recette en < 2 min sur téléphone)._
