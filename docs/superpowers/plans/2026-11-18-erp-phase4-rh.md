# ERP UCCB — Phase 4 : Ressources humaines — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter l'ancien module RH (`uccb_backend/gestion_rh` + `api/api_rh.py`) comme module `rh` de l'ERP : enseignants et personnel sur les fiches uniques du socle, contrats, et vacations calculées à partir des affectations de l'EDT, confirmées par la faculté.

**Architecture:** App Django `erp/backend/rh` sur le socle (`core.Personne`, `core.Enseignant`, `core.Employe`) et l'EDT (`edt.AffectationEC`, `edt.quotas`). La vacation est une confirmation posée sur une `AffectationEC` ; la Finance (phase 5) s'y branchera par des listes de rappels. Frontend `erp/frontend/src/modules/rh` (style EDT) et une entrée « Vacations » dans le menu faculté de la Scolarité.

**Tech Stack:** celle des phases 1–3, sans nouvelle dépendance.

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md` (§6.3, §7.3, tableau des liens automatiques) ; phases précédentes : `docs/superpowers/plans/2026-11-19-erp-phase2-edt.md`, `docs/superpowers/plans/2026-11-19-erp-phase3-scolarite.md`.

## Global Constraints

- Sources à porter (lecture seule) : `/home/it-junior/Gestion-Universit-/uccb_backend/gestion_rh/models.py` et `/home/it-junior/Gestion-Universit-/uccb_backend/api/api_rh.py`.
- `Contrat` (spec §7.3) : sur un enseignant ou un employé ; type permanent / vacataire ; dates ; salaire mensuel ou taux horaire ; RIB, n° de sécurité sociale, diplôme ; contrats expirés détectés.
- **Vacations** (spec §7.3, décision de l'utilisateur) : un vacataire est payé quand il termine son module ou son volume horaire, pas au mois.
  - L'unité est l'`AffectationEC` de l'EDT ; l'ancien `AffectationVacataire` disparaît.
  - Une affectation est **terminée** quand ses heures effectuées (séances confirmées et passées, `edt.quotas`) atteignent ses heures prévues.
  - La faculté (`scolarite_faculte`, périmètre de rattachement, faculté de l'EC) confirme avec les heures retenues : par défaut les heures effectuées, modifiables avec un motif. Elle peut confirmer une affectation non terminée, avec un motif (module arrêté avant la fin).
  - Retirer une confirmation n'est possible que tant que la paie n'est pas payée : liste de vérifications que la Finance remplira en phase 5.
  - L'historique avec motif porte sur les confirmations et leurs retraits, pas sur les modifications courantes des affectations dans l'EDT.
- Droits : `rh_utilisateur` (lecture), `rh_responsable` (écriture) ; confirmation des vacations : `scolarite_faculte`.
- API sous `/api/rh/…` ; journal d'audit sur les créations, les contrats et les confirmations.
- Liens émis pour la Finance (phase 5) : `rh.vacations.APRES_CONFIRMATION` (création de la ligne de paie) et `rh.vacations.VERIFICATIONS_RETRAIT` (refus si payée).

## Décisions soumises à validation

1. **Où se confirment les vacations :** dans le module Scolarité, menu de la faculté, entrée « Vacations » (la spec confie la confirmation à la faculté). Le module RH les affiche en lecture : volumes, état, historique.
2. **Qui a des vacations :** seuls les enseignants qui ont un **contrat de vacataire en cours**. Un permanent est payé au mois (phase 5). Le taux horaire du contrat est **figé dans la vacation** au moment de la confirmation : un avenant ultérieur ne change pas une vacation déjà confirmée.
3. **Statut actif / inactif :** un enseignant ou un employé est actif s'il a un contrat en cours. « Désactiver » termine le contrat à la date choisie ; « Renouveler » crée le contrat suivant. Il n'y a pas de champ de statut séparé. La suspension (blocage de la connexion) reste dans Paramètres.
4. **Données sensibles :** le RIB et le n° de sécurité sociale ne sont visibles en clair que pour `rh_responsable` ; `rh_utilisateur` les voit masqués (4 derniers caractères).
5. **Comptes de connexion :** la RH crée les fiches (enseignant, employé) et leurs contrats ; le compte de connexion reste créé dans Paramètres → Utilisateurs, comme aujourd'hui.

## Review Focus

1. Heures retenues différentes des heures effectuées, ou affectation non terminée, sans motif → 400 ; heures retenues ≤ 0 → 400.
2. Confirmation lancée deux fois pour la même affectation → 400 « déjà confirmée », une seule vacation.
3. Enseignant sans contrat de vacataire en cours (permanent, contrat expiré, aucun contrat) → affectation non confirmable, message explicite ; elle reste visible dans la liste avec ce motif.
4. Deux contrats qui se chevauchent pour la même personne → 400.
5. Utilisateur faculté rattaché à la FST qui confirme ou retire une vacation d'un EC de la FSE → 404.

---

### Task 1: Contrats

**Files:** Create `erp/backend/rh/{__init__,apps,admin,models,contrats}.py`, `rh/tests/{__init__,fabriques,test_contrats}.py` ; Modify `config/settings.py` (INSTALLED_APPS).

**Interfaces:**
- `Contrat(personne FK core.Personne PROTECT related_name='contrats', type 'permanent'|'vacataire', date_debut, date_fin null (durée indéterminée), salaire_mensuel Decimal null, taux_horaire Decimal null, rib, numero_secu, diplome, created_at)`.
- `clean()` : la personne est enseignant ou employé ; vacataire ⇒ enseignant et `taux_horaire > 0` ; permanent ⇒ `salaire_mensuel > 0` ; `date_fin ≥ date_debut` ; pas de chevauchement avec un autre contrat de la même personne (Review Focus 4).
- `rh.contrats.contrat_en_cours(personne, jour=None) -> Contrat | None` ; `Contrat.etat(jour) -> 'a_venir' | 'en_cours' | 'expire'` ; `contrats_a_echeance(jours=30) -> QuerySet`.
- `terminer(contrat, date_fin)` (fin anticipée, refusée si `date_fin < date_debut`).
- [ ] Tests : règles de type, dates, chevauchement (y compris contrat sans fin), contrat en cours à une date, échéance à 30 jours. FAIL → implémenter → PASS (`manage.py test rh core`). Commit.

### Task 2: Vacations

**Files:** Create `rh/vacations.py`, `rh/tests/test_vacations.py` ; Modify `rh/models.py`.

**Interfaces:**
- `Vacation(affectation OneToOne edt.AffectationEC PROTECT related_name='vacation', contrat FK Contrat PROTECT, heures_effectuees Decimal, heures_retenues Decimal, motif, taux_horaire Decimal, montant Decimal, confirmee_le, confirmee_par FK User null)` : montant = heures retenues × taux, figés à la confirmation.
- `HistoriqueVacation(affectation FK edt.AffectationEC CASCADE, action 'confirmation'|'retrait', heures_retenues, montant, motif, par FK User null, le)`.
- `rh.vacations.etat(affectation, totaux=None) -> dict` : `{heures_prevues, heures_effectuees, terminee, contrat (vacataire en cours ou None), confirmable, motif_blocage, vacation}`.
- `confirmer(affectation, *, heures_retenues=None, motif='', par=None) -> Vacation` : refus si déjà confirmée, sans contrat de vacataire en cours, heures ≤ 0, ou motif absent quand les heures diffèrent des heures effectuées ou que l'affectation n'est pas terminée ; écrit l'historique ; appelle `APRES_CONFIRMATION`.
- `retirer(vacation, *, motif, par=None)` : motif obligatoire ; chaque fonction de `VERIFICATIONS_RETRAIT` peut refuser (ValidationError) ; écrit l'historique ; supprime la vacation.
- Une affectation confirmée ne peut plus être supprimée dans l'EDT (PROTECT → 400 expliqué).
- [ ] Tests : terminée / non terminée (séances passées et futures), montant, motif obligatoire, double confirmation, permanent ou contrat expiré refusé, retrait (historique, rappel qui refuse), suppression d'affectation confirmée refusée. FAIL → PASS. Commit.

### Task 3: API RH

**Files:** Create `rh/permissions.py`, `rh/serializers.py`, `rh/views.py`, `rh/urls.py`, `rh/tests/test_api.py` ; Modify `config/urls.py`.

**Interfaces:**
- `GET tableau-de-bord/` : personnel actif par fonction, enseignants actifs (permanents, vacataires), chefs de département, contrats à échéance (30 jours) et expirés, vacations terminées non confirmées.
- `enseignants/` : liste (filtres `q`, `departement`, `type` de contrat, `actif`), fiche (identité, département, grade, contrats, affectations de l'année avec leur état de vacation), création en un appel `{personne: {...}, departement, grade, contrat: {...} facultatif}`, modification (grade, département).
- `employes/` : idem avec `fonction`, `fonction_autre` (obligatoire si « autre »), `lieu_travail`, `faculte_rattachement`.
- `contrats/` : liste (filtres `personne`, `etat`, `echeance=30`), création, modification, `POST contrats/{id}/terminer/ {date_fin}` ; RIB et n° de sécurité sociale masqués pour `rh_utilisateur` (décision 4).
- `GET vacations/?annee=&etat=a_confirmer|en_cours|confirmee&faculte=` : une ligne par affectation d'un enseignant vacataire (`etat()`), lisible par la RH (tout) et par `scolarite_faculte` (sa faculté) ; `GET vacations/historique/`.
- Droits : `rh_utilisateur` lecture, `rh_responsable` écriture ; audit sur création, contrat, fin de contrat.
- [ ] Tests : création enseignant + contrat, employé « autre » sans libellé refusé, chevauchement → 400, masquage pour `rh_utilisateur`, lecture seule, tableau de bord, liste des vacations par état, requêtes bornées (Totaux). FAIL → PASS. Commit.

### Task 4: Confirmation des vacations par la faculté

**Files:** Modify `rh/views.py`, `rh/urls.py` ; Create `rh/tests/test_confirmation.py`.

**Interfaces:**
- `POST vacations/{affectation_id}/confirmer/ {heures_retenues?, motif?}` et `POST vacations/{affectation_id}/retirer/ {motif}` : `scolarite_faculte`, affectation de la faculté de l'EC (rattachement → sinon 404, Review Focus 5) ; audit.
- [ ] Tests : confirmation par défaut, avec heures modifiées et motif, sans motif (400), double confirmation (400), contrat absent (400 explicite), retrait, périmètre (404), RH et secrétariat refusés (403). FAIL → PASS. Commit.

### Task 5: Données de démonstration

**Files:** Create `rh/management/commands/seed_rh.py`, `rh/tests/test_seed.py` ; Modify `README.md`, `erp/frontend/playwright.config.js` (`seed_rh`).
- `seed_rh` (DEBUG seulement, idempotent, après `seed_edt`) : contrats de tous les enseignants (2 permanents, les autres vacataires dont `enseignant` et `referent`), ~10 employés dont 2 chauffeurs avec contrats, un contrat qui expire dans 15 jours, un contrat expiré ; une affectation terminée à confirmer, une vacation confirmée ; comptes `rh_utilisateur`, `rh_responsable` déjà créés par le socle.
- [ ] Test idempotence et cohérence (une vacation à confirmer, une confirmée). Commit.

### Task 6: Frontend — module RH

**Files:** Create `erp/frontend/src/modules/rh/{routes.jsx,api.js,hooks.js}`, `pages/{TableauDeBord,Enseignants,FicheEnseignant,Personnel,FicheEmploye,Contrats,Vacations}.jsx`, `components/*` ; Modify `src/app/modules.js`, `src/app/routesModules.jsx`.
- Menu : Tableau de bord (indicateurs, contrats à échéance) ; Enseignants (liste, ajout avec contrat, fiche : contrats, affectations et état de vacation, désactiver / renouveler) ; Personnel (idem, fonction) ; Contrats (échéances et expirés) ; Vacations (lecture : volumes, état, historique). Boutons d'écriture pour `rh_responsable` seulement.
- [ ] Tests Vitest : ajout d'un enseignant avec contrat (erreurs serveur affichées), lecture seule pour `rh_utilisateur`, tableau des vacations par état. FAIL → PASS ; lint ; build. Commit.

### Task 7: Frontend — vacations dans la Scolarité

**Files:** Create `erp/frontend/src/modules/scolarite/pages/Vacations.jsx` ; Modify `modules/scolarite/{api.js,routes.jsx}`, `src/app/modules.js` (entrée « Vacations », niveau `faculte`).
- Onglets « À confirmer », « En cours », « Confirmées » ; dialogue de confirmation (heures retenues pré-remplies, motif exigé si elles changent ou si l'affectation n'est pas terminée) ; retrait avec motif ; motif de blocage affiché (pas de contrat de vacataire).
- [ ] Tests Vitest : motif exigé quand les heures changent, retrait. FAIL → PASS ; lint ; build. Commit.

### Task 8: Bout en bout

**Files:** Create `erp/frontend/e2e/04-rh.spec.js`.
- [ ] Scénarios : la RH ajoute un enseignant vacataire avec son contrat ; `rh_utilisateur` ne voit pas le RIB en clair ; la faculté confirme une vacation terminée, la RH la voit confirmée dans l'historique ; tous les e2e verts. Commit.

## Hors de cette phase

- Lignes de paie (salaires mensuels et vacations confirmées), paiements : phase 5, branchés sur `APRES_CONFIRMATION` et `VERIFICATIONS_RETRAIT`.
- Chauffeurs en Logistique : phase 6 (employé de fonction « chauffeur » avec un contrat en cours).
