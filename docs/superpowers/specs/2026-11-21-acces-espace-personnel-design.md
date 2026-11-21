# Accès à l'espace personnel — Document de conception

Date : 2026-11-21
Statut : validé par l'utilisateur le 2026-11-21

## 1. Intention

Les étudiants et les enseignants accèdent à « Mon espace » (`/moi`) par la page de connexion commune.
Trois obstacles rendent cet accès dépendant de l'administration ou maladroit :

1. un enseignant ne peut pas activer son compte : l'administration doit le créer dans Paramètres et lui
   transmettre un mot de passe ;
2. il n'existe pas de « mot de passe oublié » : la page dit « Contactez l'administration » ;
3. après la connexion, une personne qui n'a que son espace personnel arrive sur le lanceur, qui ne contient
   qu'une tuile.

But : qu'un étudiant ou un enseignant obtienne, retrouve et atteigne son espace sans passer par l'administration.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Activation du compte par l'enseignant lui-même, sur le modèle de l'activation étudiant.
- Réinitialisation du mot de passe par un lien envoyé par e-mail, pour tout compte qui a une adresse.
- Arrivée directe sur `/moi` pour qui n'a aucun module.

**Non-objectifs**
- Changement de mot de passe depuis l'espace connecté (« changer mon mot de passe »).
- Activation par les employés (sans espace personnel aujourd'hui).
- Vérification de l'adresse e-mail, double authentification.
- Mise en forme HTML des e-mails : texte brut.

**Anti-objectifs** (échec même si « ça marche »)
- Une réponse qui révèle si un identifiant, un matricule ou une adresse existe.
- Un lien de réinitialisation réutilisable, ou encore valable après usage ou changement de mot de passe.
- Une session ouverte ailleurs qui survit à une réinitialisation.
- Une deuxième page d'activation (une pour les étudiants, une pour les enseignants).
- Un secret (mot de passe SMTP) versionné.

## 3. Contraintes

- Stack existante : Django 5.2, DRF, SimpleJWT avec blacklist ; React 18, react-hook-form, TanStack Query.
- Configuration par `.env` (python-decouple), lue aussi par la pile Docker (`erp/.env`).
- Aucun envoi d'e-mail n'existe aujourd'hui ; aucun serveur SMTP n'est fourni en développement.
- Tout reste en français ; même charte que les pages `LoginPage` et `ActivationPage`.

## 4. Approches envisagées

Seul le mot de passe oublié offrait un vrai choix.

- **A. Lien par e-mail** (retenue par l'utilisateur). L'utilisateur saisit son identifiant ou son adresse
  et reçoit un lien à durée limitée. Seule option qui supprime le passage par l'administration. Coût : une
  adresse d'envoi SMTP à configurer.
- **B. Réinitialisation par identité** (matricule + e-mail + date de naissance). Écartée : un camarade qui
  connaît ces informations peut prendre le compte.
- **C. Demande traitée par l'administration** (code temporaire remis en main propre). Écartée : sûre, mais
  garde l'administration dans la boucle, ce que l'on veut éviter.

Activation enseignant et redirection : une seule approche raisonnable (sections 5.1 et 5.3).

## 5. Conception

### 5.1 Activation commune étudiants et enseignants

- L'activation quitte le module Scolarité pour le socle : `POST /api/core/activation/`
  (`core/api/activation.py`). `POST /api/scolarite/activation/` est supprimé ; seul le frontend l'appelait.
- Champs inchangés : `matricule`, `email`, `date_naissance`, `password`.
- Le matricule désigne la fiche : `Etudiant` dont le statut est `actif`, sinon `Enseignant`.
  Recherche insensible à la casse (les matricules enseignants sont `UCCB-ENS-…`).
- Conditions, toutes requises, sinon le même message d'échec générique qu'aujourd'hui (`ECHEC_ACTIVATION`) :
  la fiche existe ; la personne n'a pas encore de compte ; elle n'est pas suspendue ; l'e-mail correspond
  (insensible à la casse) ; la date de naissance correspond ; aucun utilisateur n'a déjà ce matricule pour
  identifiant.
- Le compte créé a le matricule pour identifiant, l'e-mail, le prénom et le nom de la personne ; il est lié à
  la personne. Aucun groupe : les rôles `enseignant` / `etudiant` découlent déjà de la fiche
  (`core/droits.py`).
- Throttles inchangés (par IP + matricule, et par IP). Journal d'audit : module `core`, action
  `activation_compte`, cible le matricule.
- Page `/activation` : titre « Activer mon compte », sous-titre qui couvre les deux cas (« informations
  données au secrétariat ou aux ressources humaines »), champs inchangés. Après succès, retour à la connexion
  avec le message actuel (« Compte activé… Identifiant : <matricule> »).
- Les tests d'activation de `scolarite/tests/test_espace_etudiant.py` passent dans `core/tests/` et couvrent
  aussi l'enseignant.

### 5.2 Mot de passe oublié

**Envoi d'e-mails**
- Nouveaux réglages lus dans `.env` : `EMAIL_HOST`, `EMAIL_PORT` (587), `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` (True), `DEFAULT_FROM_EMAIL`.
- Sans `EMAIL_HOST`, le backend console est utilisé : l'e-mail s'affiche dans les journaux
  (`docker compose logs web`). C'est le cas en développement.
- `erp/.env.example` et `erp/backend/.env.example` documentent ces variables ; `erp/docker/README.md`
  explique comment renseigner une adresse d'envoi.

**Demande** — `POST /api/core/mot-de-passe/oubli/`, sans authentification, champ `identifiant`.
- `identifiant` est un identifiant de connexion ou une adresse e-mail (insensible à la casse).
- Compte retrouvé par identifiant, sinon par e-mail de la personne liée, sinon par `User.email`.
- Un e-mail part seulement si : le compte existe, est actif, sa personne n'est pas suspendue, et une adresse
  est connue (celle de la personne, à défaut `User.email`).
- Réponse toujours identique, `200` : « Si un compte correspond, un e-mail contenant un lien vient d'être
  envoyé. » Erreur d'envoi SMTP : journalisée côté serveur, même réponse.
- Throttles : même plafond que la connexion, par IP + identifiant saisi, et par IP.
- Journal d'audit à chaque envoi effectif (`core`, `demande_reinitialisation`, identifiant du compte).

**E-mail** — texte brut : salutation avec le nom, lien
`{BASE_URL}/reinitialisation/<uid>/<jeton>`, durée de validité, phrase « Si vous n'avez rien demandé,
ignorez ce message. »
- `uid` : identifiant du compte en base64 URL ; `jeton` : `default_token_generator` de Django.
  Ce jeton devient invalide dès que le mot de passe change ou que le compte se reconnecte
  (`last_login`), et expire après `PASSWORD_RESET_TIMEOUT`, fixé à **1 heure**.

**Nouveau mot de passe** — `POST /api/core/mot-de-passe/reinitialisation/`, sans authentification,
champs `uid`, `jeton`, `password`.
- Lien invalide ou expiré : `400` « Ce lien n'est plus valable. Faites une nouvelle demande. »
- Mot de passe soumis aux validateurs Django, erreurs sur le champ `password`.
- Succès : mot de passe enregistré ; tous les refresh tokens encore valides du compte sont mis sur liste noire
  (les autres sessions tombent au plus tard à l'expiration de leur jeton d'accès, 2 h) ; journal d'audit
  (`core`, `reinitialisation_mot_de_passe`). Réponse : « Mot de passe modifié. Connectez-vous. »
- Throttle par IP.

**Pages**
- Page de connexion : « Mot de passe oublié ? Contactez l'administration. » devient un lien
  « Mot de passe oublié ? » vers `/mot-de-passe-oublie`.
- `/mot-de-passe-oublie` : un champ « Identifiant ou e-mail », bouton « Envoyer le lien » ; après envoi, le
  message neutre remplace le formulaire, avec un lien de retour à la connexion.
- `/reinitialisation/:uid/:jeton` : « Nouveau mot de passe » et « Confirmer » ; après succès, retour à la
  connexion avec le message de succès (`noterMessageConnexion`, comme l'activation). Lien invalide : message et
  lien vers une nouvelle demande.
- Ces deux pages sont publiques, dans la charte d'`ActivationPage`.

### 5.3 Arrivée directe dans « Mon espace »

- Le lanceur (`/`) redirige vers `/moi` quand la personne n'a **aucun module** et a le rôle `etudiant` ou
  `enseignant`. Cela couvre la connexion et toute visite de `/`.
- Dans ce cas, le lien « Tous les modules » du menu latéral (`ModuleShell`) est masqué : il ramènerait
  aussitôt sur `/moi`.
- Avec au moins un module (chef de département, référent, administrateur lié à un enseignant…), le lanceur
  reste inchangé.
- La redirection vers la page demandée avant connexion (`location.state.from`) garde la priorité.

## 6. Tests attendus

- Backend : activation étudiant et enseignant (succès, chaque condition d'échec, réponse identique,
  identifiant créé, audit) ; oubli (identifiant, e-mail, inconnu, compte inactif, personne suspendue, sans
  adresse : même réponse ; un seul e-mail envoyé quand il faut, lien bien formé) ; réinitialisation (succès,
  jeton réutilisé, jeton expiré, uid invalide, mot de passe faible, refresh tokens blacklistés).
- Frontend (Vitest) : pages oubli et réinitialisation, lien depuis la connexion, redirection du lanceur,
  « Tous les modules » masqué.
- Vérification manuelle dans la pile Docker de dev : parcours complet avec l'e-mail lu dans les journaux.

## 7. Choix du concepteur à relire

- Un enseignant peut activer son compte dès que sa fiche existe, sans exiger de contrat en cours : l'espace ne
  montre que ses propres affectations.
- Un compte sans adresse e-mail (ni sur la personne, ni sur le compte) ne peut pas se réinitialiser seul : il
  reste réinitialisable dans Paramètres.
- Lien valable 1 heure, et invalidé si le compte se reconnecte entre-temps.
- Les liens `/reinitialisation/…` sont servis par la route SPA existante (`core/spa.py`) : rien à ajouter à
  nginx.

## 8. Laissé au builder

- Découpage interne des vues et serializers dans `core/api/`, noms exacts des composants React.
- Rédaction exacte des textes, dans l'esprit ci-dessus.
- Mécanisme de liste noire des refresh tokens (`OutstandingToken` de SimpleJWT).
- `BASE_URL` de la pile de dev : la passer à `http://localhost:5180` dans `docker-compose.dev.yml` pour que les
  liens d'e-mail ouvrent l'interface de dev. *(choix du concepteur)*
