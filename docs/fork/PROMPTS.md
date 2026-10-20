# Prompts à copier-coller

Tous se lancent dans une **session cloud** sur le dépôt du fork (claude.ai/code, onglet Code de l'app mobile,
ou `claude --cloud "..."` depuis un terminal), environnement `tandoor-fork`, **mode Auto** sauf mention contraire.

---

## 1. Entretien de cadrage (toi présent, 30–45 min, une seule fois)

Mode : Plan (lecture seule) pour la première partie, puis Auto pour écrire les fichiers.

```text
Tu prépares un fork personnel de Tandoor que des sessions Claude Code vont ensuite développer seules.
Lis CLAUDE.md et tout docs/fork/. Lance scripts/fork/verify.sh --quick --ui m0-preview et regarde les captures
mobiles .fork/screens/m0-preview/*-mobile.jpg pour connaître l'UI actuelle.

Ensuite interroge-moi en détail avec l'outil AskUserQuestion, par petits lots de questions, pour compléter
docs/fork/SPEC.md et valider docs/fork/DESIGN.md. Creuse les parties difficiles, pas l'évident :
- ce qui me gêne concrètement aujourd'hui dans l'organisation des aliments et dans la création de recettes
  (montre-moi ce que Tandoor sait déjà faire, je ne le connais peut-être pas) ;
- mes 3 à 5 parcours prioritaires sur téléphone, pas à pas ;
- la direction visuelle proposée dans DESIGN.md : garder, ajuster, refuser, point par point ;
- ce qui est hors périmètre, et comment je saurai que le fork est réussi.

Quand tout est couvert : remplis SPEC.md, mets DESIGN.md à jour, remplace dans ROADMAP.md les critères de M3 et M4
par ceux qui découlent de SPEC.md, puis ouvre une PR « docs: cadrage du fork » vers main du fork.
Ne modifie aucun code.
```

---

## 2. Lancer un jalon en autonomie (le prompt standard)

Remplace `M1` par le jalon voulu. Le `/goal` fait vérifier la fin par un évaluateur séparé : la session continue
tant que la condition n'est pas remplie.

```text
/goal Exécute le jalon M1 de docs/fork/ROADMAP.md en suivant exactement .claude/skills/milestone/SKILL.md, sans me poser de question sauf pour une action irréversible. La condition est remplie quand : (1) la sortie complète de `scripts/fork/verify.sh --ui m1 --publish` affichée dans la conversation se termine par `VERIFY: OK` ; (2) les subagents reviewer et ui-auditor ont été exécutés et leurs points bloquants corrigés ; (3) une PR vers la branche main du fork est ouverte et son URL est affichée ; (4) tous les critères de M1 sont cochés dans ROADMAP.md, ou les critères non tenus sont expliqués dans la PR. Arrête-toi aussi après 80 tours.
```

---

## 3. Mode marathon (plusieurs jalons d'affilée, absence longue)

À n'utiliser qu'une fois M0 et M1 fusionnés et validés : les jalons suivants s'empilent sur des branches dépendantes.

```text
/goal Exécute successivement les jalons M2, M3 puis M4 de docs/fork/ROADMAP.md en suivant .claude/skills/milestone/SKILL.md pour chacun : une branche et une PR par jalon, chaque branche partant de la précédente si sa PR n'est pas encore fusionnée (indique-le dans la PR). Ne me pose aucune question ; note tes choix dans docs/fork/DECISIONS.md et les questions ouvertes en tête de docs/fork/PROGRESS.md. La condition est remplie quand trois PR sont ouvertes et que la dernière sortie de `scripts/fork/verify.sh --ui` affichée pour chacune se termine par `VERIFY: OK`. Arrête-toi aussi après 200 tours.
```

---

## 4. Corriger après ta relecture

Le plus simple : commenter directement la PR sur GitHub avec **Auto-fix** activé (barre CI de la session) ;
Claude traite les commentaires et pousse les corrections. Sinon, dans la session du jalon :

```text
Voici mes retours sur la PR (captures et test sur téléphone) :
- …
- …
Corrige-les sur la même branche, relance scripts/fork/verify.sh --ui m1 --publish, mets à jour les captures de la PR
et réponds point par point dans un commentaire de PR.
```

---

## 5. Synchroniser avec une nouvelle release Tandoor

```text
/goal Suis .claude/skills/upstream-sync/SKILL.md pour intégrer la dernière release de Tandoor. La condition est remplie quand une PR « Sync upstream <tag> » vers main du fork est ouverte et que la sortie de `scripts/fork/verify.sh --ui sync --publish` affichée dans la conversation se termine par `VERIFY: OK`. Arrête-toi aussi après 60 tours.
```

---

## 6. Faire le point en rentrant

```text
Fais-moi un point en 10 lignes maximum : jalons terminés, PR ouvertes et ce qu'il faut que je teste sur chacune,
décisions de docs/fork/DECISIONS.md à valider, questions en attente dans docs/fork/PROGRESS.md. Ne modifie rien.
```
