# Déployer le fork sur le homelab

La bascule reste manuelle : ce document donne les étapes, dans l'ordre. Il suit la stack Komodo réelle `tandoor`
(serveur `VPS-hostinger`, compose dans `Alex-Delaveau/homelab-config`, `stacks/tandoor/compose.yaml`, Nginx Proxy
Manager devant). Chaque commande a été jouée dans la session M6 sur des stacks identiques (mêmes noms de services et de
conteneurs, image upstream `2.6.15`, puis image du fork construite localement, PostgreSQL 16).

Principe : le fork utilise **le Dockerfile, le `boot.sh` et la base de Tandoor sans changement**. Ses ajouts vivent dans
leurs propres tables (`kitchen_*`). On passe de l'image upstream à celle du fork (et retour) en changeant **une seule
variable** de la stack : `TANDOOR_IMAGE`.

## 1. L'image

- Publiée sur GHCR par le workflow `Fork image` (`.github/workflows/fork-image.yml`) à chaque fusion dans `main`, ou à la
  demande (onglet Actions › Fork image › Run workflow).
- Étiquettes :
  - `ghcr.io/alex-delaveau/recipes:<release upstream>-fork.<n>`, par exemple `2.6.15-fork.105`. `<release>` est la
    version de Tandoor sur laquelle le fork est basé, `<n>` augmente à chaque fusion. **C'est celle à mettre en
    production** : elle ne bouge pas toute seule. Le résumé du workflow l'affiche ; `scripts/fork/image_tag.sh` la
    calcule en local ;
  - `fork-latest` (dernière image de `main`) et `sha-<commit>`.
- Une seule architecture, `linux/amd64` (le VPS). Pour un serveur ARM, ajouter `linux/arm64` dans `platforms`.
- Le paquet GHCR est **privé** au premier envoi. Au choix :
  - le rendre public : GitHub › ton profil › Packages › `recipes` › Package settings › Change visibility ;
  - ou déclarer dans Komodo un compte de registre `ghcr.io` (jeton GitHub classic limité à `read:packages`) et le
    sélectionner dans la configuration de la stack.

## 2. Ce qui change dans la stack

### Dans `homelab-config`, `stacks/tandoor/compose.yaml`

Remplacer le fichier par `docs/fork/deploy/compose.yaml`. C'est ton fichier actuel avec quatre différences :

| Élément | Avant | Après | Pourquoi |
|---|---|---|---|
| image web | `ghcr.io/tandoorrecipes/recipes:latest` | `${TANDOOR_IMAGE:-ghcr.io/tandoorrecipes/recipes:2.6.15}` | l'image se choisit dans l'environnement Komodo |
| `container_name` | `tandoor-db`, `tandoor-web` | `${TANDOOR_NAME:-tandoor}-db`, `…-web` | mêmes noms par défaut ; une copie d'essai peut tourner à côté |
| port | `127.0.0.1:8083:80` | `127.0.0.1:${TANDOOR_HTTP_PORT:-8083}:80` | idem |
| attente de la base | `condition: service_started` | contrôle de santé + `service_healthy` | le web attend que PostgreSQL réponde |

Les noms par défaut ne changent pas : NPM continue de joindre `tandoor-web:80` sur `internal-network`.
Ce changement seul ne change pas l'image utilisée : 2.6.15 est ton `latest` actuel (vérifié le 2026-10-21, même
dernière migration `0242`). On peut donc le pousser et redéployer d'abord, pour vérifier que tout reste pareil.

### Dans l'environnement de la stack Komodo

Ajouter une ligne, à l'étape 5 seulement (le reste ne bouge pas) :

```
TANDOOR_IMAGE=ghcr.io/alex-delaveau/recipes:2.6.15-fork.<n>
```

Autres remarques sur la configuration actuelle :
- `poll_for_updates = true` ne fait rien avec une étiquette figée, et c'est voulu. Ne pas mettre `fork-latest` (ni
  `latest`) : une mise à jour doit être un changement d'étiquette voulu.
- `ENABLE_SIGNUP=1` : si le premier compte admin est créé, repasser à `0`.

Règle de version : l'image du fork et l'image upstream de retour doivent être de **la même release** (ou plus récente
pour l'upstream). Une image plus ancienne que la base ne connaît pas toutes ses migrations. Avant chaque bascule,
vérifier la version en cours : `docker exec tandoor-web cat cookbook/version_info.py | head -1`.

## 3. Sauvegarde avant bascule

Sur le VPS, dans le dossier de la stack (le `run_directory` de Komodo, `…/stacks/tandoor`) :

```sh
mkdir -p ~/backups/tandoor
docker exec tandoor-db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > ~/backups/tandoor/before-fork.dump
tar czf ~/backups/tandoor/mediafiles-before-fork.tgz mediafiles
ls -la ~/backups/tandoor   # le dump ne doit pas faire 0 octet
```

La sauvegarde va hors du dossier de la stack, qui est un clone git géré par Komodo. Garder ces deux fichiers jusqu'à ce
que le fork ait tourné quelques jours sans souci, et en copier un exemplaire hors du VPS.

## 4. Essai sur une copie

On démarre une deuxième stack, isolée, sur la sauvegarde, avec l'image du fork. La production n'est pas touchée.

- L'essai n'est **pas** branché sur `internal-network` (`docs/fork/deploy/essai.override.yaml`). Sinon NPM pourrait
  envoyer le trafic de `tandoor-web` vers la copie, qui porterait le même alias réseau.
- On y accède par un tunnel SSH.

```sh
# sur le VPS
mkdir -p ~/tandoor-essai && cd ~/tandoor-essai
cp <clone de homelab-config>/stacks/tandoor/compose.yaml .     # le compose de l'étape 2
curl -fsSLO https://raw.githubusercontent.com/Alex-Delaveau/recipes/main/docs/fork/deploy/essai.override.yaml
docker exec tandoor-web env | grep -E '^(SECRET_KEY|DB_ENGINE|POSTGRES_|TZ|TIMEZONE|GUNICORN_MEDIA)=' > .env
cat >> .env <<'EOF'
TANDOOR_IMAGE=ghcr.io/alex-delaveau/recipes:2.6.15-fork.<n>
TANDOOR_NAME=tandoor-essai
TANDOOR_HTTP_PORT=8084
ALLOWED_HOSTS=*
EOF
C="docker compose -p tandoor-essai -f compose.yaml -f essai.override.yaml"
$C up -d tandoor-db
until docker exec tandoor-essai-db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; do sleep 2; done
docker exec -i tandoor-essai-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < ~/backups/tandoor/before-fork.dump
tar xzf ~/backups/tandoor/mediafiles-before-fork.tgz
$C up -d
docker logs -f tandoor-essai-web   # attendre "Applying kitchen.0001_aisles_and_duplicates... OK" puis "Starting gunicorn"
```

`POSTGRES_HOST=tandoor-db` reste juste : chaque stack a son propre réseau, et `tandoor-db` y désigne sa propre base.
Vérifié en M6 : après l'essai, la base de production n'a aucune table `kitchen_*`.

Depuis l'ordinateur : `ssh -L 8084:127.0.0.1:8084 <vps>`, puis ouvrir `http://localhost:8084`. Se connecter avec ses
comptes habituels et parcourir :
- une recette, avec le mode cuisine ;
- la liste de courses ;
- les aliments ;
- « Ajouter › Saisir une recette ».

Ensuite, supprimer l'essai : `$C down -v && cd ~ && rm -rf ~/tandoor-essai`.

## 5. Bascule

1. Refaire la sauvegarde de l'étape 3, juste avant, pour garder ce qui a changé depuis l'essai.
2. Si ce n'est pas déjà fait : pousser le compose de l'étape 2 dans `homelab-config`.
3. Komodo › stack `tandoor` › Environment : ajouter `TANDOOR_IMAGE=ghcr.io/alex-delaveau/recipes:2.6.15-fork.<n>`, puis
   Deploy. Au démarrage, `boot.sh` applique les migrations, dont celles du fork (`kitchen.0001…`), puis lance le
   serveur.
4. Vérifier :
   - `https://tandoor.aldelaveau.com` s'ouvre, et les recettes et la liste de courses sont là ;
   - `docker exec tandoor-web /opt/recipes/venv/bin/python manage.py showmigrations kitchen` affiche `[X]` partout ;
   - `docker ps --format '{{.Names}} {{.Image}}'` montre l'image du fork pour `tandoor-web`.

Mises à jour suivantes : changer l'étiquette dans `TANDOOR_IMAGE` et redéployer. Pour une nouvelle release Tandoor
(après la PR de synchronisation upstream), refaire d'abord les étapes 3 et 4.

## 6. Retour arrière vers l'image upstream

**Attention** : ne pas remettre directement l'image upstream. Les tables du fork référencent les aliments et l'espace
de Tandoor. Tant qu'elles existent, l'image upstream **ne peut plus supprimer** un aliment étendu par le fork (erreur
d'intégrité PostgreSQL, constatée en M6). Il faut d'abord retirer les tables du fork, **avec l'image du fork**.

### Retour arrière propre (garde les données saisies depuis la bascule)

1. Avec l'image du fork encore en place, retirer les tables `kitchen_*` :
   `docker exec tandoor-web /opt/recipes/venv/bin/python manage.py migrate kitchen zero --noinput`
2. Komodo › Environment : supprimer la ligne `TANDOOR_IMAGE` (retour au défaut, upstream 2.6.15), ou mettre
   `ghcr.io/tandoorrecipes/recipes:<même release>`. Puis Deploy.
3. Contrôle : `docker exec tandoor-web /opt/recipes/venv/bin/python manage.py migrate --check && echo OK`

On perd seulement ce que le fork stocke à part :
- le rayon générique choisi ;
- le marquage « famille » des aliments ;
- les paires « pas des doublons ».

Les recettes, aliments, rayons et courses restent dans les tables de Tandoor.

### Retour arrière par la sauvegarde (si le fork a abîmé quelque chose)

On revient à l'état exact d'avant la bascule. Tout ce qui a été saisi depuis est perdu.

1. Komodo › Environment : supprimer la ligne `TANDOOR_IMAGE`. Ne **pas** redéployer encore.
2. Komodo › Stop (ou `docker stop tandoor-web tandoor-db`).
3. Sur le VPS, dans le dossier de la stack :

   ```sh
   mv postgresql ~/backups/tandoor/postgresql-fork && mv mediafiles ~/backups/tandoor/mediafiles-fork   # gardés de côté
   docker compose up -d tandoor-db    # base vide, variables lues dans le .env écrit par Komodo
   until docker exec tandoor-db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; do sleep 2; done
   docker exec -i tandoor-db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' < ~/backups/tandoor/before-fork.dump
   tar xzf ~/backups/tandoor/mediafiles-before-fork.tgz
   ```

4. Komodo › Deploy. Puis `docker ps --format '{{.Names}} {{.Image}}'` doit montrer l'image upstream pour
   `tandoor-web`.

## 7. Ce que la CI garantit

- `Fork verify`, sur chaque PR vers `main` :
  - `verify.sh` complet, qui doit finir par `VERIFY: OK` ;
  - `scripts/fork/pg_upgrade_check.sh`, en trois temps :
    - une base PostgreSQL est créée par l'image upstream de la release de base, qui y écrit des données ;
    - les migrations du fork sont appliquées par-dessus ;
    - le retour arrière de la section 6 est joué : `migrate kitchen zero`, puis l'image upstream doit encore
      supprimer un aliment.
- Pour que la porte bloque vraiment les fusions : GitHub › Settings › Branches › règle sur `main` › « Require status
  checks to pass », cocher `verify.sh`. À faire une fois, après le premier passage du workflow.
- `Fork image` construit l'image à chaque fusion dans `main`, et sur les PR qui touchent le Dockerfile ou les
  dépendances. Elle n'est publiée sur GHCR qu'en dehors des PR.
