# ERP UCCB — Phase 3 : Scolarité — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter l'ancienne scolarité (`uccb_backend/gestion_eleves` + `api/api_faculte.py`, `api/api_secretariat.py`, `api/api_etudiant.py`) comme module `scolarite` de l'ERP : inscriptions annuelles, notes, moteur de calcul, délibérations, promotion, orientation, documents officiels avec QR code ; et l'espace étudiant (notes, planning, enseignants).

**Architecture:** App Django `erp/backend/scolarite` sur le socle (`core.Etudiant`, `core.Classe`, `core.UniteEnseignement`, `core.ElementConstitutif`) ; le moteur `engine.py` est porté sans changer ses règles. Utilitaires PDF/QR/Excel dans `core/documents.py`. Frontend `erp/frontend/src/modules/scolarite` (style EDT) et extension de `modules/moi` pour l'étudiant.

**Tech Stack:** celle des phases 1–2 ; ajout de `xhtml2pdf`, `qrcode[pil]`, `openpyxl` (déjà utilisés par l'ancienne scolarité).

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md` (§7.1, §7.7) ; phases précédentes : `docs/superpowers/plans/2026-11-18-erp-phase1-socle.md`, `docs/superpowers/plans/2026-11-19-erp-phase2-edt.md`.

## Global Constraints

- Sources à porter (lecture seule) : `/home/it-junior/Gestion-Universit-/uccb_backend/gestion_eleves/` (engine.py, models.py, views_secretaire.py, views_faculte.py, pdf_utils.py, templates `documents/`) et `/home/it-junior/Gestion-Universit-/uccb_backend/api/`.
- **Règles de calcul inchangées** (spec §7.1) : moyenne EC = `(devoir+session)/2`, avec SR `max(normale, (devoir+2×SR)/3)`, absent = 0 ; note < 6 éliminatoire ; ADMIS si moyenne semestre ≥ 10 sans éliminatoire, alors tous les crédits du semestre acquis ; sinon UE validée si moyenne UE ≥ 6 ; EC sans note ignoré ; mentions Passable [10,12), Assez bien [12,14), Bien [14,16), Très bien ≥ 16 ; rang par moyenne décroissante.
- **Inscription annuelle** : une par étudiant et par année, dans une classe annuelle ; notes par (inscription, EC) ; un `ResultatSemestre` par (inscription, semestre).
- Droits : `scolarite_secretariat` (étudiants, inscriptions, statuts, attestations, relevés), `scolarite_faculte` (notes, délibérations, promotion, orientation, matrice A3) ; rattachement à une faculté = périmètre limité à cette faculté (phase 1, `RattachementFaculte`).
- API sous `/api/scolarite/…` ; espace étudiant sous `/api/scolarite/moi/…`.
- Une notification d'inscription est émise pour la Finance (phase 5) : liste de rappels `scolarite.inscriptions.APRES_INSCRIPTION`.

## Décisions soumises à validation

1. **Compte étudiant : activation par l'étudiant** (comme l'ancienne scolarité). Le secrétariat crée la fiche et l'inscription ; l'étudiant active son compte depuis la page de connexion avec son **matricule, son e-mail et sa date de naissance** enregistrés, puis choisit son mot de passe. Son identifiant de connexion est son matricule.
2. **Documents en PDF** téléchargés (attestation, relevé, matrice A3), avec un QR code sur l'attestation et le relevé.
3. **Page de vérification publique** ouverte par le QR code : elle confirme l'authenticité (nom, matricule, type de document, semestre, décision, date d'émission) **sans afficher le détail des notes**. L'ancienne page publique affichait toutes les notes à partir de l'identifiant de l'étudiant.
4. **Export Excel de la délibération** rétabli (la spec le prévoit ; l'ancienne scolarité l'avait retiré au profit de la matrice A3).

## Review Focus

1. Note saisie hors bornes (21, −1, « abc ») ou SR sans note de session → 400 par cellule, la saisie des autres notes de la grille n'est pas perdue.
2. Utilisateur `scolarite_faculte` rattaché à la FST qui ouvre un étudiant, une classe ou une délibération de la FSE → 404.
3. Délibération d'un semestre où certaines notes manquent → les EC sans note sont ignorés (pas comptés 0), et l'écran le signale.
4. Promotion ou orientation lancée deux fois pour le même étudiant → aucune deuxième inscription ; message « déjà inscrit pour l'année suivante ».
5. Jeton de vérification inconnu ou modifié → page « document introuvable », jamais d'erreur 500 ni d'information sur d'autres étudiants.

---

### Task 1: Inscriptions, notes et résultats

**Files:** Create `erp/backend/scolarite/{__init__,apps,admin,models,inscriptions}.py`, `scolarite/tests/{__init__,fabriques,test_modeles}.py` ; Modify `config/settings.py` (INSTALLED_APPS), `requirements.txt` (xhtml2pdf, qrcode[pil], openpyxl).

**Interfaces:**
- `Inscription(etudiant FK core.Etudiant PROTECT related_name='inscriptions', classe FK core.Classe PROTECT, type 'premiere'|'reinscription', statut 'active'|'terminee'|'abandonnee', date_inscription, created_at)` ; contrainte et contrôle : une inscription par (étudiant, année de la classe) ; classe non archivée ; propriété `annee`.
- `Note(inscription FK related_name='notes', ec FK core.ElementConstitutif PROTECT, note_devoir, note_session : Decimal 0–20 null, note_sr Decimal 0–20 null, est_absent bool, moyenne Decimal stockée)` ; unique (inscription, ec) ; `calculer() -> float | None` (formule de la spec ; `None` tant que devoir et session ne sont pas saisis, sauf absent) ; SR sans session → erreur.
- `ResultatSemestre(inscription FK related_name='resultats', semestre 'S1'…'S10', moyenne, credits_obtenus, credits_totaux, decision 'ADMIS'|'AJOURNÉ', mention, rang, delibere_le, delibere_par FK User null)` ; unique (inscription, semestre).
- `scolarite.inscriptions.inscrire(etudiant, classe, *, type, date=None) -> Inscription` : crée l'inscription, les lignes de notes vides de tous les EC au programme de la classe (`edt.views.ecs_de_classe` déplacé dans `core` : `core.models.Classe.ecs_au_programme()`), puis appelle chaque rappel de `APRES_INSCRIPTION`.
- [ ] Tests : formule (normale, SR meilleure, SR moins bonne, absent), bornes 0–20, unicité annuelle, notes créées pour les EC de S1 et S2 d'une L1, rappel appelé. FAIL → implémenter → PASS (`manage.py test scolarite edt core`). Commit.

### Task 2: Moteur de calcul

**Files:** Create `scolarite/moteur.py`, `scolarite/tests/test_moteur.py`.

**Interfaces:**
- `ligne_etudiant(inscription, semestre) -> dict` : `{inscription, ues: [{ue, ecs: [{ec, note|None, devoir, session, sr, absent, non_saisi}], moyenne_ue, credits_ue, validee}], moyenne, eliminatoire, decision, mention, credits_valides, credits_totaux, ecs_non_saisis}` — port de `calculer_ligne_etudiant` (EC sans note ignoré, crédits totaux = tous les EC du semestre).
- `deliberation(classe, semestre, *, enregistrer=False, par=None) -> list[dict]` : lignes de toutes les inscriptions actives de la classe, triées par moyenne décroissante avec rang ; `enregistrer=True` écrit les `ResultatSemestre` (rang, date, auteur).
- Requêtes bornées : notes et EC chargés en une fois pour toute la classe.
- [ ] Tests portés des règles (éliminatoire, compensation, mentions aux bornes 10/12/14/16, EC non saisi ignoré, rang, enregistrement idempotent) + test « nombre de requêtes indépendant du nombre d'étudiants ». FAIL → PASS. Commit.

### Task 3: Périmètre et API Secrétariat

**Files:** Create `scolarite/perimetre.py`, `scolarite/permissions.py`, `scolarite/serializers.py`, `scolarite/views_secretariat.py`, `scolarite/urls.py`, `scolarite/tests/test_api_secretariat.py` ; Modify `config/urls.py`.

**Interfaces:**
- `facultes_autorisees(user) -> QuerySet | None`, `restreindre_par_faculte(qs, user, champ)` (rattachement → une faculté ; sinon toutes).
- `etudiants/` : liste (filtres `q`, `classe`, `annee`, `statut`, `faculte`), fiche (identité + inscriptions), création en un appel `{personne: {...}, classe, date_inscription}` → Personne + Etudiant (matricule) + inscription « premiere » ; `POST etudiants/{id}/statut/ {statut}` (actif/diplôme/abandon ; abandon termine l'inscription active).
- `inscriptions/` : liste, création (réinscription d'un étudiant existant), changement de classe dans la même année tant qu'aucune note n'est saisie.
- Droits : `scolarite_secretariat` en écriture ; `scolarite_faculte` en lecture. Journal d'audit sur création, statut, inscription.
- [ ] Tests : création complète, matricule, refus seconde inscription la même année, périmètre faculté → 404 (Review Focus 2), faculté en lecture seule. FAIL → PASS. Commit.

### Task 4: API Faculté — notes, délibération, promotion, orientation

**Files:** Create `scolarite/views_faculte.py`, `scolarite/excel.py`, `scolarite/tests/test_api_faculte.py`.

**Interfaces:**
- `GET saisie/?classe=&ec=` → lignes `{note_id, etudiant, matricule, nom_complet, devoir, session, sr, absent, moyenne}` ; `POST saisie/ {notes: [{note_id, devoir, session, sr, absent}]}` → enregistre les lignes valides, renvoie `{enregistrees: n, erreurs: {note_id: {champ: message}}}` (Review Focus 1, réponse 200 si au moins une ligne valide, 400 si aucune).
- `GET etudiants/{id}/notes/?annee=` → relevé par semestre (moteur).
- `GET deliberation/?classe=&semestre=` (calcul à la volée, `ecs_non_saisis` par ligne, Review Focus 3) ; `POST deliberation/ {classe, semestre}` (enregistre les résultats) ; `GET deliberation/excel/?classe=&semestre=` (classeur `.xlsx` : une ligne par étudiant, moyennes UE, moyenne, crédits, décision, mention, rang).
- `GET promotion/?classe=` (étudiants avec résultats des deux semestres et décisions) ; `POST promotion/ {classe, etudiants: [ids]}` → pour chacun, inscription « reinscription » dans la classe du niveau suivant de l'année suivante (même filière, ou même portail pour une L1… voir orientation), inscription courante terminée ; déjà inscrit → ignoré avec message (Review Focus 4) ; classe cible absente → erreur explicite.
- `POST orientation/ {classe (L1), choix: {etudiant_id: filiere_id}}` → passage en L2 dans la filière choisie (filière d'un département de la même faculté, portail d'origine = portail de la L1).
- Droits : `scolarite_faculte` (périmètre faculté).
- [ ] Tests : saisie partielle avec erreurs par cellule, délibération avec EC manquant, enregistrement, export Excel (ouvrable par openpyxl, en-têtes), promotion et orientation idempotentes, périmètre. FAIL → PASS. Commit.

### Task 5: Documents officiels et vérification

**Files:** Create `core/documents.py` (PDF xhtml2pdf + `link_callback` de `pdf_utils.py`, QR PNG en data URI), `scolarite/documents.py`, `scolarite/models.py` (`DocumentEmis`), templates `scolarite/templates/scolarite/{attestation,releve,matrice_a3,verification}.html` (portés des templates `documents/` de la source), `scolarite/tests/test_documents.py`.

**Interfaces:**
- `DocumentEmis(jeton: str unique 32 caractères aléatoires (secrets.token_urlsafe), type 'attestation'|'releve', inscription FK, semestre, decision, emis_le, emis_par FK User)`.
- `GET etudiants/{id}/attestation.pdf?annee=` et `releve.pdf?semestre=&annee=` (secrétariat) : créent un `DocumentEmis`, QR vers `{BASE_URL}/verifier/{jeton}` ; `GET matrice-a3.pdf?classe=&semestre=` (faculté) — signataire = doyen de la faculté (`Faculte.signataire_pv`), secrétaire et ville depuis `ParametresEtablissement`.
- Page publique Django (hors SPA) `GET /verifier/<jeton>` : rendu serveur ; inconnu → 404 « document introuvable » (Review Focus 5) ; affiche seulement nom, matricule, type, semestre, décision, date d'émission.
- `settings.BASE_URL` (env `BASE_URL`, défaut `http://localhost:8000`) ; la route catch-all de la SPA exclut `verifier/`.
- [ ] Tests : PDF non vide (`%PDF`), QR présent, jeton unique, page de vérification (connu / inconnu / modifié), aucune note détaillée sur la page. FAIL → PASS. Commit.

### Task 6: Compte et espace étudiant

**Files:** Create `scolarite/views_etudiant.py`, `scolarite/tests/test_espace_etudiant.py` ; Modify `scolarite/urls.py`, `core/auth.py` (aucun changement de connexion : l'identifiant est le matricule).

**Interfaces:**
- `POST /api/scolarite/activation/ {matricule, email, date_naissance, password}` (anonyme, limité comme la connexion) : si les trois correspondent à un étudiant actif sans compte → crée le `User` (username = matricule), le lie à la personne ; sinon 400 « Informations incorrectes ou compte déjà activé » (même message dans tous les cas).
- `GET moi/notes/` (résultats et notes de l'étudiant connecté, par année et semestre), `GET moi/planning/?date_debut=&date_fin=` (séances publiées de sa classe de l'année en cours, filtre sur le jour effectif comme l'EDT), `GET moi/enseignants/` (enseignants affectés à sa classe : nom, photo, grade, EC — le trombinoscope).
- [ ] Tests : activation (succès, mauvaise date, double activation, étudiant abandonné), notes visibles seulement pour soi, planning limité à sa classe et aux séances publiées. FAIL → PASS. Commit.

### Task 7: Données de démonstration

**Files:** Create `scolarite/management/commands/seed_scolarite.py`, `scolarite/tests/test_seed.py` ; Modify `README.md`.
- `seed_scolarite` (DEBUG seulement, idempotent, après `seed_socle` et `seed_edt`) : ~60 étudiants (L1 MIP, L1 BCG, L2 INFO) avec inscriptions et notes de S1 (quelques absences, un éliminatoire, quelques EC non saisis), une délibération S1 enregistrée pour la L1 MIP, comptes `etudiant` (activé) ; année 2027-2028 avec ses classes pour tester la promotion.
- [ ] Test idempotence + délibération cohérente avec le moteur. Commit.

### Task 8: Frontend — module Scolarité

**Files:** Create `erp/frontend/src/modules/scolarite/{routes.jsx,api.js,hooks.js}`, `pages/{Etudiants,FicheEtudiant,SaisieNotes,Deliberation,Promotion}.jsx`, `components/*` ; Modify `src/app/modules.js`, `src/app/routesModules.jsx`.
- Menu : Étudiants (liste, recherche, ajout avec inscription, fiche : identité, inscriptions, notes par semestre, boutons attestation/relevé PDF, changement de statut) ; Saisie des notes (classe → EC → grille éditable au clavier, enregistrement groupé, cellules en erreur surlignées avec message) ; Délibération (classe + semestre, tableau UE/moyenne/décision/mention/rang, alerte EC non saisis, « Enregistrer la délibération », export Excel, matrice A3 PDF) ; Promotion & orientation (sélection des admis, choix de filière pour la L1). Entrées filtrées par niveau (`secretariat` / `faculte`).
- [ ] Tests Vitest : grille de saisie (erreur d'une cellule affichée, autres conservées), délibération (alerte EC manquants), droits (secrétariat ne voit pas Saisie/Délibération). FAIL → PASS ; lint ; build. Commit.

### Task 9: Frontend — espace étudiant et activation

**Files:** Create `modules/moi/pages/{MesNotes,MonPlanningEtudiant,MesEnseignants}.jsx`, `src/features/auth/ActivationPage.jsx` ; Modify `modules/moi/MoiShell.jsx` (menu étudiant), `src/app/router.jsx` (`/activation`), `LoginPage.jsx` (lien « Première connexion ? Activer mon compte »).
- [ ] Tests : menu étudiant (Mes notes, Mon planning, Mes enseignants), activation (succès → retour login, échec → message). FAIL → PASS ; lint ; build. Commit.

### Task 10: Bout en bout

**Files:** Create `erp/frontend/e2e/03-scolarite.spec.js` ; Modify `playwright.config.js` (`seed_scolarite`).
- [ ] Scénarios : le secrétariat inscrit un étudiant et télécharge son attestation ; la faculté saisit des notes (une cellule invalide signalée) puis délibère ; l'étudiant voit sa décision ; la page de vérification d'un document s'ouvre, un jeton modifié affiche « introuvable ». Tous les e2e verts. Commit.

## Hors de cette phase

- Frais de scolarité et grille de tarifs : phase 5 (branchée sur `APRES_INSCRIPTION`).
- Vacations (heures effectuées → paie) : phases 4–5.
- Rattrapage (session SR) : saisi comme note SR dans la grille, pas de session distincte.
