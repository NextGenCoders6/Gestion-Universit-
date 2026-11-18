# ERP UCCB — Phase 1 : Socle — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer le socle de l'ERP : projet `erp/`, app `core` (référentiel, personnes, droits, audit), connexion JWT unique, API Paramètres, et une SPA React avec login, lanceur de modules, layout de module et écrans Paramètres.

**Architecture:** Nouveau projet Django `erp/backend` (projet `config`, app `core`) exposant `/api/core/…` en DRF. Nouvelle SPA `erp/frontend` construite à partir de `Projet-Gestion-Acad-mique-main/edt-frontend` ; un registre de modules côté frontend, alimenté par `/api/core/moi/`, pilote le lanceur, les menus et les gardes de route. Les phases 2 à 6 (EDT, Scolarité, RH, Finance, Logistique) auront chacune leur plan et s'enregistreront dans ce registre.

**Tech Stack:** Python 3.12, Django 5.x, DRF 3.15+, djangorestframework-simplejwt 5.x (blacklist), django-cors-headers, python-decouple, mysqlclient, Pillow, factory_boy ; React 18, Vite, Tailwind 3, shadcn/Radix, react-router-dom 6, TanStack Query 5, zustand 4, react-hook-form + zod, lucide-react, axios ; tests : `manage.py test` (Django TestCase), Vitest + Testing Library, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md`

## Global Constraints

- Les dossiers `uccb_backend/`, `uccb_frontend/`, `Projet-Gestion-Acad-mique-main/` ne sont **jamais modifiés** ; on y lit et on copie.
- Tout le code nouveau vit sous `erp/backend/` et `erp/frontend/`.
- Configuration par `.env` (python-decouple) ; `.env` jamais versionné, `.env.example` versionné.
- Base : MySQL (`DB_ENGINE=mysql`) ; tests et dev rapide : SQLite (`DB_ENGINE=sqlite`).
- Textes d'interface, messages d'erreur et noms métier en français.
- Groupes de droits : `<module>_<niveau>` ; Scolarité = `scolarite_secretariat`, `scolarite_faculte` ; autres modules = `<module>_utilisateur`, `<module>_responsable` ; Paramètres = `parametres_responsable`. Le superuser a tout.
- Matricules : étudiant `UCCB{AA}{NOM3}{PR2}{n:05d}`, enseignant `UCCB-ENS-{n:05d}`, employé `UCCB-PERS-{n:05d}`.
- Design : thème shadcn de `edt-frontend/src/index.css`, primaire `147.6 83.4% 26.1%`, logo `logo-uccb.svg`.
- JWT : accès 2 h, refresh 7 j, rotation + blacklist ; débits `login` 30/min, `login_ip` 60/min (repris de `uccb_backend/uccb_project/settings.py:136-170`).

## Review Focus

1. Compte suspendu alors que son jeton d'accès est encore valide → tout appel API renvoie 403 avec `code: "profil_suspendu"`, et le frontend renvoie au login avec le motif (Task 4, Task 8).
2. Utilisateur sans aucun droit de module (ex. un employé sans rôle) → le lanceur affiche « Aucun module ne vous est attribué », pas une page blanche (Task 9).
3. Lien direct vers `/parametres/…` sans le droit → page 403 dans le layout, sans boucle de redirection ; non connecté → `/login` puis retour à la page demandée (Task 9).
4. Saisie incohérente du référentiel (classe L1 avec filière, classe avec portail **et** filière, UE S3 sur un portail) → 400 avec message français par champ, jamais 500 (Task 1, Task 5).
5. Suppression d'un élément encore utilisé (faculté avec départements, département avec enseignants) → 400 « … est encore utilisé par … », jamais 500 (Task 5).

---

### Task 1: Projet Django et référentiel académique

**Files:**
- Create: `erp/backend/manage.py`, `erp/backend/config/{__init__,settings,urls,wsgi}.py`, `erp/backend/requirements.txt`, `erp/backend/.env.example`, `erp/backend/.gitignore`
- Create: `erp/backend/core/{__init__,apps,admin}.py`, `erp/backend/core/models/__init__.py`, `erp/backend/core/models/referentiel.py`
- Test: `erp/backend/core/tests/__init__.py`, `erp/backend/core/tests/test_referentiel.py`

**Interfaces:**
- Produces (models, app `core`):
  - `AnneeAcademique(libelle: str unique 'AAAA-AAAA', date_debut, date_fin, statut: 'active'|'archivee', en_cours: bool)` ; `AnneeAcademique.courante() -> AnneeAcademique | None`.
  - `Periode(annee FK related_name='periodes', numero: 1|2, date_debut, date_fin)` ; unique `(annee, numero)`.
  - `Faculte(nom unique, code unique, logo, genre_doyen 'M'|'F', nom_doyen, genre_vice_doyen, nom_vice_doyen)` ; propriétés `titre_doyen`, `titre_vice_doyen`, `signataire_pv`.
  - `Departement(libelle, faculte FK related_name='departements')` — le champ `chef` est ajouté en Task 2.
  - `Portail(faculte FK related_name='portails', nom, code)` ; unique `(faculte, code)`.
  - `Filiere(departement FK related_name='filieres', portail FK related_name='filieres', nom, code)` ; unique `(departement, code)` — le champ `responsable` est ajouté en Task 2.
  - `Parcours(type_parcours 'Licence'|'Master'|'Doctorat', niveau int)` ; propriétés `code -> 'L1'…'M2'|'D1'…`, `semestres -> tuple[str, str]`.
  - `Classe(annee FK related_name='classes', parcours FK, portail FK null, filiere FK null, libelle auto)`.
  - `UniteEnseignement(code unique, libelle, semestre 'S1'…'S10', portail FK null, filiere FK null)` ; propriété `periode_numero -> 1|2`.
  - `ElementConstitutif(ue FK related_name='ecs', code unique, libelle, credits, heures_cm, heures_td, heures_tp, departement FK PROTECT, description)` ; propriété `heures_total`.
  - `ParametresEtablissement` (singleton) `(nom_secretaire, genre_secretaire, ville_signature='Liambou')` ; `ParametresEtablissement.get() -> ParametresEtablissement` ; propriété `titre_secretaire`.
  - Constante `core.models.referentiel.SEMESTRES = [('S1','Semestre 1'), …, ('S10','Semestre 10')]`.

- [ ] **Step 1: Créer le squelette** — `erp/backend` avec `django-admin startproject config .`, app `core`, `requirements.txt` (versions de la Tech Stack + `factory_boy`), `.env.example` (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_ENGINE`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `CORS_ALLOWED_ORIGINS`), `.gitignore` (`.venv/`, `.env`, `media/`, `staticfiles/`, `*.sqlite3`, `__pycache__/`). `settings.py` lit tout via `decouple.config` ; `DATABASES` = SQLite (`BASE_DIR/'db.sqlite3'`) si `DB_ENGINE=sqlite`, sinon MySQL `utf8mb4`. `LANGUAGE_CODE='fr-fr'`, `TIME_ZONE='Africa/Brazzaville'`, `USE_TZ=True`. Venv : `cd erp/backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`.

- [ ] **Step 2: Écrire les tests qui échouent** dans `test_referentiel.py` :

```python
class AnneeAcademiqueTests(TestCase):
    def test_libelle_format_invalide(self):
        with self.assertRaisesMessage(ValidationError, "AAAA-AAAA"):
            AnneeAcademique.objects.create(libelle="2026/2027", date_debut=date(2026,10,1), date_fin=date(2027,7,31))
    def test_une_seule_annee_en_cours(self):
        a = annee("2025-2026", en_cours=True); b = annee("2026-2027", en_cours=True)
        a.refresh_from_db(); self.assertFalse(a.en_cours); self.assertEqual(AnneeAcademique.courante(), b)

class PeriodeTests(TestCase):
    def test_periode_hors_annee_refusee(self):  # date_debut < annee.date_debut → ValidationError sur 'date_debut'

class ParcoursTests(TestCase):
    def test_code_et_semestres(self):
        self.assertEqual(Parcours(type_parcours="Licence", niveau=2).code, "L2")
        self.assertEqual(Parcours(type_parcours="Licence", niveau=2).semestres, ("S3", "S4"))
        self.assertEqual(Parcours(type_parcours="Master", niveau=1).semestres, ("S7", "S8"))
    def test_niveau_max(self):  # Licence 4 → ValidationError

class ClasseTests(TestCase):
    def test_l1_sur_portail_libelle(self):   # libelle == "L1 MIP — 2026-2027"
    def test_l1_avec_filiere_refusee(self):  # ValidationError
    def test_l2_sans_filiere_refusee(self):  # ValidationError
    def test_portail_et_filiere_refuses(self):
    def test_doctorat_refuse(self):
    def test_unicite(self):  # même annee+parcours+portail deux fois → ValidationError

class UETests(TestCase):
    def test_s1_sur_portail_ok_s3_sur_portail_refuse(self):
    def test_periode_numero(self):  # S3 → 1, S4 → 2

class ECTests(TestCase):
    def test_credits_bornes(self):  # 0 et 7 refusés, 1 et 6 acceptés

class FiliereTests(TestCase):
    def test_portail_et_departement_meme_faculte(self):  # facultés différentes → ValidationError
```

  Les helpers `annee()`, `faculte()`, etc. vont dans `core/tests/fabriques.py` (factory_boy), réutilisés par toutes les tâches.

- [ ] **Step 3: Lancer, constater l'échec** — `cd erp/backend && DB_ENGINE=sqlite .venv/bin/python manage.py test core.tests.test_referentiel` → erreurs d'import.

- [ ] **Step 4: Implémenter `core/models/referentiel.py`.** Chaque `save()` appelle `full_clean()` (pattern EDT). Règles reprises :
  - `AnneeAcademique.clean` = `uccb_backend/EDT_app/models.py:153-190` sans le bloc « séances futures » (il reviendra en phase 2 via un hook) ; `save()` avec `en_cours=True` met les autres à `False` dans la même transaction.
  - `Periode.clean` = `EDT_app/models.py:211-225`.
  - `Faculte.titre_*` / `signataire_pv` = `uccb_backend/gestion_eleves/models.py:48-75`.
  - `Parcours` : maxima `{'Licence': 3, 'Master': 2, 'Doctorat': 3}` ; `semestres` = Licence n → (S2n-1, S2n), Master n → (S6+2n-1, S6+2n), Doctorat → `()`.
  - `Classe.clean` : exactement un de `portail`/`filiere` ; `parcours.code == 'L1'` ⇔ portail ; Doctorat refusé ; unicité via deux `UniqueConstraint` conditionnelles (`portail__isnull=False` / `filiere__isnull=False`) + contrôle explicite dans `clean` pour un message français. `libelle = f"{parcours.code} {(portail or filiere).code} — {annee.libelle}"`.
  - `UniteEnseignement.clean` : exactement un de `portail`/`filiere` ; S1/S2 ⇔ portail.
  - `ElementConstitutif.credits` : validateurs 1…6 ; heures ≥ 0, défaut 0.
  - `Filiere.clean` : `portail.faculte_id == departement.faculte_id`.
  - `ParametresEtablissement.get()` = `get_or_create(pk=1)`.
  - Pas encore de dossier `migrations/` : le lanceur de tests crée les tables d'une app sans migrations. La migration `0001_initial` est générée en Task 2.

- [ ] **Step 5: Lancer les tests** — même commande → PASS. `manage.py check` → `System check identified no issues`.

- [ ] **Step 6: Commit** — `git add erp/backend && git commit -m "feat(core): projet ERP et référentiel académique"`

---

### Task 2: Personnes et rôles

**Files:**
- Create: `erp/backend/core/models/personnes.py`, `erp/backend/core/validateurs.py`
- Modify: `erp/backend/core/models/__init__.py` (exports), `erp/backend/core/admin.py`
- Test: `erp/backend/core/tests/test_personnes.py`

**Interfaces:**
- Consumes: Task 1 (`Faculte`, `Departement`, `AnneeAcademique`).
- Produces:
  - `core.validateurs.nom_validator`, `valider_date_naissance(valeur: date) -> None` (copiés de `uccb_backend/gestion_eleves/models.py` ; message d'âge neutre « la personne »).
  - `Personne(nom, prenom, genre 'M'|'F', date_naissance null, lieu_naissance, nationalite='Congolaise', email unique null, telephone, adresse, photo, statut 'actif'|'suspendu', motif_suspension, user OneToOne auth.User null SET_NULL related_name='personne')` ; propriétés `nom_complet -> "NOM Prénom"`, `est_suspendue -> bool`.
  - `Etudiant(personne OneToOne pk related_name='etudiant', matricule unique auto, statut 'actif'|'diplome'|'abandonne', annee_entree FK AnneeAcademique)`.
  - `Enseignant(personne OneToOne pk related_name='enseignant', matricule auto, grade ('', 'Ingénieur','Docteur','Professeur'), departement FK PROTECT related_name='enseignants')`.
  - `Employe(personne OneToOne pk related_name='employe', matricule auto, fonction ('menage','gardien','cuisinier','chauffeur','technicien','autre'), fonction_autre, lieu_travail, faculte_rattachement FK null)`.
  - `core.models.personnes.generer_matricule_etudiant(personne: Personne, annee: AnneeAcademique) -> str`.
  - Ajouts au référentiel de Task 1 : `Departement.chef` (FK `Enseignant` null SET_NULL related_name='departements_diriges') et `Filiere.responsable` (FK `Enseignant` null SET_NULL related_name='filieres_responsable').

- [ ] **Step 1: Tests qui échouent**

```python
def test_matricule_etudiant(self):
    p = personne(nom="Mabiala", prenom="Grâce"); e = Etudiant.objects.create(personne=p, annee_entree=annee("2026-2027"))
    self.assertRegex(e.matricule, r"^UCCB26MABGR\d{5}$")
def test_matricule_nom_court(self):          # nom "Ba" prénom "N" → "UCCB26BAXNX…"
def test_matricule_enseignant_et_employe(self):  # "UCCB-ENS-00001", "UCCB-PERS-00001", séquences indépendantes
def test_cumul_roles(self):                  # une Personne peut être Enseignant et Employe
def test_suspension_exige_motif(self):       # statut='suspendu', motif vide → ValidationError
def test_nom_invalide(self):                 # "J3an" → ValidationError
def test_fonction_autre_exige_libelle(self):
def test_email_unique_mais_optionnel(self):  # deux personnes sans e-mail OK ; deux identiques refusées
```

- [ ] **Step 2: Lancer** — `DB_ENGINE=sqlite .venv/bin/python manage.py test core.tests.test_personnes` → FAIL.
- [ ] **Step 3: Implémenter.** Matricule étudiant : algorithme de `gestion_eleves/models.py:313-318` (année = 2 chiffres de début du libellé, `num` = `max(id)+1` des étudiants). Enseignant/employé : `{prefixe}-{num:05d}` avec `num` = nombre existant + 1, recalculé jusqu'à trouver un matricule libre. `email` vide → `None` avant sauvegarde.
- [ ] **Step 4: Migrations** — `makemigrations core` → `0001_initial` (référentiel + personnes). Tests Task 1 + Task 2 → PASS.
- [ ] **Step 5: Commit** — `feat(core): fiches personnes uniques et matricules`

---

### Task 3: Droits par module et rôles contextuels

**Files:**
- Create: `erp/backend/core/droits.py`, `erp/backend/core/migrations/0002_groupes_modules.py`, `erp/backend/core/models/acces.py`, `erp/backend/core/permissions.py`
- Test: `erp/backend/core/tests/test_droits.py`

**Interfaces:**
- Produces:
  - `core.droits.MODULES: dict[str, dict]` — ordre d'affichage du lanceur :
    ```python
    MODULES = {
        "scolarite":  {"libelle": "Scolarité",              "niveaux": ["secretariat", "faculte"]},
        "edt":        {"libelle": "Emploi du temps",        "niveaux": ["utilisateur", "responsable"]},
        "rh":         {"libelle": "Ressources humaines",    "niveaux": ["utilisateur", "responsable"]},
        "finance":    {"libelle": "Finance",                "niveaux": ["utilisateur", "responsable"]},
        "logistique": {"libelle": "Logistique",             "niveaux": ["utilisateur", "responsable"]},
        "parametres": {"libelle": "Paramètres",             "niveaux": ["responsable"]},
    }
    ```
  - `nom_groupe(module: str, niveau: str) -> str` ; `niveaux_utilisateur(user, module: str) -> list[str]` ; `a_droit(user, module: str, niveau: str | None = None) -> bool` ; `modules_accessibles(user) -> list[dict]` (`{"code", "libelle", "niveaux"}`, superuser = tous niveaux) ; `roles_contextuels(user) -> list[str]` parmi `"etudiant"`, `"enseignant"`, `"chef_departement"`, `"employe"` ; `definir_droits(user, groupes: list[str]) -> None` (refuse tout nom hors `MODULES`, `ValueError`).
  - `core.models.acces.RattachementFaculte(user OneToOne related_name='rattachement_faculte', faculte FK CASCADE)` ; `core.droits.faculte_rattachee(user) -> Faculte | None`.
  - `core.permissions.CompteActif` (BasePermission : 403 `code='profil_suspendu'` si `user.personne.est_suspendue`) ; `core.permissions.droit_module(module: str, niveau: str | None = None) -> type[BasePermission]` ; `core.permissions.LectureAuthentifieeEcritureParametres`.
  - Le référentiel « référent de classe » arrive en phase 2 avec l'EDT ; `roles_contextuels` est prévu pour être étendu (liste de fonctions enregistrées `ROLES_CONTEXTUELS: list[Callable[[User], str | None]]`).

- [ ] **Step 1: Tests qui échouent**

```python
def test_groupes_crees_par_migration(self):
    self.assertTrue(Group.objects.filter(name="scolarite_faculte").exists())
    self.assertEqual(Group.objects.filter(name__regex=r"^(scolarite|edt|rh|finance|logistique|parametres)_").count(), 11)
def test_modules_accessibles(self):   # user dans rh_responsable → [{"code":"rh","libelle":"Ressources humaines","niveaux":["responsable"]}]
def test_superuser_tout(self):        # 6 modules, tous niveaux
def test_a_droit_niveau(self):        # rh_utilisateur : a_droit(u,"rh") True, a_droit(u,"rh","responsable") False
def test_definir_droits_refuse_inconnu(self):  # ValueError sur "compta_responsable"
def test_roles_contextuels(self):     # enseignant chef d'un département → ["enseignant","chef_departement"]
def test_compte_actif_refuse_suspendu(self):  # vue de test avec CompteActif → 403, data["code"]=="profil_suspendu"
def test_droit_module_permission(self):       # droit_module("rh") : 403 sans groupe, 200 avec
```

- [ ] **Step 2: Lancer** → FAIL.
- [ ] **Step 3: Implémenter** `droits.py`, `permissions.py`, `acces.py`, la migration de données (`RunPython` qui crée les 11 groupes à partir de `MODULES`, réversible).
- [ ] **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `feat(core): droits par module et rôles contextuels`

---

### Task 4: Connexion JWT unique et `/api/core/moi/`

**Files:**
- Create: `erp/backend/core/auth.py`, `erp/backend/core/throttles.py`, `erp/backend/core/pagination.py`, `erp/backend/core/exceptions.py`, `erp/backend/core/urls.py`
- Modify: `erp/backend/config/settings.py` (REST_FRAMEWORK, SIMPLE_JWT, CORS), `erp/backend/config/urls.py`
- Test: `erp/backend/core/tests/test_auth.py`

**Interfaces:**
- Consumes: Task 3 (`modules_accessibles`, `roles_contextuels`, `faculte_rattachee`, `CompteActif`).
- Produces (HTTP) :
  - `POST /api/core/token/` `{username, password}` → 200 `{access, refresh, user: Moi}` ; 401 identifiants faux `{"detail": "Identifiant ou mot de passe incorrect."}` ; 401 suspendu `{"detail": "Votre profil est suspendu. Motif : …", "code": "profil_suspendu"}` ; 429 au-delà des débits.
  - `POST /api/core/token/refresh/` `{refresh}` → `{access, refresh}` ; refusé (401 `profil_suspendu`) si la personne est suspendue entre-temps.
  - `POST /api/core/deconnexion/` `{refresh}` → 205, refresh blacklisté.
  - `GET /api/core/moi/` → `Moi = {id, username, nom_complet, photo, personne_id, modules: [{code, libelle, niveaux}], roles: [str], faculte_rattachee: {id, code, nom} | null}`.
  - `core.auth.construire_moi(user, request) -> dict` (réutilisé par login et `/moi/`).
  - Le payload JWT ne contient que `user_id`, `username`, `nom_complet` (les droits sont relus via `/moi/`, pour qu'un retrait de droit prenne effet sans attendre l'expiration du jeton).
- Reprises : `throttles.py` = `uccb_backend/EDT_app/throttles.py` (scopes `login`, `login_ip`) ; `pagination.py` = `EDT_app/pagination.py` ; `exceptions.py` = `EDT_app/exception_handlers.py` (convertit `django.core.exceptions.ValidationError` en 400 et `ProtectedError` en 400 « … est encore utilisé par … ») ; logique de suspension = `EDT_app/authentication.py:18-60,148-170`.
- Settings : `DEFAULT_PERMISSION_CLASSES = [IsAuthenticated, core.permissions.CompteActif]`, authentification JWT seule (pas de session pour l'API), débits de la section Global Constraints.

- [ ] **Step 1: Tests qui échouent**

```python
def test_login_renvoie_moi(self):          # 200 ; r.data["user"]["modules"] == [{"code":"rh",...}]
def test_login_mauvais_mot_de_passe(self): # 401 + message exact
def test_login_suspendu(self):             # 401, code "profil_suspendu", motif dans detail
def test_jeton_valide_puis_suspension(self):  # login OK, suspension, GET /moi/ → 403 code profil_suspendu
def test_refresh_refuse_apres_suspension(self):
def test_deconnexion_blackliste(self):     # refresh réutilisé après déconnexion → 401
def test_moi_sans_module(self):            # modules == [], roles == ["employe"]
def test_throttle_login(self):             # 31e tentative sur le même compte → 429 (override_settings débit bas)
def test_protected_error_400(self):        # via exceptions.py : supprimer faculté utilisée → 400
```

- [ ] **Step 2: Lancer** → FAIL.
- [ ] **Step 3: Implémenter** les vues (sous-classes de `TokenObtainPairView` / `TokenRefreshView` avec `throttle_classes`), `MoiView`, `DeconnexionView`, URLs `config/urls.py` : `path("api/core/", include("core.urls"))`, `path("admin/", admin.site.urls)`.
- [ ] **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `feat(core): connexion JWT unique et profil /moi`

---

### Task 5: API Paramètres — référentiel et établissement

**Files:**
- Create: `erp/backend/core/api/__init__.py`, `erp/backend/core/api/referentiel.py` (serializers + viewsets), `erp/backend/core/api/etablissement.py`
- Modify: `erp/backend/core/urls.py`
- Test: `erp/backend/core/tests/test_api_referentiel.py`

**Interfaces:**
- Consumes: Task 1 modèles, Task 3 `LectureAuthentifieeEcritureParametres`, Task 4 pagination/exceptions.
- Produces (routeur DRF sous `/api/core/`) : `annees`, `periodes`, `facultes`, `departements`, `portails`, `filieres`, `parcours`, `classes`, `ues`, `ecs` — CRUD ; lecture pour tout utilisateur authentifié, écriture `parametres_responsable`. Filtres query : `periodes?annee=`, `departements?faculte=`, `portails?faculte=`, `filieres?departement=&portail=&faculte=`, `classes?annee=&parcours=&faculte=`, `ues?semestre=&portail=&filiere=`, `ecs?ue=&departement=&semestre=`. Action `POST annees/{id}/definir_en_cours/`. `GET|PUT /api/core/etablissement/`. Les serializers exposent les libellés lisibles (`faculte_code`, `classe.libelle`, `parcours.code`).
- Les erreurs de `full_clean()` remontent en 400 par champ via `exceptions.py`.

- [ ] **Step 1: Tests qui échouent**

```python
def test_lecture_authentifie_ecriture_parametres(self):  # GET 200 pour user sans droit ; POST 403 ; POST 201 avec parametres_responsable
def test_classe_incoherente_400(self):   # POST classe L1 + filiere → 400, "filiere" dans r.data
def test_filtre_filieres_par_faculte(self):
def test_supprimer_faculte_utilisee_400(self):
def test_definir_en_cours(self):
def test_etablissement_get_put(self):
```

- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `feat(core): API Paramètres du référentiel`

---

### Task 6: API Paramètres — personnes, utilisateurs et audit

**Files:**
- Create: `erp/backend/core/models/audit.py`, `erp/backend/core/audit.py`, `erp/backend/core/api/personnes.py`, `erp/backend/core/api/utilisateurs.py`
- Modify: `erp/backend/core/urls.py`, `erp/backend/core/models/__init__.py`
- Test: `erp/backend/core/tests/test_api_utilisateurs.py`

**Interfaces:**
- Produces :
  - `JournalAudit(utilisateur FK null SET_NULL, module: str, action: str, description, adresse_ip null, date auto)` ; `core.audit.journaliser(request, module: str, action: str, description: str = "") -> JournalAudit` (IP via `X-Forwarded-For` puis `REMOTE_ADDR`).
  - `GET /api/core/personnes/?q=&role=etudiant|enseignant|employe` (lecture : tout utilisateur ayant au moins un module ; écriture : `parametres_responsable`) ; actions `POST personnes/{id}/suspendre/ {motif}`, `POST personnes/{id}/reactiver/`.
  - `/api/core/utilisateurs/` (`parametres_responsable` seulement) : champs `id, username, is_active, personne_id, groupes: [str], faculte_rattachee_id` ; création `{username, password, personne_id?, groupes, faculte_rattachee_id?}` ; `POST utilisateurs/{id}/mot_de_passe/ {password}` (validateurs Django) ; `GET /api/core/modules/` → `MODULES` sous forme de liste.
  - `GET /api/core/audit/?module=&utilisateur=` (lecture seule, `parametres_responsable`).
  - Journalisées : création/modif d'utilisateur, changement de droits, mot de passe, suspension, réactivation.

- [ ] **Step 1: Tests qui échouent**

```python
def test_creer_utilisateur_avec_droits(self):  # 201 ; groupes appliqués ; JournalAudit action "creation_utilisateur"
def test_groupe_inconnu_400(self):
def test_mot_de_passe_trop_simple_400(self):
def test_suspendre_exige_motif(self):          # 400 sans motif ; 200 avec, puis login → 401 profil_suspendu
def test_non_parametres_403(self):
def test_audit_filtre_module(self):
```

- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `feat(core): API utilisateurs, personnes et journal d'audit`

---

### Task 7: Jeu de données du socle

**Files:**
- Create: `erp/backend/core/management/__init__.py`, `erp/backend/core/management/commands/__init__.py`, `erp/backend/core/management/commands/seed_socle.py`, `erp/backend/README.md`
- Test: `erp/backend/core/tests/test_seed.py`

**Interfaces:**
- Produces : `python manage.py seed_socle [--reset]` — idempotent. Crée : année `2026-2027` en cours avec 2 périodes ; facultés `FST` (Sciences et Techniques) et `FSE` (Sciences Économiques) ; 2 départements par faculté ; portails `MIP`, `BCG` (FST) et `ECO` (FSE) ; 2 filières par département ; parcours L1–L3, M1, M2 ; classes L1 par portail et L2/L3 par filière ; 2 UE × 3 EC pour L1 MIP ; comptes `admin` (superuser), `parametres`, un compte par groupe de module (`<groupe>` comme identifiant), un enseignant chef de département, un employé sans droit. Les phases suivantes ajoutent leurs propres `seed_<module>` ; une phase 6 les enchaîne dans `seed_demo`.
- `README.md` : installation, `.env`, migrations, `seed_socle`, lancement, tableau des comptes de démo avec le mot de passe de démo commun `Uccb!2026demo` (valeur de démonstration, à changer hors démo).
- `--reset` refuse de s'exécuter si `DEBUG=False`.

- [ ] **Step 1: Test** — `test_seed_idempotent` : `call_command("seed_socle")` deux fois → mêmes comptes (`User.objects.count()` stable), `AnneeAcademique.courante().libelle == "2026-2027"`, l'utilisateur `rh_responsable` a `modules_accessibles == [rh]`.
- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS ; lancer toute la suite `manage.py test core` → PASS.
- [ ] **Step 5: Commit** — `feat(core): jeu de données du socle et README`

---

### Task 8: SPA — base, client API et connexion

**Files:**
- Create (copiés de `Projet-Gestion-Acad-mique-main/edt-frontend`, puis adaptés) : `erp/frontend/{package.json,vite.config.js,tailwind.config.js,postcss.config.js,jsconfig.json,components.json,index.html,eslint.config.js,.gitignore,.env.example}`, `erp/frontend/src/{main.jsx,index.css}`, `src/components/ui/*`, `src/components/shared/*`, `src/components/ErrorBoundary.jsx`, `src/lib/{utils,confirmer,messageConnexion}.js`, `src/assets/login/*`, `src/features/auth/{LoginPage.jsx,useLogin.js}`
- Create: `erp/frontend/src/api/client.js`, `src/api/auth.js`, `src/store/authStore.js`
- Test: `erp/frontend/src/store/authStore.test.js`, `erp/frontend/vitest.config.js` (ou section `test` de `vite.config.js`)

**Interfaces:**
- Consumes: Task 4 (endpoints et forme `Moi`).
- Produces :
  - `src/api/client.js` : instance axios `apiClient` (`baseURL: '/api'`), reprise de `edt-frontend/src/api/client.js` (rafraîchissement unique partagé, délai 30 s, repérage `profil_suspendu` → `clearAuth()` + message de connexion) avec les routes `/core/token/` et `/core/token/refresh/`.
  - `src/api/auth.js` : `login(username, password) -> Promise<Moi>`, `logout() -> Promise<void>` (appelle `/core/deconnexion/` puis `clearAuth`), `fetchMoi() -> Promise<Moi>`.
  - `src/store/authStore.js` (zustand persist, clé `erp-auth`) : état `{accessToken, refreshToken, user: Moi|null, isAuthenticated}` ; actions `setAuth`, `setTokens`, `setUser`, `clearAuth` ; sélecteurs `selectModules(state) -> Moi.modules`, `aDroit(state, module, niveau?) -> bool`, `aRole(state, role) -> bool`.
  - `LoginPage` : visuel EDT (`CampusShowcase`/photos campus), titre « UCCB — Système de gestion », après succès redirige vers `location.state.from` ou `/`.
- `vite.config.js` : alias `@`, proxy `/api` et `/media` → `http://127.0.0.1:8000`, `base: '/'`, `build.outDir: '../backend/frontend_dist'`. Supprimer de la copie tout ce qui est propre à l'EDT métier (features planning, etc. — ils reviennent en phase 2).
- Dépendances : celles d'`edt-frontend/package.json` + `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom` en dev.

- [ ] **Step 1: Copier et nettoyer** la base ; `npm install` ; `npm run build` → succès.
- [ ] **Step 2: Tests qui échouent** (`authStore.test.js`) :

```js
it('aDroit sans niveau', () => { setUser({ modules: [{ code: 'rh', niveaux: ['utilisateur'] }] }); expect(aDroit(get(), 'rh')).toBe(true); expect(aDroit(get(), 'finance')).toBe(false); });
it('aDroit avec niveau', () => { expect(aDroit(get(), 'rh', 'responsable')).toBe(false); });
it('clearAuth vide tout', () => { /* isAuthenticated false, user null */ });
```

- [ ] **Step 3: Lancer** — `cd erp/frontend && npx vitest run` → FAIL. **Step 4: Implémenter.** **Step 5: Lancer** → PASS.
- [ ] **Step 6: Commit** — `feat(frontend): base SPA ERP, client API et connexion`

---

### Task 9: Lanceur, layout de module et gardes de route

**Files:**
- Create: `erp/frontend/src/app/modules.js`, `src/app/router.jsx`, `src/app/RequireAuth.jsx`, `src/app/RequireModule.jsx`, `src/app/Lanceur.jsx`, `src/app/ModuleShell.jsx`, `src/app/ModuleSidebar.jsx`, `src/app/Topbar.jsx`, `src/app/pages/{Interdit,Introuvable}.jsx`
- Test: `src/app/modules.test.js`, `src/app/RequireModule.test.jsx`, `src/app/Lanceur.test.jsx`

**Interfaces:**
- Consumes: Task 8 (`authStore`, `aDroit`, `fetchMoi`).
- Produces :
  - `src/app/modules.js` : `REGISTRE: Array<{ code, libelle, description, icone: LucideIcon, chemin: '/'+code, menu: Array<{ chemin, libelle, icone, niveaux?: string[] }> }>` — en phase 1 seul `parametres` a un menu ; les autres modules sont déclarés avec `menu: []` et une page « Module disponible dans une prochaine version ». Les phases suivantes remplissent leur entrée. `modulesVisibles(moi: Moi) -> REGISTRE[]` (intersection avec `moi.modules`, ordre du registre) ; `menuVisible(module, niveaux: string[]) -> menu[]`.
  - `RequireAuth` : non connecté → `<Navigate to="/login" state={{ from: location }} />` ; au montage, rafraîchit `user` via `fetchMoi()` (droits à jour).
  - `RequireModule({ module, niveau? })` : sans droit → rend `<Interdit />` **dans** le layout (pas de redirection).
  - `ModuleShell({ module })` : reprend `edt-frontend/src/components/layout/AppShell.jsx` ; `ModuleSidebar` = `Sidebar.jsx` de l'EDT avec en-tête « UCCB · {libelle module} », bouton lanceur (icône `LayoutGrid`, `aria-label="Retour aux modules"`) vers `/`, menu filtré par `menuVisible`, déconnexion ; `Topbar` = `Topbar.jsx` de l'EDT avec menu utilisateur (profil, déconnexion).
  - `Lanceur` : en-tête (logo, nom de l'utilisateur, menu utilisateur) ; grille responsive de tuiles (`Card` shadcn : icône 32 px dans un carré `bg-primary/10 text-primary`, libellé, description) ; état vide « Aucun module ne vous est attribué. Contactez l'administrateur. » ; si l'utilisateur a le rôle `etudiant` ou `enseignant`, une tuile « Mon espace » (`/moi`, page provisoire en phase 1).
  - Routes : `/login`, `/` (Lanceur), `/:module/*` via `ModuleShell` + `RequireModule`, `/moi/*`, `*` → `Introuvable`.

- [ ] **Step 1: Tests qui échouent**

```js
it('modulesVisibles filtre et ordonne', () => expect(modulesVisibles({ modules: [{ code: 'finance' }, { code: 'rh' }] }).map(m => m.code)).toEqual(['rh', 'finance']));
it('Lanceur vide', () => { render(<Lanceur/>) avec moi.modules = [] ; expect(screen.getByText(/Aucun module ne vous est attribué/)).toBeInTheDocument(); });
it('RequireModule sans droit affiche 403', () => { /* route /parametres sans droit → texte "Accès non autorisé", URL inchangée */ });
it('RequireAuth redirige vers /login avec from', () => { /* MemoryRouter initialEntries ['/rh'] → LoginPage, state.from.pathname === '/rh' */ });
```

- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: Commit** — `feat(frontend): lanceur de modules et layout commun`

---

### Task 10: Écrans Paramètres

**Files:**
- Create: `erp/frontend/src/modules/parametres/{routes.jsx,api.js,hooks.js}`, `src/modules/parametres/pages/{Referentiel.jsx,Classes.jsx,Enseignement.jsx,Utilisateurs.jsx,Personnes.jsx,Etablissement.jsx,Audit.jsx}`, `src/modules/parametres/components/*`
- Modify: `src/app/modules.js` (menu `parametres`)
- Test: `src/modules/parametres/pages/Utilisateurs.test.jsx`, `src/modules/parametres/pages/Classes.test.jsx`

**Interfaces:**
- Consumes: Task 5 et 6 (endpoints), Task 9 (`ModuleShell`, registre), composants `DataTable`, `FormModal`, `ConfirmDialog`, `ErreurFormulaire`, `PageHeader` repris de l'EDT.
- Produces : menu Paramètres = Référentiel (années + périodes, facultés, départements, portails, filières, parcours — onglets `Tabs`), Classes, Enseignement (UE + EC), Personnes, Utilisateurs & droits, Établissement, Journal d'audit. Formulaires react-hook-form + zod ; les erreurs 400 par champ du backend s'affichent sous le champ (pattern `ErreurFormulaire` de l'EDT). Écran Utilisateurs : une ligne par module avec un sélecteur de niveau (« Aucun » + niveaux du module) et, si un niveau Scolarité est choisi, un sélecteur de faculté de rattachement (« Toutes les facultés » par défaut). Données via TanStack Query (`queryKey: ['parametres', ressource, filtres]`), invalidation après mutation, toasts de succès/erreur.

- [ ] **Step 1: Tests qui échouent** (API simulée avec `vi.mock('@/api/client')`) :

```js
it('Utilisateurs envoie les groupes choisis', async () => { /* choisir RH = Responsable, Scolarité = Faculté + FST ; soumettre ; post appelé avec { groupes: ['rh_responsable','scolarite_faculte'], faculte_rattachee_id: 1 } */ });
it('Classes affiche l’erreur de champ du serveur', async () => { /* post rejette 400 { filiere: ['…'] } ; le message apparaît sous le champ Filière */ });
```

- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS ; `npm run lint` et `npm run build` → sans erreur.
- [ ] **Step 5: Commit** — `feat(parametres): écrans d'administration du socle`

---

### Task 11: Service de la SPA par Django et test de bout en bout

**Files:**
- Create: `erp/backend/core/spa.py`, `erp/frontend/playwright.config.js`, `erp/frontend/e2e/01-socle.spec.js`
- Modify: `erp/backend/config/urls.py`, `erp/backend/config/settings.py` (`STATIC*`, `MEDIA*`, `FRONTEND_DIST = BASE_DIR / 'frontend_dist'`), `erp/backend/README.md`, `erp/backend/.gitignore` (`frontend_dist/`)
- Test: `erp/backend/core/tests/test_spa.py`

**Interfaces:**
- Produces : `core.spa.spa_index(request) -> HttpResponse` sert `FRONTEND_DIST/index.html` (503 « Interface non construite : lancez npm run build » si absent) ; route catch-all `re_path(r"^(?!api/|admin/|media/|static/).*$", spa_index)` en dernier ; les fichiers `assets/` du build servis via `STATICFILES_DIRS`.
- E2E Playwright : démarre Django (port 8011, SQLite jetable, `seed_socle`) et Vite (port 3011).

- [ ] **Step 1: Tests backend qui échouent** — `test_route_profonde_sert_index` (`GET /rh/enseignants` → 200 avec un `index.html` factice dans un `FRONTEND_DIST` temporaire), `test_api_inconnue_404_json` (`GET /api/inexistant/` → 404, pas l'index), `test_build_absent_503`.
- [ ] **Step 2: Lancer** → FAIL. **Step 3: Implémenter.** **Step 4: Lancer** → PASS.
- [ ] **Step 5: E2E** `01-socle.spec.js` :
  - `parametres` se connecte → voit la tuile « Paramètres » seule → crée une faculté → la retrouve dans la liste ;
  - `rh_responsable` ouvre `/parametres` → « Accès non autorisé » ;
  - l'employé sans droit → « Aucun module ne vous est attribué » ;
  - un compte suspendu par `parametres` pendant sa session → au clic suivant, renvoyé au login avec le motif.
  
  Run : `cd erp/frontend && npx playwright test` → 4 passed.
- [ ] **Step 6: Commit** — `feat: service de la SPA par Django et tests de bout en bout du socle`

---

## Hors de cette phase

Utilitaires PDF, QR code et Excel (spec §6.4) : ajoutés à `core` en phase 3, quand la Scolarité en a besoin. Validation des fichiers téléversés (`fichiers.py`) : phase 2. Grille de tarifs : phase 5.

## Phases suivantes (plans séparés, écrits à la fin de la phase précédente)

2. EDT + Espace personnel planning — `docs/superpowers/plans/…-erp-phase2-edt.md`
3. Scolarité + Espace étudiant notes
4. RH
5. Finance (dont `Tarif` dans Paramètres)
6. Logistique, `seed_demo`, passe finale
