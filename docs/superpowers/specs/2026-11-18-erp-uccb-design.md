# ERP UCCB — Document de conception

Date : 2026-11-18
Statut : validé par l'utilisateur le 2026-11-18

## 1. Intention

Le dépôt contient aujourd'hui six applications qui se sont développées côte à côte
dans `uccb_backend/` et `uccb_frontend/` : scolarité/notes (`gestion_eleves`),
emploi du temps (`EDT_app`), ressources humaines (`gestion_rh`), finance
(`gestion_finance`), logistique (`gestion_logistique`) et un espace étudiant.
Chacune a sa connexion, ses rôles et souvent ses propres copies des mêmes données
(`Etudiant` ×2, `Enseignant` ×3, `Faculte` ×2, `AnneeAcademique` ×2).

L'objectif est d'en faire **un vrai ERP sur le modèle d'Odoo** : les services
restent séparés (chaque module a son menu, ses écrans, ses droits), mais le système
est centralisé (une seule connexion, une seule base, un référentiel et des fiches
personnes partagés par tous les modules). Les interfaces reprennent le design de
l'application EDT.

La base actuelle ne contient aucune donnée à conserver : on part d'un schéma neuf.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Une seule connexion (JWT) pour tous les utilisateurs, étudiants compris.
- Un socle `core` : comptes, droits par module, référentiel académique, fiches personnes.
- Cinq modules métier branchés sur ce socle : Scolarité, Emploi du temps, RH,
  Finance, Logistique ; plus Paramètres (administration) et un Espace personnel
  (étudiant / enseignant).
- Une seule application React, avec un lanceur de modules en accueil.
- Reprise de toute la logique métier existante (règles, calculs, documents) et de
  ses tests.
- Des liens automatiques entre modules (section 7).

**Non-objectifs**
- Migrer les données actuelles.
- Installer/désinstaller des modules à chaud comme Odoo : les modules sont des
  apps Django fixes ; un module « absent » pour un utilisateur = pas de droit dessus.
- Multi-établissement, multi-langue (tout reste en français), application mobile,
  paiement en ligne.
- Nouvelles fonctionnalités métier non présentes aujourd'hui, sauf les liens entre
  modules de la section 7 et la grille de tarifs (demandée par l'utilisateur).

**Anti-objectifs** (échec même si « ça marche »)
- Une même personne saisie deux fois dans deux modules.
- Un module qui garde son propre référentiel (sa propre faculté, sa propre année).
- Une deuxième page de connexion.
- Une interface qui mélange l'ancien `Shell` (Font Awesome, CSS maison) et le
  design EDT.

## 3. Contraintes

- Stack conservée : Python / Django 5.x, Django REST Framework, SimpleJWT
  (avec blacklist), MySQL ; React 18, Vite, Tailwind 3, shadcn/Radix,
  react-router 6, TanStack Query, zustand, react-hook-form + zod, lucide-react,
  FullCalendar, Chart.js.
- Configuration par `.env` (python-decouple), jamais de secret versionné.
- Les anciens dossiers (`uccb_backend/`, `uccb_frontend/`,
  `Projet-Gestion-Acad-mique-main/`) restent intacts comme référence pendant la
  construction. Leur suppression sera une décision séparée de l'utilisateur.

## 4. Approches envisagées

- **A. Nouveau backend sur socle unique + une seule SPA** (retenue). Nouveau projet
  Django avec une app `core` dont dépendent tous les modules ; reprise du code
  métier existant ; frontend construit à partir de l'application EDT. Seule
  approche qui donne un système réellement centralisé sans doublons. Coût :
  le plus gros chantier, rendu raisonnable par l'absence de données à migrer.
- **B. Garder les apps et les relier** (connexion et shell communs, liens entre
  tables en double). Plus rapide, mais les doublons restent et doivent être
  synchronisés : contraire à l'objectif. Écartée.
- **C. Réécrire en modules Odoo.** Jette tout le code Django/React existant et
  impose une stack étrangère au projet. Écartée.

L'utilisateur a choisi **A**.

## 5. Architecture

```
erp/
├── backend/
│   ├── manage.py
│   ├── config/              # settings, urls, wsgi
│   ├── core/                # comptes, droits, référentiel, personnes, audit, PDF
│   ├── scolarite/           # inscriptions, notes, délibérations, documents officiels
│   ├── edt/                 # modules horaires, affectations, séances, documents pédagogiques
│   ├── rh/                  # contrats, vacations, personnel
│   ├── finance/             # frais étudiants, paie, journal, dépenses
│   └── logistique/          # bus, trajets, affectations transport
└── frontend/
    └── src/
        ├── app/             # routeur, lanceur, layout commun
        ├── modules/<module>/  # pages et hooks propres à chaque module
        ├── components/      # ui shadcn + composants partagés (repris de l'EDT)
        └── lib/, api/, store/
```

- Règle de dépendance : chaque module dépend de `core` ; un module peut lire un
  autre module uniquement via des fonctions de service documentées
  (`<module>/services.py`), jamais en modifiant ses tables directement. Les
  liens automatiques passent par des signaux ou ces services.
- API : tout sous `/api/<module>/…` (`/api/core/…` pour le socle), DRF
  ViewSets/routers, pagination et gestionnaire d'erreurs repris de l'EDT
  (`pagination.py`, `exception_handlers.py`).
- En production, Django sert le build de la SPA (vue catch-all hors `/api/`,
  `/admin/`, `/media/`, `/verifier/`). En développement, Vite proxifie `/api`.

## 6. Le socle `core`

### 6.1 Comptes et droits
- Un seul modèle utilisateur : `User` Django standard (identifiant = e-mail ou
  matricule, au choix du builder). Les étudiants ont aussi un `User` : on supprime
  `CompteEtudiant` et `EtudiantUser`.
- **Droits par module, façon Odoo** : pour chaque module, deux niveaux portés par
  des groupes Django nommés `<module>_utilisateur` et `<module>_responsable`
  (ex. `rh_responsable`). Le superuser a tout.
- **Rôles contextuels** déduits des données, comme dans l'EDT actuel :
  chef de département (dirige un `Departement`), référent de classe
  (`ReferentClasse`), enseignant (a une fiche `Enseignant`), étudiant
  (a une fiche `Etudiant`).
- Le jeton JWT et la réponse `/api/core/moi/` renvoient : identité, photo,
  liste des modules accessibles avec leur niveau, rôles contextuels. Le frontend
  construit le lanceur à partir de cette liste.
- Suspension d'un profil (avec motif) bloque la connexion — logique reprise de
  `EDT_app/authentication.py`. Limitation des tentatives par compte et par IP
  reprise de `EDT_app/throttles.py`. Réinitialisation de mot de passe par
  l'administrateur (comme aujourd'hui) ; pas d'envoi d'e-mail requis.

### 6.2 Référentiel académique (unique)
Fusion des deux référentiels actuels :

- `AnneeAcademique` : libellé, dates, statut active/archivée, une seule active.
- `Periode` : deux périodes par année (« Semestre 1 », « Semestre 2 ») avec dates —
  le calendrier de l'EDT.
- `Faculte` : nom, code, logo, doyen et vice-doyen (nom + genre, pour les titres
  des signataires).
- `Departement` : faculté, chef (→ `Enseignant`).
- `Portail` : tronc commun de L1 rattaché à une faculté (MIP, BCG, PCG).
- `Filiere` : département porteur + portail d'origine (spécialisation à partir de S3),
  responsable (→ `Enseignant`).
- `Parcours` : type (Licence, Master, Doctorat) + niveau, avec les maxima actuels.
- `Classe` : **annuelle** — année + niveau (parcours : L1, L2, L3, M1, M2) +
  portail **ou** filière (exactement un des deux ; portail pour L1, filière à
  partir de L2). Une classe couvre les deux semestres de son niveau
  (L1 = S1+S2, L2 = S3+S4, … M2 = S9+S10). Libellé généré. Le Doctorat n'a ni
  classes ni notes dans l'ERP (hors périmètre). *(choix du concepteur, découle de
  l'inscription annuelle décidée par l'utilisateur)*
- `UniteEnseignement` (UE) : code, libellé, semestre de cursus (S1…S10), portail
  ou filière. Le semestre de l'UE fixe la période calendaire de ses EC :
  semestre impair → période 1, pair → période 2.
- `ElementConstitutif` (EC) : l'unité pédagogique unique, qui fusionne la
  `Matiere` de la scolarité et le `Module` de l'EDT. Champs : UE, libellé,
  code, crédits, heures CM/TD/TP, département porteur, description.
  C'est sur l'EC qu'on saisit des notes **et** qu'on planifie des séances.
- `ParametresEtablissement` : secrétaire général (nom + genre), ville de signature
  (repris de `ParametresUCCB`).

### 6.3 Personnes (fiche unique)
- `Personne` : nom, prénom, genre, date et lieu de naissance, nationalité, e-mail,
  téléphone, adresse, photo, statut (actif/suspendu + motif), `User` optionnel.
- Rôles rattachés en un-pour-un (une personne peut en cumuler plusieurs) :
  - `Etudiant` : matricule auto (`UCCB{année}{NOM3}{PR2}{n°}`), statut
    actif/diplômé/abandon.
  - `Enseignant` : matricule auto `UCCB-ENS-xxxxx`, grade, département,
    chef de département.
  - `Employe` (personnel non enseignant) : matricule auto `UCCB-PERS-xxxxx`,
    fonction (ménage, gardien, cuisinier, chauffeur, technicien, autre + libellé),
    lieu de travail, faculté de rattachement.
- Validations de noms et d'âge reprises de `gestion_eleves/models.py`.

### 6.4 Transverse
- `JournalAudit` (repris d'`AuditLog`) : utilisateur, module, action, description,
  IP, date — écrit par tous les modules pour les actions sensibles (paiements,
  notes, changements de statut, droits).
- Utilitaires PDF (xhtml2pdf + `pdf_utils.py`), QR code (qrcode), Excel (openpyxl),
  validation des fichiers téléversés (`EDT_app/fichiers.py`).

## 7. Modules

Chaque module liste ce qu'il reprend. « Reprendre » = porter le code existant sur
le nouveau modèle en gardant le comportement, y compris les tests.

### 7.1 Scolarité
- `Inscription` (reprise de l'EDT) : étudiant, année, classe, type
  (première inscription / réinscription), statut (active, terminée, abandonnée),
  date. **Inscription annuelle** (décision de l'utilisateur) : une seule
  inscription par étudiant et par année académique, dans une classe annuelle qui
  couvre les deux semestres du niveau. L'inscription remplace les champs
  `semestre`/`portail`/`filiere` stockés sur l'étudiant.
- À l'inscription : création automatique des lignes de notes pour tous les EC de
  la classe (reprise du signal `inscrire_aux_matieres`).
- `Note` : inscription + EC ; devoir, session, rattrapage (SR), absent ; moyenne
  stockée. Formule reprise telle quelle : `(devoir+session)/2`, avec SR
  `max(normale, (devoir+2×SR)/3)`, absent = 0.
- `ResultatSemestre` : inscription + semestre (les deux semestres du niveau, donc
  deux résultats par inscription) ; moyenne, crédits obtenus/totaux, décision,
  mention, rang, archivé. La délibération reste semestrielle, comme aujourd'hui.
- Moteur de calcul (`engine.py`) repris sans changement de règles : note saisie
  < 6 éliminatoire, ADMIS si moyenne ≥ 10 sans éliminatoire, tous les crédits
  acquis si ADMIS, EC sans note ignoré, mentions actuelles.
- Écrans : tableau de bord, étudiants (liste, fiche, ajout, changement de statut),
  inscriptions, saisie des notes par classe/EC, fiche de notes individuelle,
  délibération + export Excel, promotion en lot, orientation S3 (portail → filière),
  matrice A3 PDF (avec vérification préalable), attestation, relevé de notes.
- **Promotion = passage d'année** : la faculté sélectionne les étudiants
  (résultats des deux semestres requis, comme la promotion actuelle exige des
  résultats) ; l'ERP termine leur inscription et en crée une nouvelle dans la
  classe du niveau suivant pour l'année suivante. À la fin de L1, l'**orientation**
  choisit la filière de la classe de L2. Le choix des promus reste manuel, comme
  aujourd'hui : aucune règle de passage annuel automatique. *(choix du concepteur)*
- Page publique `/verifier/<jeton>` ouverte par le QR code des documents. Le jeton
  est opaque (pas l'id brut de l'étudiant comme aujourd'hui).
- Droits (exception au schéma utilisateur/responsable, pour coller aux deux
  métiers actuels) :
  - `scolarite_secretariat` : étudiants, inscriptions, changements de statut,
    attestations, relevés, référentiel des UE/EC ;
  - `scolarite_faculte` : **saisie des notes, délibération**, promotion,
    orientation S3, matrice A3, confirmation des vacations (section 7.3).
    Décision de l'utilisateur : notes et délibérations se font à la faculté ;
    les enseignants ne saisissent pas de notes, leur Espace ne fait que consulter.
  - Un utilisateur Scolarité peut être rattaché à une faculté : il ne voit alors que
    les étudiants, classes et vacations de cette faculté ; sans rattachement, il
    voit tout. *(choix du concepteur)*

### 7.2 Emploi du temps
Reprise quasi intégrale d'`EDT_app` et de ses écrans, renommés sur le nouveau
référentiel (`Module` → `ElementConstitutif`, `Classe`, `Periode`).
- `AffectationEC` : EC + enseignant + type de séance + heures prévues,
  hors-département, alerte de dépassement.
- `Seance` : cycle brouillon → confirmée / annulée / reportée, publication,
  dépublication, publication en masse, report, séances liées/mutualisées,
  détection des conflits.
- Toutes les règles de `validation_seance.py` reprises (dimanche, pause méridienne,
  bornes de période — la période est celle du semestre de l'EC, puisque la classe
  est annuelle —, année archivée, conflits enseignant/classe, doublon, quotas EC
  et affectation, volume journalier, créneau de report).
- `ReferentClasse`, `DocumentPedagogique` (téléversement/téléchargement),
  périmètre d'accès (`perimetre.py`).
- Écrans : planning (grille/tableau, filtres), séances, affectations, organisation,
  contenu pédagogique, trombinoscope, progression.
- Droits : responsable = administration de tout l'EDT ; chef de département et
  référent = gestion dans leur périmètre ; enseignant et étudiant = leur planning
  via l'Espace personnel.

### 7.3 Ressources humaines
- `Contrat` (sur `Enseignant` ou `Employe`) : type permanent/vacataire, dates,
  salaire mensuel ou taux horaire, RIB, n° sécurité sociale, diplôme ; détection
  des contrats expirés.
- **Vacations** (décision de l'utilisateur : un vacataire est payé quand il
  **termine son module / son volume horaire**, pas au mois) :
  - l'unité de vacation est l'`AffectationEC` de l'EDT (EC + type de séance +
    heures prévues) ; l'ancien `AffectationVacataire` disparaît ;
  - une affectation est **terminée** quand ses heures effectuées (séances
    confirmées et passées) atteignent les heures prévues. Elle apparaît alors
    dans la liste « vacations à confirmer » de la faculté de l'EC ;
  - la faculté (`scolarite_faculte`) **confirme** l'affectation, avec les heures
    retenues (par défaut les heures effectuées ; modifiables avec motif, p. ex.
    module arrêté avant la fin). Elle peut aussi confirmer une affectation non
    terminée dans ce cas ;
  - la confirmation crée la ligne de paie de la vacation en Finance
    (heures retenues × taux horaire du contrat) ; retirer la confirmation n'est
    possible que tant que la ligne n'est pas payée ;
  - l'historique avec motif porte sur les heures retenues à la confirmation, pas
    sur les modifications courantes des affectations dans l'EDT.
- Écrans : tableau de bord, enseignants (liste, ajout, statut), personnel
  (liste, ajout, statut), vacations (volumes, confirmation, historique), contrats
  arrivant à échéance.

### 7.4 Finance
- `FraisScolarite` : un dossier par inscription (donc par étudiant et par année),
  créé avec elle. Le montant dû vient de la **grille de tarifs**
  (décision de l'utilisateur) : `Tarif` = année académique + niveau
  (L1, L2, L3, M1, M2) + montant, géré dans Paramètres. Si aucun tarif n'existe
  pour le niveau, le dossier est créé à 0 et signalé sur le tableau de bord
  Finance. Le montant reste modifiable par `finance_responsable`, avec trace au
  journal d'audit *(choix du concepteur)*. Champs : montant dû, montant payé, statut
  payé/partiel/non payé) et ses `PaiementEtudiant` (montant, mode : espèces,
  Mobile Money, virement, chèque ; date ; reçu PDF).
- `Paie` : montant dû, montant payé, statut (en attente / partiel / payé), mode,
  date ; deux origines :
  - **salaire** : une ligne par permanent ou employé et par mois (`AAAA-MM`),
    montant = salaire mensuel du contrat ;
  - **vacation** : une ligne par affectation confirmée par la faculté
    (section 7.3), montant = heures retenues × taux horaire.
- `Operation` (journal, reprise de `Transaction`) : libellé, montant
  (+ recette / − dépense), date, reçu PDF. Chaque paiement étudiant, paie et
  dépense transport y écrit automatiquement sa ligne.
- `DepenseTransport` : bus, type (carburant, entretien, réparation), montant,
  description, date.
- Écrans : tableau de bord (KPI + graphique de trésorerie), frais étudiants,
  paie enseignants, paie personnel, journal, transports.

### 7.5 Logistique
- `Bus` (numéro, plaque, capacité, statut), `Trajet` (départ, destination, horaires),
  `AffectationTransport` (bus + chauffeur + trajet + dates, une seule active par bus).
- Le chauffeur est un `Employe` de fonction « chauffeur » avec un contrat actif.
- Écrans : bus, trajets, affectations, et un onglet coûts qui lit les dépenses
  transport de la Finance.

### 7.6 Paramètres (administrateur)
Utilisateurs et droits par module (avec rattachement à une faculté pour la
Scolarité), référentiel académique (années, périodes, facultés, départements,
portails, filières, parcours, classes), **grille de tarifs** par année et niveau,
paramètres établissement, journal d'audit.

### 7.7 Espace personnel
Pour toute personne connectée qui a un rôle étudiant ou enseignant :
- étudiant : planning, notes et résultats, progression, documents pédagogiques,
  trombinoscope, profil, situation de ses frais ;
- enseignant : planning, mes EC/affectations, documents, classes (lecture), profil.

### Liens automatiques entre modules (récapitulatif)
| Événement | Effet |
|---|---|
| Inscription créée (Scolarité) | lignes de notes créées ; dossier de frais de l'année créé au tarif du niveau (Finance) |
| Enseignant créé (RH) | affectable dans l'EDT, éligible à la paie |
| Séance confirmée (EDT) | heures effectuées de l'affectation mises à jour ; affectation terminée → « à confirmer » par la faculté |
| Vacation confirmée (Scolarité/faculté) | ligne de paie vacation créée (Finance) |
| Paiement, paie, dépense transport (Finance) | ligne au journal des opérations |
| Employé « chauffeur » actif (RH) | sélectionnable en Logistique |

## 8. Interface

- Base : l'application EDT d'origine, `Projet-Gestion-Acad-mique-main/edt-frontend`
  (`components/layout/AppShell|Sidebar|Topbar`, `components/ui` shadcn,
  `components/shared` dont `DataTable`, `index.css`) — thème shadcn clair,
  couleur primaire verte UCCB (`--primary: 147.6 83.4% 26.1%`), logo
  `assets/login/logo-uccb.svg`, police Inter, tiroirs, dialogues, toasts. La
  palette navy/teal de `uccb_frontend/src/styles/tokens.css` appartient à
  l'ancien écran Finance et n'est pas reprise. Les écrans métier de l'EDT
  (`features/`) sont repris depuis `uccb_frontend/src/features`, qui en est la
  version la plus récente.
- **Accueil = lanceur** : grille de tuiles (icône lucide + nom), uniquement les
  modules accessibles à l'utilisateur.
- **Dans un module** : barre latérale propre au module (son menu), bouton ⊞ qui
  revient au lanceur, barre supérieure avec titre de page et menu utilisateur
  (profil, déconnexion). Responsive mobile comme le layout EDT.
- Routes : `/login`, `/`, `/scolarite/…`, `/edt/…`, `/rh/…`, `/finance/…`,
  `/logistique/…`, `/parametres/…`, `/moi/…`. Chaque route vérifie le droit du
  module (sinon page 403).
- Les écrans des anciens modules (Shell) sont refaits avec les composants EDT ;
  leurs contenus et actions sont repris, pas leur apparence.

## 9. Données de démonstration et tests

- Commande `python manage.py seed_demo` : une année active, 2 facultés avec
  départements, portails, filières, classes L1–M1, UE/EC, ~10 enseignants
  (permanents et vacataires), ~10 employés dont 2 chauffeurs, ~60 étudiants
  inscrits avec des notes, des séances, des paiements, 3 bus ; un compte par profil
  type (admin, responsable de chaque module, chef de département, enseignant,
  étudiant). Les mots de passe de démo sont écrits dans `erp/backend/README.md`.
- Tests : les ~400 tests existants de l'EDT sont portés ; tests du moteur de notes
  (règles de la section 7.1) ; tests de droits par module ; tests des liens
  automatiques de la section 7. Exécutables sur SQLite en local.

## 10. Livraison par phases

Chaque phase se termine sur un système qui démarre, avec ses tests au vert.

1. **Socle** : projet `erp/`, `core` (comptes, droits, référentiel, personnes,
   audit), connexion JWT, `/api/core/moi/`, frontend avec login, lanceur, layout
   module, Paramètres.
2. **Emploi du temps** + Espace personnel (partie planning).
3. **Scolarité** (inscriptions, notes, moteur, documents, QR) + Espace étudiant (notes).
4. **RH** (contrats, personnel, vacations).
5. **Finance** (frais, paie, journal, dépenses) avec ses liens automatiques.
6. **Logistique**, puis `seed_demo` complet et passe finale.

## 11. Laissé au builder

- Identifiant de connexion (e-mail ou matricule).
- Noms exacts des modèles, champs, endpoints et fichiers, dans l'esprit ci-dessus.
- Découpage interne des composants React et des hooks.
- Choix du mécanisme (signaux ou services) pour chaque lien automatique.
- Adaptation des tests EDT au nouveau modèle quand un renommage l'impose.
