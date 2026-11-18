# ERP UCCB — Phase 6 : Logistique, données de démonstration et passe finale — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dernière phase de l'ERP :
- porter l'ancien module Logistique (`uccb_backend/gestion_logistique`) : bus, trajets, affectations des chauffeurs ;
- ajouter les dépenses de transport, reportées de la phase 5, au journal de la Finance ;
- livrer `seed_demo`, une commande unique qui remplit tout l'ERP ;
- faire une passe finale sur les défauts reportés des phases précédentes qui se voient ou touchent la sécurité.

**Architecture:** App Django `erp/backend/logistique` sur le socle (`core.Employe` de fonction « chauffeur ») et les RH (`rh.contrats.contrat_en_cours`). `finance.DepenseTransport` référence un bus et écrit sa ligne au journal comme les autres paiements. Frontend `erp/frontend/src/modules/logistique` (style EDT), page « Transports » dans la Finance.

**Tech Stack:** celle des phases 1–5, sans nouvelle dépendance.

**Spec:** `docs/superpowers/specs/2026-11-18-erp-uccb-design.md` (§7.4 `DepenseTransport`, §7.5 Logistique, §9 données de démonstration, §10 phase 6) ; phases précédentes : `docs/superpowers/plans/2026-11-18-erp-phase5-finance.md` et les listes « Deferred minors » des PR #2 à #5.

## Global Constraints

- Source à porter (lecture seule) : `/home/it-junior/Gestion-Universit-/uccb_backend/gestion_logistique/` (models.py, views.py) et `api/api_logistique.py`.
- `Bus` (numéro, plaque, capacité, statut actif / maintenance / hors service), `Trajet` (nom, départ, destination, heures), `AffectationTransport` (bus + chauffeur + trajet + dates). Un bus n'a **qu'une seule affectation active** à la fois (spec §7.5).
- Le chauffeur est un `Employe` de fonction « chauffeur » avec un **contrat en cours** (spec §7.5).
- `DepenseTransport` (spec §7.4) : bus, type (carburant, entretien, réparation), montant, description, date. Chaque dépense écrit sa ligne au journal (montant négatif).
- Écrans Logistique : bus, trajets, affectations, et un onglet « Coûts » qui **lit** les dépenses de transport de la Finance (spec §7.5).
- Droits : `logistique_utilisateur` en lecture, `logistique_responsable` en écriture ; dépenses de transport : décision 1.
- `seed_demo` (spec §9) : une année active, 2 facultés, ~10 enseignants permanents et vacataires, ~10 employés dont 2 chauffeurs, ~60 étudiants inscrits avec des notes, des séances, des paiements, 3 bus, et un compte par profil type. Les mots de passe de démonstration figurent dans `erp/backend/README.md`.

## Décisions soumises à validation

1. **Dépenses de transport saisies par la Finance.** `finance_responsable` les saisit dans une page « Transports » de la Finance, comme le prévoit la spec. Elles passent au journal et s'annulent par une contre-écriture, comme les autres paiements. La Logistique les voit dans son onglet « Coûts », en lecture seule.
2. **Un chauffeur ne conduit qu'un bus à la fois.** La spec impose déjà une seule affectation active par bus ; j'ajoute la même règle pour le chauffeur. Seul un employé « chauffeur » qui a un contrat en cours à la date de début peut être affecté.
3. **Bus mis en maintenance ou hors service :** son affectation en cours se termine automatiquement ce jour-là, avec une trace au journal d'audit. Un bus qui n'est pas actif ne peut pas recevoir d'affectation.
4. **Contrat d'un chauffeur terminé :** l'affectation n'est pas coupée automatiquement. Elle est signalée sur le tableau de bord de la Logistique (« chauffeur sans contrat en cours »), pour que la Logistique la remplace.
5. **`seed_demo` enchaîne les seeds de chaque module** (socle, emploi du temps, scolarité, RH, finance, logistique). Il est idempotent et refusé hors développement. Il affiche à la fin la liste des comptes et le mot de passe. Les seeds de chaque module restent disponibles.
6. **Passe finale** — je corrige les défauts reportés qui se voient pour l'utilisateur ou qui touchent la sécurité, chacun avec un test :
   - Scolarité :
     - une promotion lancée sur plusieurs étudiants n'échoue plus en bloc : chaque étudiant refusé est listé avec son motif ;
     - l'API refuse de promouvoir un étudiant diplômé ou qui a abandonné ;
     - un PDF qui échoue renvoie un message clair et ne laisse pas de document vérifiable ;
     - plus aucune écriture n'est possible sur une année archivée (statut, promotion, date d'inscription) ;
     - `/verifier/<jeton>/` avec une barre finale affiche la page « document introuvable » ;
     - un avertissement apparaît au démarrage si `BASE_URL` pointe vers localhost hors développement.
   - RH :
     - le tableau de bord ne compte plus les personnes déjà renouvelées ;
     - un contrat à venir peut être annulé depuis l'écran ;
     - un contrat qui a des vacations confirmées ne peut plus changer de personne ni de type ;
     - les retraits de vacation sont verrouillés.
   - Finance :
     - l'étudiant ne voit plus l'identifiant du caissier ;
     - une date de paiement ne peut pas précéder l'année académique précédente ;
     - les messages précis du serveur s'affichent dans les deux formulaires concernés ;
     - le bouton de reçu de l'étudiant affiche une erreur au lieu d'échouer sans rien dire ;
     - le mois par défaut est calculé en heure locale ;
     - un tarif garde ses centimes ;
     - le retrait d'une vacation verrouille sa ligne de paie.
   - Emploi du temps : une contrainte d'unicité en base empêche deux affectations identiques.

   Les autres mineurs reportés restent notés pour plus tard : requêtes en trop, pagination côté serveur des frais, historique de vacation effacé avec l'affectation.

## Review Focus

1. Deuxième affectation active pour le même bus ou le même chauffeur → 400 avec un message clair. Après la fin de la première, la nouvelle est acceptée.
2. Affectation avec un employé qui n'est pas chauffeur, ou chauffeur sans contrat en cours à la date de début → 400.
3. Bus passé en maintenance avec une affectation en cours → l'affectation se termine ce jour-là. Bus en maintenance proposé dans une nouvelle affectation → 400.
4. Dépense de transport nulle, négative ou non numérique → 400, rien n'est écrit au journal ; une dépense annulée → contre-écriture, et l'onglet « Coûts » n'en tient plus compte.
5. `seed_demo` lancé deux fois → aucun doublon ; lancé sur une base vide → tout l'ERP est rempli et les e2e passent dessus.

---

### Task 1: Bus, trajets et affectations

**Files:** Create `erp/backend/logistique/{__init__,apps,admin,models,affectations}.py`, `logistique/tests/{__init__,fabriques,test_modeles}.py` ; Modify `config/settings.py`.

**Interfaces:**
- `Bus(numero unique, plaque unique, capacite ≥ 1, statut 'actif'|'maintenance'|'hors_service')` ; `Trajet(nom, depart, destination, heure_depart, heure_arrivee > heure_depart)` ; `AffectationTransport(bus FK PROTECT, chauffeur FK core.Employe PROTECT, trajet FK PROTECT, date_debut, date_fin null)`.
- `est_active(jour)` : `date_debut ≤ jour` et (`date_fin` vide ou `≥ jour`).
- `clean()` :
  - chauffeur de fonction « chauffeur » avec un contrat en cours à `date_debut` ;
  - bus actif à la création ;
  - pas d'autre affectation qui chevauche la période, ni pour le bus ni pour le chauffeur (Review Focus 1–2) ;
  - `date_fin ≥ date_debut`.
- `logistique.affectations.terminer(affectation, jour=None)` ; `changer_statut(bus, statut, par)` termine l'affectation en cours si le bus n'est plus actif (décision 3) ; `chauffeurs_disponibles(jour)` ; `alertes(jour)` (chauffeurs sans contrat en cours, décision 4).
- [ ] Tests : unicité (bus, plaque), heures du trajet, règles d'affectation (non-chauffeur, contrat absent ou fini, bus en maintenance, chevauchements bus et chauffeur, contigu autorisé), fin d'affectation, statut qui termine, chauffeurs disponibles, alertes. FAIL → implémenter → PASS (`manage.py test logistique`). Commit.

### Task 2: Dépenses de transport

**Files:** Create `finance/transports.py`, `finance/tests/test_transports.py` ; Modify `finance/models.py` (catégorie d'opération `transport`).

**Interfaces:**
- `DepenseTransport(bus FK logistique.Bus PROTECT related_name='depenses', type 'carburant'|'entretien'|'reparation', montant > 0, description, date, operation OneToOne, annule, motif_annulation, par)`.
- `transports.enregistrer(bus, type, montant, *, date=None, description='', par=None)` : ligne de journal négative « Transport — carburant — Bus 01 (…) » ; `annuler_depense(depense, motif, par)` : contre-écriture.
- `couts(bus=None, debut=None, fin=None) -> {total, par_type, par_bus, par_mois}` sur les dépenses non annulées.
- [ ] Tests : écriture au journal, montants invalides sans écriture, annulation, coûts (annulées exclues), reçu PDF d'une dépense. Commit.

### Task 3: API Logistique et dépenses

**Files:** Create `logistique/permissions.py`, `logistique/serializers.py`, `logistique/views.py`, `logistique/urls.py`, `logistique/tests/test_api.py` ; Modify `config/urls.py`, `finance/views.py`, `finance/urls.py`, `finance/tests/test_api.py`.

**Interfaces:**
- `GET /api/logistique/tableau-de-bord/` : bus par statut, affectations actives, chauffeurs disponibles, alertes (décision 4), coûts du mois et de l'année.
- `bus/` (CRUD, `POST bus/{id}/statut/ {statut}`), `trajets/` (CRUD), `affectations/` (liste avec `actives=true`, création, `POST affectations/{id}/terminer/ {date_fin?}`), `GET chauffeurs/?date=` (disponibles), `GET couts/?bus=&debut=&fin=` (lecture des dépenses de la Finance).
- Finance : `transports/` (liste, création par `finance_responsable`), `POST transports/{id}/annuler/`, `GET transports/{id}/recu.pdf`.
- Droits : `logistique_utilisateur` lecture, `logistique_responsable` écriture ; journal d'audit sur bus, statut, affectations.
- [ ] Tests : droits, création d'affectation via l'API (400 explicites), statut qui termine, chauffeurs disponibles, coûts lus par la Logistique, dépenses réservées au responsable Finance, suppression d'un bus utilisé refusée (400). Commit.

### Task 4: Données de démonstration complètes

**Files:** Create `logistique/management/commands/seed_logistique.py`, `core/management/commands/seed_demo.py`, `logistique/tests/test_seed.py`, `core/tests/test_seed_demo.py` ; Modify `README.md`, `erp/frontend/playwright.config.js` (`seed_demo` au lieu de la chaîne de seeds).
- `seed_logistique` (DEBUG, idempotent) :
  - 3 bus : 2 actifs et 1 en maintenance ;
  - 3 trajets ;
  - 2 affectations actives avec les 2 chauffeurs de `seed_rh` ;
  - des dépenses de transport (carburant, entretien) d'octobre et novembre 2026.
- `seed_demo` :
  - enchaîne `seed_socle`, `seed_edt`, `seed_scolarite`, `seed_rh`, `seed_finance` et `seed_logistique` ;
  - affiche les comptes de démonstration et leur mot de passe ;
  - accepte `--reset`, qui est passé à `seed_socle`.
- `README.md` : démarrage rapide (`seed_demo`), un tableau de tous les comptes par profil, la commande de tests de tous les modules.
- [ ] Tests : `seed_demo` lancé deux fois sans doublon (comptes, bus, affectations, dépenses) ; contenu attendu (spec §9) : au moins 55 étudiants, 2 chauffeurs actifs, 3 bus, un compte par module ; refus hors DEBUG. Commit.

### Task 5: Frontend — Logistique et transports

**Files:** Create `erp/frontend/src/modules/logistique/{routes.jsx,api.js,hooks.js}`, `pages/{TableauDeBord,Bus,Trajets,Affectations,Couts}.jsx` ; Create `modules/finance/pages/Transports.jsx` ; Modify `src/app/modules.js`, `src/app/routesModules.jsx`, `modules/finance/routes.jsx`.
- **Tableau de bord** : bus par statut, affectations, alertes.
- **Bus** : liste, ajout, modification, changement de statut avec un avertissement si une affectation est en cours.
- **Trajets.**
- **Affectations** : en cours et passées ; nouvelle affectation proposant seulement les bus actifs et les chauffeurs disponibles ; fin d'affectation.
- **Coûts** : total, répartition par bus, par type et par mois, en lecture seule.
- **Finance → Transports** : saisie, annulation, reçu.
- [ ] Tests Vitest :
  - lecture seule pour `logistique_utilisateur` ;
  - nouvelle affectation : message du serveur affiché ;
  - avertissement au passage en maintenance ;
  - saisie d'une dépense de transport (Finance).

  Puis FAIL → PASS ; lint ; build. Commit.

### Task 6: Passe finale

**Files:** selon chaque correctif (décision 6) ; Create `core/tests/test_passe_finale.py` et les tests frontend associés.
- Un test qui échoue d'abord pour chaque point de la décision 6. Les correctifs sont regroupés par module, avec un commit par module.
- [ ] Tous les tests backend et Vitest au vert ; lint ; build.

### Task 7: Bout en bout et vérification finale

**Files:** Create `erp/frontend/e2e/06-logistique.spec.js`.
- [ ] Scénarios :
  - `logistique_responsable` ajoute un bus, affecte un chauffeur disponible, puis voit le refus d'une seconde affectation du même chauffeur ;
  - passage d'un bus en maintenance : son affectation se termine ;
  - `finance_responsable` saisit une dépense de carburant, et l'onglet « Coûts » de la Logistique l'affiche.
- [ ] Tous les e2e verts sur `seed_demo`. Commit.
- [ ] Vérification de l'application servie par Django : le build Vite (`frontend_dist`) s'ouvre sur `/`, une page profonde se recharge sans erreur, et `/verifier/<jeton>` sort de la SPA.

## Hors de cette phase

- Mineurs reportés non retenus dans la décision 6 (listés dans la PR).
- Paiement en ligne et application mobile : non-objectifs de la spec.
