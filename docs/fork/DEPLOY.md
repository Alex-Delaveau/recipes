# Déployer le fork sur le homelab

La bascule reste manuelle : ce document donne les étapes, dans l'ordre. Chaque commande a été jouée dans la session M6
sur une stack identique (image upstream `2.6.15`, puis image du fork construite localement, PostgreSQL 16).

Principe : le fork utilise **le Dockerfile, le `boot.sh` et la base de Tandoor sans changement**. Ses ajouts vivent dans
leurs propres tables (`kitchen_*`). On passe donc de l'image upstream à celle du fork (et retour) en changeant **une
seule variable** de la stack : `TANDOOR_IMAGE`.

## 1. L'image

- Publiée sur GHCR par le workflow `Fork image` (`.github/workflows/fork-image.yml`) à chaque fusion dans `main`, ou à la
  demande (onglet Actions › Fork image › Run workflow).
- Étiquettes :
  - `ghcr.io/alex-delaveau/recipes:<release upstream>-fork.<n>`, par exemple `2.6.15-fork.97`. `<release>` est la
    version de Tandoor sur laquelle le fork est basé, `<n>` augmente à chaque fusion. **C'est celle à mettre en
    production** : elle ne bouge pas toute seule ;
  - `fork-latest` (dernière image de `main`) et `sha-<commit>`.

  Le résumé du workflow affiche l'étiquette produite. `scripts/fork/image_tag.sh` la calcule en local.
- Une seule architecture, `linux/amd64`. Si le homelab est en ARM, ajouter `linux/arm64` dans `platforms` du workflow
  (build nettement plus long, par émulation).
- Le paquet GHCR est **privé** au premier envoi. Deux possibilités :
  - le rendre public (GitHub › Packages › `recipes` › Package settings › Change visibility) ;
  - ou, dans Komodo, ajouter un compte de registre `ghcr.io` avec un jeton GitHub (classic) limité à `read:packages`.

## 2. La stack Komodo

Fichiers : `docs/fork/deploy/compose.yaml` et `docs/fork/deploy/fork.env.example`. C'est la stack « plain » d'upstream
(`docs/install/docker/plain/docker-compose.yml`) avec trois différences :
- l'image web vient de `TANDOOR_IMAGE` (obligatoire) ;
- le port publié vient de `TANDOOR_HTTP_PORT` (80 par défaut) ;
- PostgreSQL a un contrôle de santé, et le web attend qu'il réponde.

Dans Komodo :
1. Stack existante : remplacer son compose par `compose.yaml`, ou y reporter seulement ces trois différences. Garder
   les mêmes dossiers `./postgresql` et `./mediafiles`, et les mêmes variables (`SECRET_KEY`, `POSTGRES_*`…).
2. Dans l'environnement de la stack, ajouter `TANDOOR_IMAGE` :
   - avec l'image upstream actuelle d'abord (par exemple `vabene1111/recipes:2.6.15`), pour vérifier que rien ne
     change ;
   - puis l'image du fork, à l'étape 5.
3. Ne pas utiliser `latest` ni `fork-latest` en production : une mise à jour doit être un changement d'étiquette voulu.

Règle de version : l'image du fork et l'image upstream de retour doivent être de **la même release** (ou plus récente
pour l'upstream). Une image upstream plus ancienne que la base ne connaît pas toutes ses migrations.

## 3. Sauvegarde avant bascule

Depuis le dossier de la stack, sur le homelab (ou avec la commande « Execute » de Komodo) :

```sh
mkdir -p backups
docker compose exec -T db_recipes sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/tandoor-before-fork.dump
tar czf backups/mediafiles-before-fork.tgz mediafiles
ls -la backups   # le dump ne doit pas faire 0 octet
```

Garder ces deux fichiers jusqu'à ce que le fork ait tourné quelques jours sans souci. Les copier hors du serveur.

## 4. Essai sur une copie

On démarre une deuxième stack, isolée, sur la sauvegarde, avec l'image du fork. La production n'est pas touchée.

1. Créer une stack Komodo `tandoor-essai` (ou un dossier à part) avec le même `compose.yaml` et un `.env` copié de la
   production, en changeant :
   - `TANDOOR_IMAGE=ghcr.io/alex-delaveau/recipes:<release>-fork.<n>` ;
   - `TANDOOR_HTTP_PORT=8081` (un port libre) ;
   - `ALLOWED_HOSTS` si besoin (adresse de l'essai).
2. Démarrer **seulement la base**, restaurer le dump et les médias, puis démarrer le web. Ici, la stack de
   production est dans `../tandoor` :

   ```sh
   docker compose up -d db_recipes
   until docker compose exec -T db_recipes sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; do sleep 2; done
   docker compose exec -T db_recipes sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < ../tandoor/backups/tandoor-before-fork.dump
   tar xzf ../tandoor/backups/mediafiles-before-fork.tgz
   docker compose up -d
   docker compose logs -f web_recipes   # attendre "Applying kitchen.0001_aisles_and_duplicates... OK" puis "Starting gunicorn"
   ```

3. Sur le téléphone, ouvrir `http://<homelab>:8081` et parcourir : une recette (mode cuisine), la liste de courses,
   les aliments, « Ajouter › Saisir une recette ». Se connecter avec ses comptes habituels.
4. Arrêter et supprimer l'essai : `docker compose down -v`, puis supprimer le dossier.

## 5. Bascule

1. Refaire la sauvegarde de l'étape 3 (juste avant, pour ne rien perdre de ce qui a changé depuis l'essai).
2. Dans l'environnement de la stack de production : `TANDOOR_IMAGE=ghcr.io/alex-delaveau/recipes:<release>-fork.<n>`.
3. Redéployer la stack (Komodo › Deploy). Au démarrage, `boot.sh` applique les migrations, dont celles du fork
   (`kitchen.0001…`), puis lance le serveur.
4. Vérifier : la page s'ouvre, les recettes et la liste de courses sont là, la console du navigateur ne montre pas
   d'erreur. `docker compose exec -T web_recipes /opt/recipes/venv/bin/python manage.py showmigrations kitchen` doit
   afficher `[X]` partout.

Mises à jour suivantes : changer l'étiquette dans `TANDOOR_IMAGE` et redéployer. Pour une nouvelle release Tandoor
(après la PR de synchronisation upstream), refaire les étapes 3 et 4 avant.

## 6. Retour arrière vers l'image upstream

**Attention** : ne pas remettre directement l'image upstream. Les tables du fork référencent les aliments et l'espace
de Tandoor ; tant qu'elles existent, l'image upstream **ne peut plus supprimer** un aliment étendu par le fork (erreur
d'intégrité PostgreSQL, constatée en M6). Il faut d'abord retirer les tables du fork, **avec l'image du fork**.

### Retour arrière propre (garde les données saisies depuis la bascule)

```sh
# 1. avec l'image du fork encore en place : retirer les tables kitchen_*
docker compose exec -T web_recipes /opt/recipes/venv/bin/python manage.py migrate kitchen zero --noinput
# 2. dans Komodo : TANDOOR_IMAGE=vabene1111/recipes:<même release>, puis Deploy
# 3. contrôle : aucune migration en attente
docker compose exec -T web_recipes /opt/recipes/venv/bin/python manage.py migrate --check && echo OK
```

On perd seulement ce que le fork stocke à part : rayon générique choisi, marquage « famille » des aliments, paires
« pas des doublons ». Les recettes, aliments, rayons et courses restent dans les tables de Tandoor.

### Retour arrière par la sauvegarde (si le fork a abîmé quelque chose)

On revient à l'état exact d'avant la bascule. Tout ce qui a été saisi depuis est perdu.

```sh
docker compose down
mv postgresql postgresql-fork && mv mediafiles mediafiles-fork     # gardés de côté, à supprimer plus tard
# remettre l'image upstream AVANT de relancer : sinon le fork redémarre sur la base restaurée
sed -i 's#^TANDOOR_IMAGE=.*#TANDOOR_IMAGE=vabene1111/recipes:<même release>#' .env
docker compose up -d db_recipes
until docker compose exec -T db_recipes sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; do sleep 2; done
docker compose exec -T db_recipes sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < backups/tandoor-before-fork.dump
tar xzf backups/mediafiles-before-fork.tgz
docker compose up -d
docker compose ps --format '{{.Image}}' web_recipes   # doit afficher l'image upstream
```

Puis reporter la même valeur de `TANDOOR_IMAGE` dans l'environnement de la stack Komodo : Komodo réécrit `.env` au
prochain Deploy, et remettrait sinon l'image du fork.

## 7. Ce que la CI garantit

- `Fork verify` (chaque PR vers `main`) :
  - `verify.sh` complet, qui doit finir par `VERIFY: OK` ;
  - `scripts/fork/pg_upgrade_check.sh`, qui crée une base PostgreSQL avec l'image upstream de la release de base et y
    écrit des données. Les migrations du fork sont ensuite appliquées par-dessus. Enfin, le script joue le retour
    arrière de la section 6 : `migrate kitchen zero`, puis l'image upstream qui doit encore supprimer un aliment.
- Pour que la porte bloque vraiment les fusions : GitHub › Settings › Branches › règle sur `main` › « Require status
  checks to pass », cocher `verify.sh`. À faire une fois, après le premier passage du workflow.
- `Fork image` (fusion dans `main`, et PR qui touchent le Dockerfile ou les dépendances) : construction de l'image,
  publication sur GHCR hors PR.
