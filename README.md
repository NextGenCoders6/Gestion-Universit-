# ERP UCCB

ERP de l'université (scolarité, emploi du temps, RH, finance, logistique), sur un socle commun :
une seule connexion, une seule base, un référentiel partagé.

| Dossier | Contenu |
|---|---|
| `erp/backend/` | API Django REST (voir `erp/backend/README.md`) |
| `erp/frontend/` | interface React (Vite) |
| `erp/docker/` | pile Docker : MySQL, Django/gunicorn, nginx (voir `erp/docker/README.md`) |
| `docs/` | conception et plans de réalisation |

Démarrage rapide avec Docker :

```bash
cd erp
cp .env.example .env        # puis renseigner SECRET_KEY, DB_PASSWORD et MYSQL_ROOT_PASSWORD
docker compose up -d --build
```
