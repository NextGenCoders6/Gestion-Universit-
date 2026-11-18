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
.venv/bin/python manage.py seed_demo       # tout l'ERP de démonstration, puis la liste des comptes
.venv/bin/python manage.py runserver
```

`seed_demo --reset` vide d'abord toutes les données (refusé si `DEBUG=False`, comme tous les seeds).
Chaque module garde son seed, à lancer dans cet ordre : `seed_socle`, `seed_edt`, `seed_scolarite`,
`seed_rh`, `seed_finance`, `seed_logistique`.

Contenu : une année 2026-2027 active (et 2027-2028 pour la promotion), 2 facultés, des classes L1 à L3
et une M1, ~10 enseignants permanents et vacataires, 10 employés dont 2 chauffeurs, 62 étudiants avec
notes et une délibération, des séances, des tarifs à 1 500 000 FCFA en 10 mensualités, des paiements,
la paie d'octobre, 3 bus, 3 trajets et des dépenses de transport.

## Docker

Pile complète (MySQL, Django avec gunicorn, nginx) : voir [`../docker/README.md`](../docker/README.md).

```bash
cd erp && cp .env.example .env && docker compose up -d --build   # → http://localhost:8080
```

## Tests

```bash
DB_ENGINE=sqlite .venv/bin/python manage.py test core edt scolarite rh finance logistique
cd ../frontend && npx vitest run && npx playwright test
```

## Comptes de démonstration

Mot de passe commun : `Uccb!2026demo` — valeur de démonstration, à changer hors démo.

| Identifiant | Accès |
|---|---|
| `admin` | superutilisateur : tous les modules |
| `parametres` | Paramètres (référentiel, utilisateurs, tarifs) |
| `scolarite_secretariat` | Scolarité — secrétariat (étudiants, inscriptions, attestations, relevés) |
| `scolarite_faculte` | Scolarité — faculté, rattaché à la FST (notes, délibérations, vacations) |
| `edt_utilisateur`, `edt_responsable` | Emploi du temps |
| `rh_utilisateur`, `rh_responsable` | Ressources humaines |
| `finance_utilisateur` | Finance — caisse (encaissements) |
| `finance_responsable` | Finance — paie, ajustements, annulations, transports |
| `logistique_utilisateur`, `logistique_responsable` | Logistique |
| `chef` | enseignant chef du département Informatique : gère l'EDT de la L2 INFO |
| `referent` | enseignant référent des L1 MIP et BCG |
| `enseignant` | enseignante (Mon espace : planning, enseignements, documents) |
| `etudiant` | étudiant de L1 MIP (Mon espace : notes, planning, enseignants, frais) |
| `employe` | gardien, sans aucun droit |

Activation d'un compte étudiant : matricule de Jonas Bakala, e-mail `jonas.bakala@etu.uccb.cg`,
date de naissance 12/05/2006.

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
