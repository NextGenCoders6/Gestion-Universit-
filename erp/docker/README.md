# ERP UCCB — Docker

La pile se compose de trois services, décrits dans `erp/docker-compose.yml` :

| Service | Rôle |
|---|---|
| `db` | MySQL 8.4 (données dans le volume `mysql`) |
| `web` | Django servi par gunicorn ; l'image embarque l'interface React construite (Vite) |
| `nginx` | frontal publié sur le port 8080 : sert `/static/` et `/media/`, relaie le reste à Django |

Au démarrage, `web` attend la base, applique les migrations et collecte les fichiers statiques.

## Démarrer

```bash
cd erp
cp .env.example .env        # puis remplacer SECRET_KEY, DB_PASSWORD et MYSQL_ROOT_PASSWORD
docker compose up -d --build
```

L'ERP répond sur <http://localhost:8080>.

`erp/.env` est ignoré par git : ne le commitez jamais. Pour générer une clé secrète :

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

## Premier compte administrateur

```bash
docker compose exec web python manage.py createsuperuser
```

## Données de démonstration

Les seeds sont refusés quand `DEBUG=False`, car leurs comptes partagent un mot de passe publié. Attendez que le service
`web` ait fini ses migrations (`docker compose logs -f web` affiche « Listening at »), puis, pour une démonstration
locale uniquement, lancez-les en forçant `DEBUG` pour cette seule commande :

```bash
docker compose run --rm -e DEBUG=True web python manage.py seed_demo
```

La commande affiche les comptes et leur mot de passe commun, également listés dans `erp/backend/README.md`.

## Opérations courantes

```bash
docker compose logs -f web                       # journaux de Django et de gunicorn
docker compose exec web python manage.py shell   # console Django
docker compose pull nginx db && docker compose up -d --build   # mise à jour
docker compose down                              # arrêt (les volumes sont conservés)
```

Sauvegarde et restauration de la base :

```bash
docker compose exec db sh -c 'mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' > sauvegarde.sql
docker compose exec -T db sh -c 'mysql -u root -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < sauvegarde.sql
```

Les fichiers téléversés (documents pédagogiques, photos) sont dans le volume `media`.

## Mise en production

- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` et `BASE_URL` : renseignez le nom de domaine réel.
  `BASE_URL` est l'adresse vers laquelle pointent les QR codes des documents officiels.
- Terminez le HTTPS devant nginx (reverse proxy, Traefik, Caddy, ou certificats montés dans nginx), puis passez
  `DERRIERE_HTTPS=True`.
- `MIGRATIONS_AU_DEMARRAGE=0` désactive les migrations automatiques ; lancez-les alors à la main :
  `docker compose run --rm web python manage.py migrate`.
- Avant la migration `edt/0004` sur une base existante, vérifiez qu'aucune affectation de l'emploi du temps n'est en
  double : elle ajoute une contrainte d'unicité.
