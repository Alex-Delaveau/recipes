# Guide : piloter le fork avec Claude Code sans être devant le PC

## Le principe

Tu décides du **quoi** et de ce qui compte comme « fini » ; Claude Code décide du **comment**.
- Toi : un entretien de cadrage au départ (SPEC.md, DESIGN.md), puis une relecture de PR par jalon, depuis le téléphone.
- Claude : découpe chaque jalon en sous-tâches (écrites dans PROGRESS.md), code, vérifie, se fait relire par deux
  subagents, ouvre la PR avec les captures avant/après.
- Les garde-fous sont des scripts, pas des promesses : `verify.sh` (règles du fork, typage, build, tests, contrôles mobiles)
  et l'évaluateur `/goal` qui empêche la session de s'arrêter tant que la condition n'est pas remplie.

Les sessions tournent dans le cloud d'Anthropic (VM Ubuntu avec Python, uv, Node, yarn, Docker, Postgres) : ton PC
peut rester éteint. Tu suis et relances tout depuis l'app Claude (onglet Code) et l'app GitHub.

## 1. Créer le dépôt (≈ 15 min, au PC)

Un dépôt **privé indépendant** plutôt qu'un fork GitHub : les PR ne risquent pas de viser le dépôt de Tandoor, et
la synchronisation se fait par git de toute façon.

1. Sur GitHub, crée un dépôt privé vide, par exemple `tandoor-perso`.
2. Dans un terminal (WSL ou Mac) :
   ```bash
   git clone https://github.com/TandoorRecipes/recipes.git tandoor-perso && cd tandoor-perso
   git remote rename origin upstream
   git remote add origin git@github.com:<toi>/tandoor-perso.git
   git switch -c main upstream/master          # on suit les releases, pas develop
   unzip ~/Downloads/tandoor-fork-kit.zip -d .  # ce kit, à la racine du dépôt
   cat docs/fork/gitignore.append >> .gitignore
   chmod +x scripts/fork/*.sh
   git add -A && git commit -m "chore(fork): add Claude Code fork kit"
   git push -u origin main
   ```
3. Sur GitHub, dans les réglages du dépôt : branche par défaut `main`, et une règle de protection sur `main`
   (PR obligatoire, pas de push forcé). C'est le vrai filet de sécurité.
4. Installe la [Claude GitHub App](https://github.com/apps/claude) sur ce dépôt (nécessaire pour Auto-fix et les projets).

Optionnel, pour tester en local : `scripts/fork/setup.sh` puis `scripts/fork/serve.sh start` → http://127.0.0.1:8000, `demo` / `demo`.

## 2. Créer l'environnement cloud (≈ 5 min)

Sur claude.ai/code, sélecteur d'environnement sous la zone de message → nouvel environnement `tandoor-fork` :
- Accès réseau : **Trusted** (registres npm/PyPI, GitHub, Ubuntu ; suffisant, les captures utilisent un Chromium livré par npm).
- Script de configuration (mis en cache, accélère chaque session) :
  ```bash
  #!/bin/bash
  set -e
  apt-get update -q
  apt-get install -y -q libldap2-dev libsasl2-dev libxmlsec1-dev pkg-config gettext
  uv python install 3.12
  ```
- Aucune variable d'environnement ni secret nécessaires.

Le reste (dépendances Python avec uv, yarn, base SQLite, utilisateur `demo`) est fait à chaque démarrage par le hook
`SessionStart` du dépôt (`scripts/fork/session_start.sh`), uniquement dans le cloud.

## 3. Phase 0 : cadrage (toi présent, 30–45 min)

Nouvelle session cloud sur le dépôt, prompt 1 de `PROMPTS.md`. Claude regarde l'UI actuelle, te pose ses questions,
remplit SPEC.md et DESIGN.md, ajuste M3/M4 et ouvre une PR. Relis-la attentivement : **c'est l'étape qui compte le
plus**. Tout ce qui n'est pas écrit là sera décidé par Claude seul. Fusionne.

## 4. Jalons en autonomie

Pour chaque jalon, depuis le téléphone :
1. App Claude → Code → nouvelle session sur `tandoor-perso`, environnement `tandoor-fork`, mode **Auto**.
2. Colle le prompt 2 de `PROMPTS.md` avec le bon jalon. Tu peux fermer l'app.
3. Notification à la fin. Ouvre la PR : résumé, critères cochés, captures mobiles avant/après, décisions à valider.
4. Retours : commente la PR (avec Auto-fix activé dans la session, Claude les traite) ou utilise le prompt 4.
5. Fusionne, puis lance le jalon suivant.

Commence par **M0** puis **M1** un par un : c'est là que tu vérifies que le cadre tient. Ensuite seulement,
le mode marathon (prompt 3) pour enchaîner M2→M4 pendant une absence longue.

Si l'onglet **Projects** est disponible sur ton compte (bêta Pro/Max), tu peux y créer un projet sur ce dépôt et lui
donner « Exécute la feuille de route docs/fork/ROADMAP.md jalon par jalon, une PR par jalon » : il lance et suit les
sessions pour toi, avec une vue d'ensemble de ce qui attend ta relecture.

## 5. Synchroniser avec Tandoor

À chaque nouvelle release (onglet Releases du dépôt Tandoor) : prompt 5. Tu peux aussi en faire une tâche planifiée
mensuelle (routine) depuis claude.ai/code.

## 6. Mettre en production (M5)

M5 prépare l'image Docker sur GHCR et `DEPLOY.md`. La bascule sur le homelab reste manuelle et à faire toi-même :
sauvegarde de la base, essai sur une copie, puis changement d'image dans la stack Komodo. Les ajouts du fork vivent
dans leurs propres tables (`kitchen/`) : revenir à l'image upstream reste possible.

## Ce qui peut coincer

- **Limites d'usage** : les sessions cloud consomment ton forfait comme les autres ; un jalon de refonte est long.
  Si la limite est atteinte, l'objectif `/goal` se met en pause et reprend à la réinitialisation.
- **Session expirée** après inactivité : rouvre-la depuis claude.ai/code, la conversation est conservée.
- **Le classifieur du mode Auto bloque une action** : la session continue autrement ; c'est visible dans le fil.
- **Claude part dans une mauvaise direction visuelle** : c'est que DESIGN.md est trop vague. Corrige-le (ou joins une
  capture d'une appli que tu aimes dans la session) plutôt que de corriger écran par écran.
- **Upstream change beaucoup une page refaite** : le sync le signale dans sa PR ; la règle est « logique upstream,
  présentation du fork ».
