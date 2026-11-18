# ERP UCCB — Phase 2 : Emploi du temps — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter l'application EDT (`uccb_backend/EDT_app` + écrans `uccb_frontend/src/features`) dans l'ERP comme module `edt`, branché sur le référentiel et les fiches personnes du socle, avec le planning personnel de l'enseignant dans « Mon espace ».

**Architecture:** Nouvelle app Django `erp/backend/edt` (affectations, séances, référents, documents) qui ne garde aucun référentiel propre : elle utilise `core.Classe`, `core.ElementConstitutif`, `core.Periode`, `core.Enseignant`. Les règles de `EDT_app/validation_seance.py`, `perimetre.py` et des modèles sont portées en gardant leur comportement. Côté frontend, `erp/frontend/src/modules/edt` reprend les écrans EDT (planning, séances, affectations, progression, documents) et `src/modules/moi` l'espace enseignant.

**Tech Stack:** celle de la phase 1 ; ajout de `@fullcalendar/react`, `daygrid`, `timegrid`, `interaction` (déjà utilisés par l'EDT).

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md` (§7.2, §7.7, §8) ; socle : `docs/superpowers/plans/2026-11-18-erp-phase1-socle.md`.

## Global Constraints

- Phase 1 inchangée sauf ajouts listés ici ; tous ses tests restent verts.
- Sources à porter (lecture seule) : `/home/it-junior/Gestion-Universit-/uccb_backend/EDT_app/` et `/home/it-junior/Gestion-Universit-/uccb_frontend/src/` (version EDT la plus récente).
- Table de correspondance EDT → ERP, à appliquer partout (code, tests, écrans) :

| EDT | ERP |
|---|---|
| `Module` | `core.ElementConstitutif` (EC) **dans une classe donnée** |
| `Module.classe` / `Module.semestre` | `Seance.classe` / `ec.ue.semestre` |
| `Semestre` (dates) | `core.Periode` (numéro = `ec.ue.periode_numero`) |
| `Matiere` | supprimée (l'EC porte son département) |
| `AffectationModule` | `edt.AffectationEC` (+ champ `classe`) |
| `Profil` / `Enseignant` EDT | `core.Personne` / `core.Enseignant` |
| `Seance.annee` | supprimé : `seance.classe.annee` |
| groupe `responsable` | `edt_responsable` |
| rôles `chef_departement`, `referent_l1` | rôles contextuels `chef_departement`, `referent_classe` |

- Quota d'un EC dans une classe : `credits × 12` h (`Seance.HEURES_PAR_CREDIT`). Plafond par type : `heures_cm/td/tp` de l'EC **si > 0** (0 = non ventilé). Les heures se comptent par couple (EC, classe).
- Statuts et types de séance inchangés : `brouillon`, `Confirmée`, `Annulée`, `Reportée` ; `CM`, `TD`, `TP`. Bornes horaires inchangées (début ≥ 09:00, pause 11:00–11:15, fin ≤ 16:20, 6 h max par jour et par classe).
- API sous `/api/edt/…` ; erreurs en 400 par champ (gestionnaire de la phase 1).

## Droits du module

- `edt_responsable` : tout l'EDT, toutes classes.
- `edt_utilisateur` : lecture de tout le planning et des affectations (ex. secrétariat), aucune écriture.
- Rôle contextuel `chef_departement` : gestion (séances, affectations, référents) des classes à filière de ses départements dirigés.
- Rôle contextuel `referent_classe` (nouveau, déclaré par l'app `edt` dans `core.droits.ROLES_CONTEXTUELS`) : gestion des séances de ses classes assignées (typiquement les L1).
- Un chef ou un référent voit la tuile Emploi du temps même sans groupe : `edt` ajoute un niveau contextuel `perimetre` via un nouveau point d'extension `core.droits.NIVEAUX_CONTEXTUELS`.
- Enseignant : pas d'accès au module ; son planning et ses EC sont dans « Mon espace ».

## Review Focus

1. Séance déplacée par glisser-déposer sur un créneau interdit (dimanche, pause, après 16:20, hors période) → message français précis dans un toast, la séance revient à sa place.
2. Chef de département qui ouvre l'URL d'une séance d'un autre département → 404 (pas de fuite), et aucune action d'écriture possible.
3. Classe L1 (portail) : visible et gérable par le référent, invisible pour un chef qui n'en est pas référent.
4. Année archivée : aucune création/modification de séance, et l'archivage est refusé s'il reste des séances confirmées futures.
5. EC dont la période n'a pas de dates définies pour l'année → 400 « La période … n'est pas définie », jamais 500.

---

### Task 1: App `edt`, affectations et quotas

**Files:**
- Create: `erp/backend/edt/{__init__,apps,admin}.py`, `edt/models.py`, `edt/quotas.py`, `edt/tests/{__init__,fabriques,test_affectations,test_quotas}.py`
- Modify: `erp/backend/config/settings.py` (INSTALLED_APPS), `erp/backend/core/models/referentiel.py` (règle de ventilation de l'EC), `core/management/commands/seed_socle.py` (heures compatibles)

**Interfaces:**
- Produces:
  - `edt.models.AffectationEC(ec FK core.ElementConstitutif PROTECT, classe FK core.Classe PROTECT, enseignant FK core.Enseignant PROTECT related_name='affectations', type_seance: None|'CM'|'TD'|'TP', heures_prevues: float ≥ 0, hors_departement: bool, created_at)` — règles de `EDT_app/models.py:926-976` (non-ambiguïté générique/typée par (ec, classe, enseignant), département de l'enseignant = département de l'EC sauf `hors_departement`), avertissement de dépassement non bloquant.
  - `edt.quotas.heures_max(ec) -> int` (= `credits × 12`), `plafond_type(ec, type) -> int | None`, `heures_consommees(ec, classe, *, type=None, enseignant=None, exclure=None) -> float`, `heures_effectuees(...) -> float` (séances passées seulement), `heures_restantes(...)`. Comptent les séances `Confirmée`/`Reportée`, créneau effectif (report), mutualisées dédupliquées (`Seance.dedupliquer_mutualisees`).
  - Règle ajoutée à `ElementConstitutif.clean` : somme des heures ventilées (> 0) ≤ `credits × 12` (règle de `EDT_app/models.py:829-846`).
- [ ] Tests (`test_affectations.py`, `test_quotas.py`) portés de `EDT_app/tests_affectation.py` (partie modèle) et `tests_module_quota.py`, avec la table de correspondance ; plus `test_heures_comptees_par_classe` (même EC dans deux classes : quotas indépendants) et `test_ec_ventilation_depasse_refusee`.
- [ ] Lancer → FAIL ; implémenter ; lancer `DB_ENGINE=sqlite .venv/bin/python manage.py test edt core` → PASS. `seed_socle` : heures des EC ramenées sous `credits × 12`.
- [ ] Commit `feat(edt): affectations et quotas par EC et par classe`.

### Task 2: Séances et règles de validation

**Files:**
- Create: `edt/validation.py` (port de `EDT_app/validation_seance.py`), `edt/tests/{test_validation,test_seance_cycle,test_volume_journalier}.py`
- Modify: `edt/models.py` (`Seance`), `core/models/referentiel.py` (hook d'archivage)

**Interfaces:**
- Produces:
  - `edt.models.Seance(libelle, date_seance, heure_debut, heure_fin, type_seance, statut, date_report, heure_debut_report, heure_fin_report, ec FK, enseignant FK, classe FK, seance_liee FK self null)` ; méthodes portées `calculer_duree_effective`, `creneau_effectif`, `dedupliquer_mutualisees`, constantes horaires ; `clean()` appelle les validateurs dans l'ordre de `EDT_app/models.py:1176-1290`.
  - `edt.validation` : mêmes fonctions que la source, sauf :
    - `valider_coherence_annee_classe` supprimée (année = `classe.annee`) ;
    - `valider_coherence_module_semestre` → `valider_ec_dans_classe(ec, classe)` : l'UE de l'EC est sur le portail ou la filière de la classe **et** `ec.ue.semestre in classe.semestres` ;
    - `valider_bornes_semestre` → `valider_bornes_periode(date, classe, ec)` : période `numero = ec.ue.periode_numero` de `classe.annee` ; absente → `ValidationError({'date_seance': "La période Semestre N de AAAA-AAAA n'est pas définie."})` ;
    - `valider_volume_module` / `valider_affectation` → quotas de `edt.quotas` par (EC, classe).
  - Hook d'archivage : `core.models.referentiel.VERIFICATIONS_ARCHIVAGE: list[Callable[[AnneeAcademique], None]]` appelé par `AnneeAcademique.clean` quand `statut='archivee'` ; `edt` y ajoute le refus « séances confirmées dans le futur » (`EDT_app/models.py:177-189`).
- [ ] Tests portés de `tests_seance_lifecycle.py`, `tests_volume_journalier.py` et des tests de validation de `tests_complets.py` / `tests_solidite.py` qui portent sur les séances ; plus `test_periode_non_definie_400` (Review Focus 5) et `test_archivage_refuse_si_seances_futures` (Review Focus 4).
- [ ] FAIL → implémenter → PASS (`manage.py test edt core`).
- [ ] Commit `feat(edt): séances et règles de validation portées de l'EDT`.

### Task 3: Périmètre, référents et droits contextuels

**Files:**
- Create: `edt/perimetre.py`, `edt/permissions.py`, `edt/droits.py`, `edt/tests/{test_perimetre,test_roles}.py`
- Modify: `edt/models.py` (`ReferentClasse`), `edt/apps.py` (`ready()` enregistre rôles et niveaux), `core/droits.py` (`NIVEAUX_CONTEXTUELS`)

**Interfaces:**
- Produces:
  - `edt.models.ReferentClasse(enseignant OneToOne related_name='referent_classes', classes M2M core.Classe)`.
  - `core.droits.NIVEAUX_CONTEXTUELS: list[Callable[[User], dict[str, list[str]]]]` — `niveaux_utilisateur` y ajoute les niveaux renvoyés ; `edt` renvoie `{'edt': ['perimetre']}` pour un chef ou un référent. `MODULES['edt']['niveaux']` reste `['utilisateur', 'responsable']` (le niveau contextuel n'est pas un groupe).
  - Rôle contextuel `referent_classe` (enseignant ayant une `ReferentClasse` avec au moins une classe).
  - `edt.perimetre.classes_autorisees(user) -> QuerySet[Classe] | None` (None = illimité : superuser, `edt_responsable`, `edt_utilisateur` en lecture), `classes_gerables(user)` (écriture : superuser, `edt_responsable`, sinon chef ∪ référent), `ecs_autorises(user)`, `restreindre_enseignants(user, qs)` — logique de `EDT_app/perimetre.py`, chef = classes dont `filiere.departement` est dirigé, référent = ses classes.
  - `edt.permissions.LectureEdt`, `GestionEdt` (lecture : niveau quelconque du module ; écriture : `edt_responsable` ou `perimetre`, objet dans `classes_gerables`).
- [ ] Tests portés de `tests_perimetre.py` et de la partie EDT de `tests_securite_roles.py` ; plus `test_tuile_edt_pour_chef_sans_groupe` (`modules_accessibles` contient `edt` niveau `perimetre`), `test_l1_reservee_au_referent` (Review Focus 3).
- [ ] FAIL → implémenter → PASS (`manage.py test edt core`).
- [ ] Commit `feat(edt): périmètre, référents de classe et droits contextuels`.

### Task 4: API de l'emploi du temps

**Files:**
- Create: `edt/serializers.py`, `edt/views.py`, `edt/urls.py`, `edt/tests/{test_api_seances,test_api_affectations,test_api_publication}.py`
- Modify: `config/urls.py` (`path('api/edt/', include('edt.urls'))`)

**Interfaces:**
- Produces (routeur sous `/api/edt/`) :
  - `seances/` CRUD — filtres `classe`, `enseignant`, `ec`, `statut`, `annee`, `date_debut`, `date_fin` (entiers validés en 400) ; actions portées de `EDT_app/views.py:1299-1527` : `POST {id}/publier/`, `POST {id}/depublier/`, `POST publier_masse/ {ids:[...]}`, `PATCH {id}/reporter/ {date_report, heure_debut_report, heure_fin_report}`, `GET conflits/?enseignant=&classe=&date=&heure_debut=&heure_fin=&exclure=`, `GET {id}/seances_liees/`. Champs lus : ceux du modèle + `ec_code`, `ec_libelle`, `classe_libelle`, `enseignant_nom`, `creneau_effectif`.
  - `affectations/` CRUD — filtres `ec`, `classe`, `enseignant`, `annee` ; champs calculés `heures_consommees`, `heures_effectuees`, `heures_restantes`, `warnings`.
  - `enseignements/` lecture seule : une ligne par (EC, classe) du périmètre pour l'année demandée (`?annee=` défaut année en cours, `?classe=`, `?departement=`) : `{ec, ec_code, ec_libelle, classe, classe_libelle, semestre, heures_max, plafonds{CM,TD,TP}, heures_consommees, heures_effectuees, affectations:[...]}`.
  - `referents/` CRUD (`edt_responsable` ou chef pour les classes de ses départements).
  - `moi/planning/` et `moi/enseignements/` (enseignant connecté, même sans module) : ses séances publiées (`Confirmée`, `Reportée`) / ses affectations avec quotas.
  - Pagination `PaginationStandard` (page_size ≤ 200) ; ressources hors périmètre → 404.
- [ ] Tests portés des tests API de `tests_complets.py`, `tests_seance_publication.py`, `tests_securite.py` (parties séances/affectations/modules), plus `test_seance_autre_departement_404` (Review Focus 2) et `test_edt_utilisateur_lecture_seule`.
- [ ] FAIL → implémenter → PASS (`manage.py test edt core`).
- [ ] Commit `feat(edt): API séances, affectations et enseignements`.

### Task 5: Documents pédagogiques

**Files:**
- Create: `edt/fichiers.py` (port de `EDT_app/fichiers.py`), `edt/tests/test_documents.py`
- Modify: `edt/models.py` (`DocumentPedagogique`), `edt/serializers.py`, `edt/views.py`, `edt/urls.py`

**Interfaces:**
- Produces : `DocumentPedagogique(titre, fichier, type_doc 'cours'|'td'|'tp'|'autre', ec FK, classe FK, enseignant FK, created_at)` ; `documents/` CRUD (dépôt par l'enseignant affecté à l'EC dans la classe, ou gestionnaire du périmètre ; lecture : périmètre) ; `GET documents/{id}/telecharger/` (en-têtes `Content-Disposition` de la source) ; `moi/documents/` pour l'enseignant. Validation extension / taille / contenu réel reprise de `fichiers.py` (taille max lue dans `settings.TAILLE_MAX_DOCUMENT_MO`, défaut 20).
- [ ] Tests portés des tests documents de `tests_securite.py` / `tests_solidite.py` (fichier déguisé, trop gros, extension refusée) ; FAIL → implémenter → PASS.
- [ ] Commit `feat(edt): documents pédagogiques`.

### Task 6: Données de démonstration EDT

**Files:**
- Create: `edt/management/commands/seed_edt.py`, `edt/tests/test_seed.py`
- Modify: `erp/backend/README.md`

**Interfaces:**
- Produces : `seed_edt` (refusé si `DEBUG=False`, idempotent, après `seed_socle`) : UE/EC de L1 MIP S1–S2 et L2 INFO S3–S4, 4 enseignants supplémentaires (dont 1 référent L1 MIP, compte `referent`), affectations, ~40 séances sur la période 1 (brouillons et confirmées, une mutualisée), comptes `enseignant` (Ngoma) et `referent`. README : nouveaux comptes.
- [ ] Test `test_seed_edt_idempotent` + `test_seances_valides` (toutes les séances créées passent `full_clean`) ; FAIL → implémenter → PASS.
- [ ] Commit `feat(edt): jeu de données de démonstration`.

### Task 7: Frontend — module Emploi du temps

**Files:**
- Create: `erp/frontend/src/modules/edt/{routes.jsx,api.js}`, `modules/edt/pages/{Planning,Seances,Enseignements,Referents}.jsx`, `modules/edt/components/*` (portés de `uccb_frontend/src/features/{planning,seances,affectations,progression}` et des `hooks/`, `lib/{creneau,planningFilters,progression,semestres}.js` qu'ils utilisent)
- Modify: `src/app/modules.js` (menu `edt`), `src/app/routesModules.jsx`, `package.json` (FullCalendar)
- Test: `modules/edt/pages/{Planning,Seances}.test.jsx`, `modules/edt/lib/*.test.js` pour les utilitaires portés

**Interfaces:**
- Consumes : Task 4 (endpoints), registre/ModuleShell de la phase 1, `RessourceCrud` pour Référents.
- Produces : menu EDT = Planning (grille FullCalendar semaine/jour + vue tableau, filtres classe/enseignant/EC, détails de séance), Séances (liste groupée par classe/jour, formulaire, report, publication en masse, conflits en direct), Enseignements (une ligne par EC × classe : quotas, barre d'avancement, panneau d'affectations), Référents (`niveaux: ['responsable', 'perimetre']`). Les actions d'écriture sont masquées pour `edt_utilisateur`. Chaque appel EDT passe par `modules/edt/api.js` (`/edt/...`) ; les écrans portés gardent leurs comportements (toasts, confirmations, retour visuel du glisser-déposer refusé).
- Écrans EDT **non** repris (couverts ailleurs) : Organisation, Classes, Contenu pédagogique, Modules/Matières (→ Paramètres), Enseignants/Étudiants/Statut (→ Paramètres puis RH/Scolarité), Profil.
- [ ] Tests : `Planning.test.jsx` — un déplacement refusé par l'API (400 `date_seance`) affiche le message et appelle `revert()` (Review Focus 1) ; `Seances.test.jsx` — `edt_utilisateur` ne voit ni « Nouvelle séance » ni « Publier » ; tests des utilitaires portés (`creneau`, `planningFilters`, `progression`). FAIL → porter → PASS ; `npm run lint`, `npm run build`.
- [ ] Commit `feat(edt): écrans du module Emploi du temps`.

### Task 8: Frontend — Mon espace enseignant

**Files:**
- Create: `erp/frontend/src/modules/moi/{routes.jsx,api.js}`, `modules/moi/pages/{MonPlanning,MesEnseignements,MesDocuments}.jsx`, `modules/moi/MoiShell.jsx`
- Modify: `src/app/router.jsx` (`/moi/*`), suppression de `app/pages/MonEspace.jsx`
- Test: `modules/moi/MoiShell.test.jsx`

**Interfaces:**
- Produces : « Mon espace » avec le même `ModuleShell` (module virtuel `moi`, menu filtré par rôle : `enseignant` → Planning, Mes enseignements, Documents) ; planning en lecture seule (grille réutilisée de la Task 7), avancement par affectation, dépôt/liste de documents. Un étudiant voit pour l'instant « Votre planning arrivera avec la Scolarité » (ses classes viennent des inscriptions, phase 3).
- [ ] Test : un enseignant voit les 3 entrées et sa grille ; un étudiant voit le message d'attente. FAIL → implémenter → PASS.
- [ ] Commit `feat(moi): espace personnel de l'enseignant`.

### Task 9: Bout en bout

**Files:**
- Create: `erp/frontend/e2e/02-edt.spec.js`
- Modify: `playwright.config.js` (lance aussi `seed_edt`)

- [ ] Scénarios : le référent crée une séance L1 MIP puis la publie ; le chef Informatique n'a pas cette classe ; l'enseignant la voit dans Mon espace ; un déplacement sur un dimanche est refusé avec message. `npx playwright test` → tous verts (phase 1 comprise).
- [ ] Commit `test(edt): parcours de bout en bout`.

## Hors de cette phase

- Planning de l'étudiant et trombinoscope : phase 3 (dépendent des inscriptions).
- Lien heures effectuées → vacations / paie : phases 4 et 5 (les fonctions `edt.quotas` sont l'interface qu'elles consommeront).
- Profil avec photo : plus tard (champ `photo` déjà sur `Personne`).
