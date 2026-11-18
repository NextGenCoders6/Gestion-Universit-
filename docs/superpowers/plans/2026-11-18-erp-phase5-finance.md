# ERP UCCB — Phase 5 : Finance — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter l'ancien module Finance (`uccb_backend/gestion_finance` + `api/api_finance.py`) comme module `finance` de l'ERP. Il couvre :
- les frais de scolarité, calculés à partir d'une grille de tarifs par année et par niveau, et payables selon un **échéancier mensuel** : chaque mois écoulé a sa date limite, jusqu'à solder le montant de l'année ;
- les paiements des étudiants, avec un reçu ;
- la paie : salaires mensuels des permanents et vacations confirmées ;
- un journal des opérations alimenté automatiquement ;
- un tableau de bord avec la trésorerie et les retards de paiement ;
- la situation des frais dans l'espace étudiant.

**Architecture:** App Django `erp/backend/finance` branchée sur les rappels déjà posés : `scolarite.inscriptions.APRES_INSCRIPTION` (dossier de frais), `rh.vacations.APRES_CONFIRMATION` et `VERIFICATIONS_RETRAIT` (ligne de paie de vacation). Chaque paiement écrit sa ligne au journal dans la même transaction. Reçus PDF via `core/documents.py`. Frontend `erp/frontend/src/modules/finance` (style EDT), page « Tarifs » dans Paramètres, page « Mes frais » dans l'espace étudiant.

**Tech Stack:** celle des phases 1–4, sans nouvelle dépendance (le graphique de trésorerie est dessiné en SVG).

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md` (§7.4, §7.6 grille de tarifs, §7.7 situation des frais, tableau des liens automatiques) ; phases précédentes : `docs/superpowers/plans/2026-11-19-erp-phase3-scolarite.md`, `docs/superpowers/plans/2026-11-18-erp-phase4-rh.md`.

## Global Constraints

- Sources à porter (lecture seule) : `/home/it-junior/Gestion-Universit-/uccb_backend/gestion_finance/` (models.py, views.py, templates `receipt_*.html`) et `/home/it-junior/Gestion-Universit-/uccb_backend/api/api_finance.py`.
- **Grille de tarifs** (décision de l'utilisateur) : `Tarif` = année académique + niveau (L1, L2, L3, M1, M2) + montant, géré dans Paramètres.
- **Modalité de paiement** (demande de l'utilisateur) : le montant de l'année se paie par mensualités jusqu'à être soldé. Chaque mois écoulé a une date limite de paiement : par exemple, la mensualité d'octobre est due le 5 novembre. La modalité est définie avec le tarif (nombre de mensualités, premier mois couvert, jour d'échéance), et chaque dossier reçoit son échéancier.
- **Dossier de frais** : un par inscription, créé avec elle. Le montant vient du tarif ; sans tarif, le dossier est créé à 0 et signalé sur le tableau de bord. Le montant est modifiable par `finance_responsable`, avec une trace au journal d'audit. Statut : payé, partiel, non payé.
- **Modes de paiement** : espèces, Mobile Money, virement, chèque. Un paiement ne dépasse jamais le reste dû.
- **Paie** : montant dû, montant payé, statut (en attente / partiel / payé), et deux origines :
  - un salaire par contrat permanent et par mois `AAAA-MM`, au montant du salaire mensuel ;
  - une vacation par vacation confirmée, au montant figé par la confirmation (phase 4).
- **Journal** (`Operation`, reprise de `Transaction`) : libellé, montant (+ recette / − dépense), date, reçu PDF. Chaque paiement d'étudiant et chaque paiement de paie y écrit sa ligne automatiquement.
- **Droits** : `finance_utilisateur` et `finance_responsable` (décision 6) ; grille de tarifs : `parametres_responsable` en écriture.
- API sous `/api/finance/…` ; journal d'audit sur les paiements, les ajustements, les annulations et la génération de la paie.

## Décisions soumises à validation

1. **Dépenses de transport : en phase 6.** Elles sont rattachées à un bus, et les bus arrivent avec la Logistique. En phase 5, le journal accepte des opérations manuelles (recette ou dépense libre) saisies par `finance_responsable`, comme l'ancien « ajouter une transaction ».
2. **Journal sans suppression.** Une erreur se corrige par une annulation avec motif : la ligne de paiement est marquée annulée et le journal reçoit une contre-écriture. Rien n'est effacé ; l'ancien module supprimait les lignes.
3. **Paie des salaires générée mois par mois.** La Finance clique sur « Générer la paie de novembre 2026 ». Cela crée une ligne par contrat permanent en cours au moins un jour du mois, au salaire mensuel entier. Relancer la génération ne crée pas de doublon. Le montant d'une ligne reste modifiable tant qu'elle n'a reçu aucun paiement, avec une trace au journal d'audit.
4. **Frais en retard et résultats :** l'ancienne scolarité masquait à l'étudiant les résultats du semestre en cours quand il n'était « pas en règle ». C'était une case cochée à la main, vraie par défaut. Je propose de **reprendre la règle avec un critère automatique** : dans son espace, l'étudiant ne voit ni moyenne ni décision des semestres de l'année tant qu'il a une **mensualité échue non payée**. Il voit ses notes saisies et la situation de ses frais. Un étudiant à jour de ses mensualités voit tout, même si l'année n'est pas soldée. Le secrétariat et la faculté voient tout, comme avant. L'autre possibilité est de ne rien bloquer.
5. **Tarif créé ou modifié après les inscriptions :** les dossiers de l'année et du niveau sont recalculés, sauf ceux dont la Finance a ajusté le montant à la main. Un dossier qui a déjà reçu plus que le nouveau montant est marqué payé, et le trop-perçu est signalé sur le tableau de bord.
6. **Droits :**
   - `finance_utilisateur` voit tout et encaisse les paiements des étudiants ;
   - `finance_responsable` fait en plus la paie (génération, paiements), les ajustements de montant, les annulations et les opérations manuelles.
7. **Échéancier mensuel (ta demande) :**
   - il est défini avec le tarif dans Paramètres : nombre de mensualités (par défaut 10, d'octobre à juillet) et jour d'échéance (par défaut le 5 du mois qui suit le mois couvert) ;
   - les mensualités sont égales ; la dernière absorbe l'arrondi ;
   - un paiement couvre les mensualités dans l'ordre, de la plus ancienne à la plus récente ; payer d'avance est possible ;
   - un dossier est « en retard » dès qu'une mensualité échue n'est pas entièrement payée ;
   - `finance_responsable` peut adapter l'échéancier d'un dossier (étudiant inscrit tard, accord particulier), à condition que la somme des mensualités reste égale au montant dû.

## Review Focus

1. Paiement supérieur au reste dû, nul, négatif ou non numérique → 400 ; ni paiement ni ligne de journal n'est écrit.
2. Deux paiements simultanés sur le même dossier ou la même ligne de paie → jamais de dépassement (verrou sur la ligne).
3. Paie du même mois générée deux fois → aucune ligne en double.
4. Retrait d'une vacation dont la paie a reçu un paiement → refusé avec un message ; sans paiement → la ligne de paie disparaît.
5. Inscription sans tarif pour son niveau → dossier à 0, signalé ; tarif créé ensuite → dossier recalculé avec son échéancier (décision 5).
6. Montant non divisible par le nombre de mensualités (1 500 000 / 7) → la somme des mensualités vaut exactement le montant. Un paiement qui couvre une mensualité et demie laisse la suivante partielle, et elle n'est pas en retard avant sa date.

---

### Task 1: Tarifs et dossiers de frais

**Files:** Create `erp/backend/finance/{__init__,apps,admin,models,frais}.py`, `finance/tests/{__init__,fabriques,test_frais}.py` ; Modify `config/settings.py` (INSTALLED_APPS).

**Interfaces:**
- `Tarif(annee FK AnneeAcademique PROTECT, parcours FK Parcours PROTECT (Licence/Master), montant Decimal ≥ 0, nombre_mensualites 1–12 (défaut 10), premier_mois 'AAAA-MM' (défaut : octobre de l'année), jour_echeance 1–28 (défaut 5))` ; unique (annee, parcours). La mensualité du mois M est due le `jour_echeance` du mois M+1.
- `FraisScolarite(inscription OneToOne scolarite.Inscription PROTECT related_name='frais', montant_du, montant_paye, montant_ajuste bool, echeancier_adapte bool, created_at)` ; `statut` calculé (`paye` | `partiel` | `non_paye`) ; `reste`, `trop_percu`.
- `EcheanceFrais(dossier FK related_name='echeances', numero, mois 'AAAA-MM', date_limite, montant)`.
- `finance.frais.echeancier(montant, tarif) -> [(mois, date_limite, montant)]` : mensualités égales, la dernière prend le reste de l'arrondi.
- `etat_echeances(dossier, jour=None) -> [{numero, mois, date_limite, montant, paye, etat 'payee'|'partielle'|'en_retard'|'a_venir'}]` : le payé couvre les échéances dans l'ordre ; `en_retard(dossier, jour)`, `montant_en_retard(dossier, jour)`, `prochaine_echeance(dossier, jour)`.
- `adapter_echeancier(dossier, [(mois, date_limite, montant)], par)` : la somme doit égaler le montant dû et les dates être croissantes.
- `finance.frais.creer_dossier(inscription) -> FraisScolarite` (branché sur `APRES_INSCRIPTION` dans `FinanceConfig.ready`) ; `appliquer_tarif(tarif)` (décision 5, appelé à l'enregistrement d'un tarif) ; `ajuster(dossier, montant, par)` ; `creer_dossiers_manquants() -> int` (inscriptions antérieures à l'installation).
- [ ] Tests : dossier créé avec l'inscription au tarif du niveau et son échéancier (pour 1 500 000 : 10 mensualités de 150 000, du 05/11 au 05/08) ; arrondi (1 500 000 / 7) ; dossier à 0 sans tarif ; recalcul à la création du tarif sauf dossier ajusté (échéancier régénéré sauf s'il a été adapté) ; trop-perçu ; ajustement ; état des échéances (payée, partielle, en retard, à venir) selon le payé et la date ; échéancier adapté (somme fausse refusée) ; rattrapage idempotent. FAIL → implémenter → PASS (`manage.py test finance scolarite`). Commit.

### Task 2: Paiements des étudiants et journal

**Files:** Create `finance/paiements.py`, `finance/tests/test_paiements.py` ; Modify `finance/models.py`.

**Interfaces:**
- `Operation(numero unique « OP-AAAA-000001 », date, libelle, montant signé, categorie 'frais'|'salaire'|'vacation'|'manuelle'|'annulation', annule FK self null, created_at, par FK User)` — jamais supprimée.
- `PaiementEtudiant(dossier FK, montant > 0, mode, date, reference, operation OneToOne, annule bool, motif_annulation, par)`.
- `paiements.encaisser(dossier, montant, mode, *, date=None, reference='', par=None) -> PaiementEtudiant` : verrou sur le dossier, refus au-delà du reste dû (Review Focus 1–2), mise à jour du payé, ligne de journal.
- `paiements.annuler_paiement(paiement, motif, par) -> Operation` (décision 2) : contre-écriture, payé diminué.
- `operation_manuelle(libelle, montant, date, par)` (décision 1).
- [ ] Tests : paiement partiel puis solde, dépassement refusé sans écriture, montant ≤ 0, numéros consécutifs, annulation (contre-écriture, statut recalculé, double annulation refusée), opération manuelle. Commit.

### Task 3: Paie

**Files:** Create `finance/paie.py`, `finance/tests/test_paie.py` ; Modify `finance/models.py`, `finance/apps.py`.

**Interfaces:**
- `Paie(origine 'salaire'|'vacation', personne FK Personne PROTECT, contrat FK rh.Contrat PROTECT, mois 'AAAA-MM' (salaire), vacation OneToOne rh.Vacation CASCADE null, montant_du, montant_paye, montant_ajuste bool, created_at)` ; unique (contrat, mois) pour les salaires ; `statut` calculé (`en_attente` | `partiel` | `paye`).
- `PaiementPaie(paie FK, montant > 0, mode, date, reference, operation OneToOne, annule, motif_annulation, par)`.
- `paie.generer_salaires(mois, par) -> (créées, existantes)` (décision 3) ; `creer_ligne_vacation(vacation)` (rappel `APRES_CONFIRMATION`) ; `refuser_retrait_si_payee(vacation)` (rappel `VERIFICATIONS_RETRAIT`) ; `payer(paie, montant, mode, ...)` ; `annuler_paiement_paie(...)` ; `ajuster(paie, montant, par)` (refusé après un paiement).
- [ ] Tests : génération idempotente, contrat commencé ou fini en cours de mois, vacataire exclu des salaires, ligne de vacation à la confirmation, retrait refusé si payée, ligne supprimée sinon, paiements partiels et verrou, ajustement refusé après paiement. Commit.

### Task 4: Reçus PDF

**Files:** Create `finance/recus.py`, templates `finance/templates/finance/{recu_etudiant,recu_paie,recu_operation}.html`, `finance/tests/test_recus.py`.
- Reçu d'un paiement d'étudiant : numéro d'opération, étudiant, matricule, classe, montant, mode, total dû, payé, reste. Reçu d'un paiement de paie. Reçu d'une opération manuelle. Un reçu d'un paiement annulé porte la mention « ANNULÉ ».
- [ ] Tests : PDF non vide (`%PDF`), mention d'annulation. Commit.

### Task 5: API Finance et espace étudiant

**Files:** Create `finance/permissions.py`, `finance/serializers.py`, `finance/views.py`, `finance/urls.py`, `finance/tests/{test_api,test_espace}.py` ; Modify `config/urls.py`, `scolarite/views_etudiant.py` (décision 4).

**Interfaces:**
- `GET tableau-de-bord/?annee=` :
  - recettes, dépenses et solde ;
  - frais attendus et encaissés, taux de recouvrement ;
  - dossiers en retard et montant échu non payé ;
  - dossiers à 0 sans tarif, trop-perçus ;
  - paie en attente (montant) ;
  - trésorerie des 12 derniers mois (recettes et dépenses par mois).
- `frais/` : liste (filtres `annee`, `classe`, `statut`, `retard=true`, `q`), fiche avec ses paiements et son échéancier (état de chaque mensualité) ; `PUT frais/{id}/echeancier/` (responsable) ; `POST frais/{id}/paiements/` ; `POST frais/{id}/ajuster/ {montant}` (responsable) ; `POST paiements/{id}/annuler/ {motif}` (responsable) ; `GET paiements/{id}/recu.pdf`.
- `paie/` : liste (filtres `origine`, `mois`, `statut`, `role` enseignant|employe, `q`) ; `POST paie/generer/ {mois}` ; `POST paie/{id}/paiements/` ; `POST paie/{id}/ajuster/` ; `POST paiements-paie/{id}/annuler/` ; `GET paiements-paie/{id}/recu.pdf` (tout en responsable sauf la lecture).
- `operations/` : journal (filtres `debut`, `fin`, `categorie`, `q`) ; `POST operations/` (manuelle, responsable) ; `GET operations/{id}/recu.pdf`.
- `tarifs/` : lecture pour la Finance et Paramètres, écriture `parametres_responsable` ; l'enregistrement appelle `appliquer_tarif`.
- `GET /api/scolarite/moi/frais/` : dossiers de l'étudiant, échéancier (prochaine échéance, retards), paiements non annulés, reçus téléchargeables. `moi/notes/` applique la décision 4.
- [ ] Tests : droits (utilisateur encaisse mais ne paie pas la paie ni n'ajuste), paiement via l'API (400 au-delà du reste), tableau de bord (taux, sans tarif, trésorerie), génération de la paie, journal filtré, tarifs réservés à Paramètres, espace étudiant (frais et échéancier ; résultats masqués s'il reste une mensualité échue non payée, visibles si l'étudiant est à jour). Commit.

### Task 6: Données de démonstration

**Files:** Create `finance/management/commands/seed_finance.py`, `finance/tests/test_seed.py` ; Modify `README.md`, `erp/frontend/playwright.config.js` (`seed_finance`).
- `seed_finance` (DEBUG seulement, idempotent, après `seed_rh`) :
  - tarifs 2026-2027 pour L1, L2 et L3 : 1 500 000 FCFA en 10 mensualités (octobre à juillet, échéance le 5 du mois suivant) ; pas de M1, pour montrer le cas « sans tarif » ;
  - dossiers de toutes les inscriptions, avec des paiements variés : soldés, à jour de leurs mensualités, en retard, et sans aucun paiement ;
  - le compte `etudiant` à jour de ses mensualités ;
  - paie d'octobre 2026 générée et en partie payée ;
  - la vacation confirmée de la phase 4 payée ;
  - deux opérations manuelles.
- [ ] Test idempotence et cohérence (journal = somme des paiements). Commit.

### Task 7: Frontend — module Finance et tarifs

**Files:** Create `erp/frontend/src/modules/finance/{routes.jsx,api.js,hooks.js}`, `pages/{TableauDeBord,Frais,DossierFrais,PaieEnseignants,PaiePersonnel,Journal}.jsx`, `components/*` ; Create `modules/parametres/pages/Tarifs.jsx` ; Modify `src/app/modules.js`, `src/app/routesModules.jsx`, `modules/parametres/routes.jsx`.
- **Tableau de bord** : indicateurs, graphique de trésorerie en SVG, alertes (dossiers en retard, sans tarif, trop-perçus).
- **Frais étudiants** : liste filtrable, dont un filtre « en retard » ; dossier avec son échéancier (état de chaque mensualité, adaptation), ses paiements, l'encaissement, le reçu, l'ajustement et l'annulation.
- **Paie enseignants / Paie personnel** : génération du mois, paiements, reçus, ajustement.
- **Journal** : filtres, opération manuelle, reçus.
- **Tarifs** (Paramètres) : grille année × niveau avec la modalité (mensualités, premier mois, jour d'échéance) et un aperçu de l'échéancier.
- [ ] Tests Vitest :
  - paiement au-delà du reste : message du serveur affiché ;
  - lecture seule de la paie pour `finance_utilisateur` ;
  - génération de la paie du mois ;
  - grille de tarifs avec aperçu de l'échéancier ;
  - échéancier d'un dossier, avec la mensualité en retard signalée.

  Puis FAIL → PASS ; lint ; build. Commit.

### Task 8: Frontend — espace étudiant

**Files:** Create `modules/moi/pages/MesFrais.jsx` ; Modify `modules/moi/MoiShell.jsx`, `modules/moi/api.js`, `modules/moi/pages/MesNotes.jsx` (message quand les résultats sont masqués, décision 4).
- [ ] Tests : menu « Mes frais », échéancier (prochaine échéance, retard), reçus, message de résultats masqués. FAIL → PASS ; lint ; build. Commit.

### Task 9: Bout en bout

**Files:** Create `erp/frontend/e2e/05-finance.spec.js`.
- [ ] Scénarios, puis tous les e2e verts. Commit.
  - le responsable Paramètres crée le tarif M1, et le dossier de M1 est recalculé ;
  - `finance_utilisateur` encaisse un paiement partiel, télécharge le reçu, et le journal montre la ligne ;
  - un paiement au-delà du reste est refusé ;
  - `finance_responsable` génère la paie du mois et paie la vacation confirmée ;
  - l'étudiant voit son échéancier et sa prochaine échéance.

## Hors de cette phase

- Dépenses de transport et onglet coûts de la Logistique : phase 6 (décision 1).
- Paiement en ligne : non-objectif de la spec.
