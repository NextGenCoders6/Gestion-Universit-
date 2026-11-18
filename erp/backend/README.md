# ERP UCCB — Backend

Django 5 + Django REST Framework + JWT. Toute l'API est sous `/api/<module>/` ;
le socle (comptes, droits, référentiel, personnes, audit) est sous `/api/core/`.

## Installation

```bash
cd erp/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # puis renseigner SECRET_KEY et la base
```

Base MySQL (par défaut) :

```sql
CREATE DATABASE uccb_erp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Pour un essai rapide sans MySQL, mettre `DB_ENGINE=sqlite` dans `.env`.

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_socle
.venv/bin/python manage.py seed_edt      # emploi du temps de démonstration
.venv/bin/python manage.py runserver
```

`seed_socle --reset` vide d'abord les données du socle (refusé si `DEBUG=False`).

## Tests

```bash
DB_ENGINE=sqlite .venv/bin/python manage.py test core edt
```

## Comptes de démonstration

Mot de passe commun : `Uccb!2026demo` — valeur de démonstration, à changer hors démo.

| Identifiant | Accès |
|---|---|
| `admin` | superutilisateur : tous les modules |
| `parametres` | Paramètres (responsable) |
| `scolarite_secretariat` | Scolarité — secrétariat |
| `scolarite_faculte` | Scolarité — faculté, rattaché à la FST |
| `edt_utilisateur`, `edt_responsable` | Emploi du temps |
| `rh_utilisateur`, `rh_responsable` | Ressources humaines |
| `finance_utilisateur`, `finance_responsable` | Finance |
| `logistique_utilisateur`, `logistique_responsable` | Logistique |
| `chef` | enseignant chef du département Informatique : gère l'EDT de la L2 INFO |
| `referent` | enseignant référent des L1 MIP et BCG (après `seed_edt`) |
| `enseignant` | enseignante (Mon espace : planning, enseignements, documents ; après `seed_edt`) |
| `employe` | gardien, sans aucun droit |

## Droits

Un module = des niveaux ; un niveau = un groupe Django `<module>_<niveau>`
(voir `core/droits.py`). Les rôles enseignant, chef de département, étudiant
et employé se déduisent des fiches personnes.

## Interface (React)

Développement : Django sur le port 8000 et Vite sur 5173 (relais de `/api`).

```bash
cd erp/frontend
npm install
npm run dev          # http://localhost:5173
```

Production : `npm run build` écrit l'interface dans `erp/backend/frontend_dist`,
que Django sert pour toute URL hors `/api/`, `/admin/`, `/media/`, `/static/`.

Tests de l'interface : `npm test` (Vitest) et `npx playwright test` (bout en bout ;
démarre ses propres serveurs sur les ports 8011 et 3011 avec une base jetable).
