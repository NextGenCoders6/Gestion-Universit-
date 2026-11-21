# Accès à l'espace personnel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** un étudiant ou un enseignant active son compte, retrouve son mot de passe par e-mail et arrive directement dans « Mon espace », sans passer par l'administration.

**Architecture :** l'activation passe de `scolarite` au socle `core` et couvre les deux fiches. Le mot de passe oublié repose sur `default_token_generator` de Django et l'envoi d'e-mails configuré par `.env` (backend console par défaut). La redirection vers `/moi` se fait dans le lanceur React.

**Tech Stack :** Django 5.2, DRF, SimpleJWT (blacklist), python-decouple ; React 18, react-router 6, react-hook-form, Vitest + Testing Library.

**Spec :** `docs/superpowers/specs/2026-11-21-acces-espace-personnel-design.md`

## Global Constraints

- Tous les textes en français, dans la charte de `ActivationPage` / `LoginPage`.
- Aucun secret versionné : réglages SMTP seulement dans `.env` / `erp/.env`.
- Réponses publiques qui ne révèlent jamais l'existence d'un compte, d'un matricule ou d'une adresse.
- `PASSWORD_RESET_TIMEOUT = 3600` (1 heure).
- Messages exacts :
  - activation, échec : `Informations incorrectes ou compte déjà activé.`
  - activation, succès : `Compte activé. Connectez-vous avec votre matricule.`
  - demande : `Si un compte correspond, un e-mail contenant un lien vient d'être envoyé.`
  - lien invalide : `Ce lien n'est plus valable. Faites une nouvelle demande.`
  - réinitialisation, succès : `Mot de passe modifié. Connectez-vous.`
- Lien d'e-mail : `{BASE_URL}/reinitialisation/<uid>/<jeton>`.
- Audit, module `core` : `activation_compte`, `demande_reinitialisation`, `reinitialisation_mot_de_passe`.

**Lancer les tests** (pile de dev démarrée, depuis `erp/`) :

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e DB_ENGINE=sqlite web python manage.py test <cible>
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npx vitest run <fichier>
```

## Review Focus

1. Identifiant saisi avec des espaces ou une casse différente (`  Admin `, `DIVINE@Example.org`) : le compte est retrouvé.
2. Deux comptes possibles pour une même saisie (l'identifiant d'un compte égal à l'e-mail d'une autre personne) : l'identifiant gagne, un seul e-mail part.
3. Lien utilisé deux fois, ou après que la personne s'est reconnectée : refusé avec le message « lien invalide ».
4. Panne SMTP à l'envoi : réponse neutre `200`, erreur journalisée, pas de `500`.
5. Personne qui est à la fois enseignant et chef / référent (au moins un module) : le lanceur n'est pas court-circuité.

Chaque point a son test dans la tâche qui possède le code (1 et 2 : Task 2 ; 3 et 4 : Tasks 2 et 3 ; 5 : Task 5).

---

### Task 1 : Activation commune dans le socle

**Files :**
- Create : `erp/backend/core/api/activation.py`
- Modify : `erp/backend/core/throttles.py` (ajout `ParChampRateThrottle`, `ActivationRateThrottle`)
- Modify : `erp/backend/core/urls.py` (route `activation/`)
- Modify : `erp/backend/scolarite/views_etudiant.py` (retirer `ECHEC_ACTIVATION`, `ActivationRateThrottle`, `ActivationSerializer`, `ActivationView` et les imports devenus inutiles)
- Modify : `erp/backend/scolarite/urls.py` (retirer `activation/`)
- Create : `erp/backend/core/tests/test_activation.py`
- Modify : `erp/backend/scolarite/tests/test_espace_etudiant.py` (retirer `ActivationTests`)
- Modify : `erp/frontend/src/features/auth/ActivationPage.jsx`, `ActivationPage.test.jsx`

**Interfaces :**
- Produces : `POST /api/core/activation/` (nom `core_activation`), corps `{matricule, email, date_naissance, password}` → `201 {detail, username}` ou `400 {detail: ECHEC_ACTIVATION}` ou `400 {password: [...]}`.
- Produces : `core.throttles.ParChampRateThrottle(SimpleRateThrottle)` avec attributs de classe `champ: str` et `prefixe: str`, scope `login` ; clé = `prefixe` + IP + sha256 de `request.data[champ]` (strip, lower, 32 caractères) — même calcul que l'actuel `ActivationRateThrottle`.
- Produces : `core.throttles.ActivationRateThrottle(ParChampRateThrottle)`, `champ='matricule'`, `prefixe='activation'`.

- [ ] **Step 1 : écrire `core/tests/test_activation.py`**

Reprendre les 4 tests de `ActivationTests` (même corps, URL `/api/core/activation/`), avec des données construites par `core.tests.fabriques` (`personne`, `annee`, `departement`) et `Etudiant.objects.create(personne=…, annee_entree=…)`. Ajouter :

```python
def test_enseignant_active_son_compte(self):
    ens = Enseignant.objects.create(personne=f.personne('Mbemba', 'Christelle', email='c.mbemba@example.org',
                                                        date_naissance=date(1985, 5, 2)),
                                    departement=f.departement())
    r = self.anonyme.post('/api/core/activation/', {'matricule': ens.matricule.lower(), 'email': 'c.mbemba@example.org',
                          'date_naissance': '1985-05-02', 'password': MDP}, format='json')
    self.assertEqual(r.status_code, 201, r.data)
    self.assertEqual(r.data['username'], ens.matricule)
    ens.personne.refresh_from_db()
    self.assertEqual(ens.personne.user.username, ens.matricule)
    moi = self.anonyme.post('/api/core/token/', {'username': ens.matricule, 'password': MDP}, format='json')
    self.assertIn('enseignant', moi.data['user']['roles'])

def test_personne_suspendue_refusee(self):     # étudiant et enseignant : 400, message générique
def test_journal_module_core(self):            # JournalAudit(module='core', action='activation_compte', description=matricule)
```

- [ ] **Step 2 : lancer `core.tests.test_activation`** — attendu : échecs (404 sur l'URL).
- [ ] **Step 3 : implémenter `ActivationSerializer` et `ActivationView` dans `core/api/activation.py`** — reprendre le code de `scolarite/views_etudiant.py:42-81`. Recherche de la fiche : `Etudiant.objects.filter(matricule__iexact=m, statut='actif').first()`, sinon `Enseignant.objects.filter(matricule__iexact=m).first()` ; l'identifiant créé est le matricule de la fiche trouvée. `journaliser(request, 'core', 'activation_compte', matricule)`. Throttles : `[ActivationRateThrottle, LoginIPRateThrottle]`. Retirer l'ancien code de `scolarite` et ses tests.
- [ ] **Step 4 : `ActivationPage.jsx`** — appel `apiClient.post('/core/activation/', …)` ; titre `Activer mon compte` ; sous-titre `Saisissez les informations données au secrétariat ou aux ressources humaines.` ; commentaire d'en-tête : étudiants et enseignants. Mettre à jour l'URL attendue dans `ActivationPage.test.jsx`.
- [ ] **Step 5 : lancer** `manage.py test core scolarite` et `npx vitest run src/features/auth/ActivationPage.test.jsx` — attendu : tout passe.
- [ ] **Step 6 : commit** `feat(core): activation du compte pour les enseignants`

### Task 2 : Demande de réinitialisation et envoi de l'e-mail

**Files :**
- Modify : `erp/backend/config/settings.py` (réglages e-mail, `PASSWORD_RESET_TIMEOUT`)
- Create : `erp/backend/core/api/mot_de_passe.py`
- Modify : `erp/backend/core/throttles.py` (`OubliRateThrottle`)
- Modify : `erp/backend/core/urls.py` (route `mot-de-passe/oubli/`)
- Create : `erp/backend/core/tests/test_mot_de_passe.py`
- Modify : `erp/.env.example`, `erp/backend/.env.example`, `erp/docker/README.md`, `erp/docker-compose.dev.yml`

**Interfaces :**
- Produces : `compte_pour_identifiant(saisie: str) -> User | None` — strip ; d'abord `User.username__iexact`, sinon `Personne.email__iexact` (son `user`), sinon `User.email__iexact` (premier).
- Produces : `adresse_de(user: User) -> str | None` — e-mail de la personne liée, sinon `user.email`, sinon `None`.
- Produces : `lien_reinitialisation(user: User) -> str` — `f'{settings.BASE_URL}/reinitialisation/{urlsafe_base64_encode(force_bytes(user.pk))}/{default_token_generator.make_token(user)}'`.
- Produces : `POST /api/core/mot-de-passe/oubli/` (nom `core_mot_de_passe_oubli`), corps `{identifiant}` → toujours `200 {detail: MESSAGE_DEMANDE}`.
- Produces : `core.throttles.OubliRateThrottle(ParChampRateThrottle)`, `champ='identifiant'`, `prefixe='oubli'`.

- [ ] **Step 1 : réglages dans `settings.py`**

```python
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_BACKEND = ('django.core.mail.backends.smtp.EmailBackend' if EMAIL_HOST
                 else 'django.core.mail.backends.console.EmailBackend')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='UCCB ERP <ne-pas-repondre@uccb.local>')
PASSWORD_RESET_TIMEOUT = 3600
```

- [ ] **Step 2 : écrire `core/tests/test_mot_de_passe.py::DemandeTests`** (Django remplace l'envoi par `mail.outbox` en test ; `cache.clear()` dans `setUp` pour remettre les throttles à zéro ; classe décorée `@override_settings(BASE_URL='http://testserver-erp')`)

```python
def test_par_identifiant_un_email_avec_lien(self):
    r = self.demander('  Divine.Moukala ')
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.data, {'detail': "Si un compte correspond, un e-mail contenant un lien vient d'être envoyé."})
    self.assertEqual(len(mail.outbox), 1)
    self.assertEqual(mail.outbox[0].to, ['divine@example.org'])
    self.assertRegex(mail.outbox[0].body, r'http://testserver-erp/reinitialisation/\w+/[\w-]+')   # BASE_URL surchargé
def test_par_email_casse_differente(self):            # 'DIVINE@Example.org' → 1 e-mail
def test_identifiant_prioritaire_sur_email(self):     # User username='x@ex.org' et Personne(email='x@ex.org') d'un autre → e-mail au premier, 1 seul
def test_cas_sans_envoi_meme_reponse(self):           # inconnu, is_active=False, personne suspendue, sans adresse → 200, même corps, outbox vide
def test_panne_smtp_reponse_neutre(self):             # patch core.api.mot_de_passe.send_mail side_effect=SMTPException → 200, même corps
def test_journal_a_chaque_envoi(self):                # JournalAudit(module='core', action='demande_reinitialisation')
```

- [ ] **Step 3 : lancer** `manage.py test core.tests.test_mot_de_passe` — attendu : échecs.
- [ ] **Step 4 : implémenter `DemandeReinitialisationView(APIView)`** dans `core/api/mot_de_passe.py` : `authentication_classes = []`, `permission_classes = []`, throttles `[OubliRateThrottle, LoginIPRateThrottle]`. Envoi si compte actif, personne non suspendue (`personne_suspendue(user) is None`) et `adresse_de(user)`. `send_mail(sujet, corps, None, [adresse])` dans un `try/except Exception` qui journalise via `logging.getLogger(__name__).exception`. Sujet et corps exacts :

```text
Sujet : UCCB — Réinitialisation de votre mot de passe
Bonjour {nom_complet(user)},

Pour choisir un nouveau mot de passe, ouvrez ce lien (valable 1 heure) :
{lien_reinitialisation(user)}

Si vous n'avez rien demandé, ignorez ce message.
```

- [ ] **Step 5 : lancer les tests** — attendu : tout passe.
- [ ] **Step 6 : configuration et doc** — ajouter les 6 variables `EMAIL_*` / `DEFAULT_FROM_EMAIL` (commentées, sans valeur réelle) à `erp/.env.example` et `erp/backend/.env.example` ; section « Envoi des e-mails » dans `erp/docker/README.md` (sans `EMAIL_HOST`, les e-mails s'affichent dans `docker compose logs web`) ; `BASE_URL: http://localhost:5180` dans l'`environment` de `web` de `docker-compose.dev.yml`.
- [ ] **Step 7 : commit** `feat(core): demande de réinitialisation du mot de passe par e-mail`

### Task 3 : Choix du nouveau mot de passe

**Files :**
- Modify : `erp/backend/core/api/mot_de_passe.py`, `erp/backend/core/urls.py` (route `mot-de-passe/reinitialisation/`)
- Modify : `erp/backend/core/tests/test_mot_de_passe.py`

**Interfaces :**
- Consumes : `lien_reinitialisation(user)` (Task 2).
- Produces : `POST /api/core/mot-de-passe/reinitialisation/` (nom `core_mot_de_passe_reinitialisation`), corps `{uid, jeton, password}` → `200 {detail: MESSAGE_SUCCES}` ; `400 {detail: MESSAGE_LIEN_INVALIDE}` ; `400 {password: [...]}`.
- Produces : `deconnecter_partout(user: User) -> None` — `BlacklistedToken.objects.get_or_create(token=t)` pour chaque `OutstandingToken` du compte non encore blacklisté.

- [ ] **Step 1 : écrire `ReinitialisationTests`**

```python
def test_succes_puis_connexion(self):            # 200, message exact, connexion avec le nouveau mot de passe OK
def test_lien_utilise_deux_fois(self):           # 2e appel → 400 {'detail': "Ce lien n'est plus valable. Faites une nouvelle demande."}
def test_lien_apres_reconnexion(self):           # connexion via /api/core/token/ entre la demande et l'usage → 400 lien invalide
def test_lien_expire(self):                      # override_settings(PASSWORD_RESET_TIMEOUT=0) + jeton d'avant → 400
def test_uid_invalide(self):                     # uid='zz' → 400 lien invalide
def test_mot_de_passe_faible(self):              # '123' → 400 avec 'password', mot de passe inchangé
def test_sessions_fermees(self):                 # refresh obtenu avant → /api/core/token/refresh/ renvoie 401 après succès
def test_journal(self):                          # JournalAudit(action='reinitialisation_mot_de_passe')
```

- [ ] **Step 2 : lancer** — attendu : échecs.
- [ ] **Step 3 : implémenter `ReinitialisationView(APIView)`** — `authentication_classes = []`, `permission_classes = []`, throttle `[LoginIPRateThrottle]`. Décoder `uid` (`urlsafe_base64_decode`, erreurs → lien invalide), vérifier avec `default_token_generator.check_token`, valider avec `validate_password(password, user)`, `set_password`, `save`, `deconnecter_partout(user)`, audit.
- [ ] **Step 4 : lancer** `manage.py test core` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(core): choix d'un nouveau mot de passe depuis le lien`

### Task 4 : Pages « mot de passe oublié » et « nouveau mot de passe »

**Files :**
- Create : `erp/frontend/src/features/auth/MotDePasseOubliePage.jsx` (+ `.test.jsx`)
- Create : `erp/frontend/src/features/auth/ReinitialisationPage.jsx` (+ `.test.jsx`)
- Modify : `erp/frontend/src/app/router.jsx` (routes publiques `/mot-de-passe-oublie`, `/reinitialisation/:uid/:jeton`)
- Modify : `erp/frontend/src/features/auth/LoginPage.jsx` (lignes 351-356)

**Interfaces :**
- Consumes : les deux endpoints des Tasks 2 et 3, via `apiClient.post('/core/mot-de-passe/oubli/', {identifiant})` et `apiClient.post('/core/mot-de-passe/reinitialisation/', {uid, jeton, password})`.
- Consumes : `noterMessageConnexion(message)` (`@/lib/messageConnexion`), `erreursServeur(e, champs)` (`@/lib/erreurs`).

- [ ] **Step 1 : écrire les tests Vitest** (même montage que `ActivationPage.test.jsx`, `apiClient` mocké)

```js
it('envoie l’identifiant et affiche le message neutre', …)
// saisie 'divine' dans « Identifiant ou e-mail », clic « Envoyer le lien »
// → post('/core/mot-de-passe/oubli/', { identifiant: 'divine' }) ; texte « Si un compte correspond… » ; lien « Retour à la connexion »
it('réinitialise puis renvoie à la connexion avec le message', …)
// route /reinitialisation/MQ/abc-123 ; « Nouveau mot de passe » + « Confirmer » ; clic « Enregistrer »
// → post('/core/mot-de-passe/reinitialisation/', { uid: 'MQ', jeton: 'abc-123', password }) ; page /login ; lireMessageConnexion() === 'Mot de passe modifié. Connectez-vous.'
it('lien invalide : message et lien vers une nouvelle demande', …)   // mock 400 detail → texte affiché, lien href '/mot-de-passe-oublie'
it('confirmation différente : erreur, aucun appel', …)
```

- [ ] **Step 2 : lancer** — attendu : échecs (modules absents).
- [ ] **Step 3 : implémenter les deux pages** dans la charte d'`ActivationPage` (réutiliser son composant `Ligne` en l'exportant, ou l'extraire dans `features/auth/Ligne.jsx` si deux pages l'importent). Mot de passe : même aide « Au moins 8 caractères, pas uniquement des chiffres. »
- [ ] **Step 4 : `LoginPage.jsx`** — remplacer « Mot de passe oublié ? Contactez l'administration. » par un `Link` « Mot de passe oublié ? » vers `/mot-de-passe-oublie` ; « Étudiant, première connexion ? » devient « Première connexion ? ».
- [ ] **Step 5 : lancer** `npx vitest run src/features/auth` — attendu : tout passe.
- [ ] **Step 6 : commit** `feat(frontend): pages mot de passe oublié et nouveau mot de passe`

### Task 5 : Arrivée directe dans « Mon espace »

**Files :**
- Modify : `erp/frontend/src/app/modules.js`, `erp/frontend/src/app/Lanceur.jsx`, `erp/frontend/src/app/ModuleShell.jsx:72-81`
- Modify : `erp/frontend/src/app/Lanceur.test.jsx`, `erp/frontend/src/modules/moi/MoiShell.test.jsx`

**Interfaces :**
- Produces : `espacePersonnelSeul(user) -> boolean` dans `app/modules.js` — `modulesVisibles(user).length === 0` et `user.roles` contient `etudiant` ou `enseignant`.

- [ ] **Step 1 : écrire les tests**

```js
// Lanceur.test.jsx — rendre avec <Routes> : '/' → <Lanceur/>, '/moi' → <p>Mon espace</p>
it('redirige vers /moi un étudiant sans module', …)            // connecter([], ['etudiant']) → texte « Mon espace »
it('garde le lanceur pour un enseignant avec un module', …)    // connecter([{ code: 'edt', … }], ['enseignant', 'chef_departement']) → tuile EDT visible
// MoiShell.test.jsx
it('masque « Tous les modules » sans autre module', …)         // roles ['etudiant'], modules [] → queryByRole('link', { name: 'Retour aux modules' }) absent
it('montre « Tous les modules » avec un module', …)
```

- [ ] **Step 2 : lancer** — attendu : échecs.
- [ ] **Step 3 : implémenter** — `Lanceur` rend `<Navigate to="/moi" replace />` quand `espacePersonnelSeul(user)` ; `ModuleShell` n'affiche le lien « Tous les modules » que si `!espacePersonnelSeul(user)`.
- [ ] **Step 4 : lancer** `npx vitest run` (toute la suite) — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(frontend): arrivée directe dans Mon espace sans module`

### Task 6 : Vérification de bout en bout

- [ ] **Step 1 :** suites complètes — `manage.py test core edt scolarite rh finance logistique` et `npx vitest run` : tout passe.
- [ ] **Step 2 :** pile de dev redémarrée (`up -d` pour prendre `BASE_URL`). Dans le navigateur sur `http://localhost:5180` :
  - activer un enseignant de démo sans compte (créer sa fiche dans RH si aucune n'est libre), se connecter avec son matricule → arrivée sur `/moi/planning` ;
  - « Mot de passe oublié ? » avec cet identifiant → lien lu dans `docker compose logs web`, ouvert → nouveau mot de passe → connexion OK, et le lien rouvert est refusé ;
  - `admin` arrive toujours sur le lanceur.
- [ ] **Step 3 :** commit des éventuels correctifs.
