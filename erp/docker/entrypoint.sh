#!/bin/sh
# Démarrage du conteneur Django : attend la base, applique les migrations, collecte les fichiers statiques.
set -e

if [ "${DB_ENGINE:-mysql}" = "mysql" ]; then
  echo "Attente de la base ${DB_HOST:-db}:${DB_PORT:-3306}…"
  python - <<'PY'
import os, sys, time
import MySQLdb
for essai in range(60):
    try:
        MySQLdb.connect(host=os.environ.get('DB_HOST', 'db'), port=int(os.environ.get('DB_PORT', 3306)),
                        user=os.environ.get('DB_USER', 'root'), password=os.environ.get('DB_PASSWORD', ''),
                        database=os.environ.get('DB_NAME', 'uccb_erp')).close()
        sys.exit(0)
    except MySQLdb.OperationalError:
        time.sleep(2)
print('La base de données ne répond pas.', file=sys.stderr)
sys.exit(1)
PY
fi

if [ "${MIGRATIONS_AU_DEMARRAGE:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi
python manage.py collectstatic --noinput -v0

exec "$@"
