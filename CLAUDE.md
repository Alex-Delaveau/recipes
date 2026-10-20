# Fork personnel de Tandoor Recipes

Fork de [TandoorRecipes/recipes](https://github.com/TandoorRecipes/recipes) basé sur `master` (versions stables).
Objectifs : une UI propre, moderne et pensée d'abord pour smartphone ; une meilleure organisation des aliments ;
une création de recettes plus fluide. Le détail vit dans `docs/fork/` :

- `docs/fork/SPEC.md` : ce qu'on construit (source de vérité produit)
- `docs/fork/DESIGN.md` : direction visuelle, tokens, règles mobile
- `docs/fork/ROADMAP.md` : jalons et critères d'acceptation
- `docs/fork/DECISIONS.md` : décisions prises et hypothèses (à relire par Alex)
- `docs/fork/PROGRESS.md` : journal de travail, plan du jalon en cours

## Stack

- Backend : Django 5 + DRF (`cookbook/`, réglages dans `recipes/settings.py`), SQLite en dev.
- Frontend : Vue 3 + Vuetify 3 + Pinia + TypeScript dans `vue3/src`, build Vite vers `cookbook/static/vue3`.
- Client API TypeScript **généré** dans `vue3/src/openapi` : ne jamais l'éditer à la main. Pour le régénérer :
  `scripts/fork/serve.sh start` puis `cd vue3/src/openapi && npx --yes @openapitools/openapi-generator-cli generate -g typescript-fetch -i http://127.0.0.1:8000/openapi/ -t templates --global-property apiDocs=false,modelDocs=false`
  (équivalent de `scripts/generate_api_client.py`, nécessite Java).
- Traductions : vue-i18n, fichiers `vue3/src/locales/*.json`. Toute nouvelle chaîne a une clé dans `en.json` **et** `fr.json`.

## Commandes

- `scripts/fork/setup.sh` : installe tout (uv pour Python, yarn pour vue3), migre, crée l'utilisateur `demo`/`demo`
- `scripts/fork/serve.sh start|stop|restart` : build du front + serveur Django sur http://127.0.0.1:8000
- `scripts/fork/verify.sh --quick` : règles du fork + vue-tsc + build (rapide, pendant le code)
- `scripts/fork/verify.sh` : idem + tests backend (~2 min)
- `scripts/fork/verify.sh --ui <label> [--publish]` : + captures mobile/desktop et contrôles mobiles
- Python : toujours via `uv` / `.venv/bin/python`, jamais `pip` global. Exporter `DJANGO_SETTINGS_MODULE=recipes.settings`.

La porte de qualité est la dernière ligne de `verify.sh` : `VERIFY: OK`. Un jalon n'est jamais « fini » sans elle.

## Règles du fork (pour rester synchronisable avec upstream)

- IMPORTANT : aucune migration dans `cookbook/migrations/`. Tout nouveau modèle ou champ va dans l'app Django du fork
  `kitchen/` (modèles d'extension en OneToOne/ForeignKey vers les modèles `cookbook`). `verify.sh` le contrôle.
- Modifier le comportement existant le moins possible côté backend ; préférer de nouveaux endpoints dans `kitchen/`.
- Côté front, passer d'abord par le thème Vuetify, les tokens et les composants partagés avant de retoucher page par page.
- Ne pas reformater, renommer ni déplacer du code upstream qu'on ne modifie pas réellement (diffs minimaux = merges faciles).
- Nouveaux composants spécifiques au fork dans `vue3/src/fork/` quand c'est possible.
- Ratchets : le nombre d'erreurs vue-tsc ne doit jamais augmenter ; aucun test ne doit casser hors de la liste de
  `docs/fork/baseline/pytest-failures.txt`. On ne relève jamais une baseline ; on peut la baisser (`--update-baseline`).
- Mobile d'abord : chaque écran touché doit passer à 360 px de large sans défilement horizontal, avec des zones
  tactiles d'au moins 44 px. Une page refaite passe à `"strict": true` dans `scripts/fork/ui/routes.json`.

## Git

- Une branche par jalon : `fork/m<N>-<slug>`. Commits petits, messages en anglais (style conventionnel).
- Les PR visent la branche `main` **du fork**, jamais `TandoorRecipes/recipes`. Ne jamais pousser sur `main` ni forcer un push.
- Le code, les commentaires et les messages de commit sont en anglais ; la doc `docs/fork/` est en français.

## Travail en autonomie

Alex n'est généralement pas devant l'écran pendant un jalon.
- Ne pas poser de question pour un choix réversible : prendre la décision la plus raisonnable au regard de SPEC/DESIGN,
  la noter dans `docs/fork/DECISIONS.md` (contexte, choix, alternative) et continuer.
- S'arrêter et demander seulement pour une action irréversible ou hors périmètre (suppression de données, changement
  du modèle de données upstream, dépendance lourde, sortie du jalon en cours).
- Tenir `docs/fork/PROGRESS.md` à jour (plan du jalon, avancement, blocages) : c'est ce qu'Alex lit en rentrant.
- Pour une exploration large du code, utiliser un subagent afin de garder le contexte principal propre.

## Pièges connus

- `runserver` exige `DEBUG=1` en dev (sinon erreur ALLOWED_HOSTS) : passer par `serve.sh`.
- La compilation de `python-ldap` / `xmlsec` demande `libldap2-dev libsasl2-dev libxmlsec1-dev pkg-config` (géré par `setup.sh`).
- La page de connexion de master est `/accounts/login/` (template Django), pas une page Vue.
- Dans les captures « pleine page », la barre de navigation fixe du bas apparaît au milieu de l'image : c'est un artefact.
- Upstream `develop` peut être cassé (tests non lançables) : on suit `master` et les tags de release.
- Lors d'un compactage du contexte, conserver : le jalon en cours, la liste des fichiers modifiés et le dernier résultat de `verify.sh`.
