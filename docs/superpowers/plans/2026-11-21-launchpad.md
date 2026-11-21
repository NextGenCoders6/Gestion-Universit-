# Launchpad de l'ERP — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** remplacer le lanceur décoratif par un launchpad au style SAP Fiori : tuiles sobres portant un chiffre vivant par module, accès rapides, toile sauge, servis par `GET /api/core/lanceur/`.

**Architecture :** `core/lanceur.py` tient un registre `{code_module: resume(request) -> dict}` ; chaque app enregistre son résumé dans `AppConfig.ready()` (même schéma que `ROLES_CONTEXTUELS`). La vue `LanceurView` appelle les résumés des modules accessibles et isole les erreurs. RH, Finance, Logistique réutilisent le calcul de leur tableau de bord, extrait en fonction. Le frontend réécrit `app/Lanceur.jsx` avec `TuileModule` et `AccesRapides`.

**Tech Stack :** Django 5.2, DRF ; React 18, TanStack Query, Tailwind, Vitest 4.

**Spec :** `docs/superpowers/specs/2026-11-21-launchpad-design.md`

## Global Constraints

- Entrée de réponse : `{ "module", "valeur": number|null, "unite": str, "libelle": str, "detail": str, "ton": "normal"|"alerte" }`.
- Un module non accessible n'apparaît pas ; un résumé qui lève → `{ "module": code, "valeur": null, "unite": "", "libelle": "", "detail": "", "ton": "normal" }` + `logger.exception`, réponse 200.
- Chiffres calculés dans le périmètre : `scolarite.perimetre.restreindre_par_faculte`, `edt.perimetre.classes_autorisees`.
- Plus de bandeau, bandes de couleur, pastilles teintées ni phrases descriptives sur le lanceur ; couleur du module seulement sur l'icône 20 px des tuiles.
- Tuile : carré `11rem` (bureau), coins `rounded-md`, une seule taille ; au moins 2 colonnes à 375 px.
- Toile : `CANVAS_MON_ESPACE` (`105 12% 93%`) posée sur le lanceur.

**Tests :** depuis `erp/`, pile de dev démarrée —
`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T -e DB_ENGINE=sqlite web python manage.py test <cible>`
`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npx vitest run <fichier>`

## Review Focus

1. Utilisateur Scolarité rattaché à une faculté : le chiffre ne compte que les étudiants de sa faculté.
2. Chef de département (EDT niveau `perimetre`) : séances de ses classes seulement ; personne sans droit EDT : pas de tuile EDT.
3. Finance sans frais attendus sur l'année : `valeur: null`, détail « Aucun frais attendu » (le tableau de bord, lui, renvoie 0,0).
4. Un résumé qui lève une exception : entrée sans chiffre, les autres modules présents, réponse 200.
5. Accès rapides : `finance_utilisateur` voit « Frais étudiants » mais pas « Saisie des notes » (niveau `faculte`).

Tests : 1 et 2 en Task 2, 3 en Task 3, 4 en Task 1, 5 en Task 4.

---

### Task 1 : Registre, endpoint et résumé Paramètres

**Files :**
- Create : `erp/backend/core/lanceur.py`, `erp/backend/core/api/lanceur.py`, `erp/backend/core/tests/test_lanceur.py`
- Modify : `erp/backend/core/urls.py` (`path('lanceur/', LanceurView.as_view(), name='core_lanceur')`), `erp/backend/core/apps.py` (enregistrer `parametres`)

**Interfaces :**
- Produces : `core.lanceur.RESUMES: dict[str, Callable[[Request], dict]]` ; `enregistrer(code: str, fonction) -> None` (idempotent) ; `entree(module, valeur=None, unite='', libelle='', detail='', ton='normal') -> dict` (construit une entrée de réponse) ; `resumes_pour(request) -> list[dict]` (ordre de `modules_accessibles`, modules sans résumé enregistré ignorés).
- Produces : `GET /api/core/lanceur/` → `resumes_pour(request)`.
- Résumé `parametres` (dans `core/lanceur.py`, `resume_parametres(request)`) : `valeur` = `User.objects.filter(is_active=True).count()`, `libelle` « comptes actifs », `detail` « Année en cours : 2026-2027 » ou « Aucune année en cours » (`ton: "alerte"`).

- [ ] **Step 1 : tests** (`core/tests/test_lanceur.py`, `APIClient` authentifié, cache vidé)

```python
def test_reserve_aux_modules_accessibles(self):      # compte avec droit parametres seulement → [e['module'] for e in r.data] == ['parametres']
def test_parametres(self):                          # annee(en_cours=True) → valeur = nb comptes actifs, detail 'Année en cours : 2026-2027', ton 'normal'
def test_parametres_sans_annee_courante(self):      # → detail 'Aucune année en cours', ton 'alerte'
def test_resume_en_erreur_isole(self):              # patch.dict(RESUMES, {'parametres': lève RuntimeError}) + superuser → 200,
                                                    # entrée parametres == entree('parametres'), assertLogs('core.lanceur', 'ERROR')
def test_anonyme_refuse(self):                      # 401
```

- [ ] **Step 2 : lancer** `core.tests.test_lanceur` — attendu : échec (404 / import).
- [ ] **Step 3 : implémenter** registre, vue (permissions par défaut), route, enregistrement `parametres` dans `CoreConfig.ready()`.
- [ ] **Step 4 : lancer** `core` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(core): endpoint du launchpad et résumé Paramètres`

### Task 2 : Résumés Scolarité et Emploi du temps

**Files :**
- Create : `erp/backend/scolarite/lanceur.py`, `erp/backend/edt/lanceur.py`, `erp/backend/scolarite/tests/test_lanceur.py`, `erp/backend/edt/tests/test_lanceur.py`
- Modify : `erp/backend/scolarite/apps.py`, `erp/backend/edt/apps.py` (`enregistrer(...)` dans `ready()`)

**Interfaces :**
- Consumes : `enregistrer`, `entree` (Task 1).
- `scolarite.lanceur.resume(request)` : `Inscription` de `AnneeAcademique.courante()`, `statut='active'`, restreintes par `restreindre_par_faculte(qs, request.user, prefixe='classe__')` ; `libelle` « étudiants inscrits », `detail` « Année 2026-2027 » ; sans année courante : `valeur: None`, `detail` « Aucune année en cours ».
- `edt.lanceur.resume(request)` : semaine `lundi → dimanche` de `timezone.localdate()` ; `Seance.objects.filter(q_jour_effectif(debut, fin))`, restreintes par `filtrer_par_classes(qs, classes_autorisees(request.user))` ; `valeur` = statut `Confirmée`/`Reportée`, `libelle` « séances cette semaine » ; `detail` « N brouillons à publier » (statut `brouillon`, même périmètre ; « Aucun brouillon » si 0).

- [ ] **Step 1 : tests** (fabriques `scolarite.tests.fabriques.Monde`/`inscrit`, `scolarite.tests.api.compte`, `edt.tests.fabriques`)

```python
# scolarite
def test_compte_les_inscrits_actifs_de_l_annee(self)   # 2 inscrits actifs + 1 abandonnée → valeur 2, detail 'Année 2026-2027'
def test_perimetre_faculte(self)                       # compte scolarite_secretariat rattaché à une 2e faculté sans inscrits → valeur 0
def test_sans_annee_courante(self)                     # → valeur None, detail 'Aucune année en cours'
# edt (dates fixées par patch de timezone.localdate → 2026-11-19)
def test_seances_de_la_semaine(self)                   # 2 Confirmée dans la semaine, 1 la semaine suivante, 1 brouillon → valeur 2, detail '1 brouillon à publier'
def test_perimetre_chef(self)                          # chef de département INFO : séances d'une classe hors département non comptées
def test_sans_droit_edt_pas_de_tuile(self)             # GET /api/core/lanceur/ pour un compte sans droit EDT → 'edt' absent
```

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter** (accord : « 1 brouillon à publier », « N brouillons à publier »).
- [ ] **Step 4 : lancer** `scolarite edt core` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(scolarite,edt): résumés du launchpad`

### Task 3 : Résumés RH, Finance, Logistique (calculs partagés avec les tableaux de bord)

**Files :**
- Create : `erp/backend/finance/tableau.py`, `erp/backend/finance/lanceur.py`, `erp/backend/rh/lanceur.py`, `erp/backend/logistique/lanceur.py` + un `tests/test_lanceur.py` par app
- Modify : `erp/backend/finance/views.py:281-320` (la vue appelle `indicateurs_frais`), `erp/backend/{rh,finance,logistique}/apps.py`

**Interfaces :**
- Produces : `finance.tableau.indicateurs_frais(annee) -> dict` avec clés `frais_attendus`, `frais_encaisses` (Decimal), `taux_recouvrement` (float|None : `None` si rien d'attendu), `dossiers`, `dossiers_en_retard`, `montant_en_retard`, `dossiers_sans_tarif`, `trop_percus`, `montant_trop_percu` — `TableauDeBordView` garde sa réponse actuelle (`taux_recouvrement` → `0.0` quand `None`).
- `finance.lanceur.resume(request)` : `valeur` = taux arrondi à 0,1, `unite` « % », `libelle` « des frais encaissés », `detail` « N dossiers en retard » / « Aucun dossier en retard », `ton` alerte si retard > 0 ; taux `None` → `valeur: None`, `detail` « Aucun frais attendu ».
- `rh.lanceur.resume(request)` : `valeur` = `contrats_a_echeance(30).count()`, `libelle` « contrats à échéance », `detail` « N vacations à confirmer » (même calcul que la vue : `lignes_vacations(_Requete(request, 'a_confirmer'), affectations_de_vacataires(request))`), `ton` alerte si valeur > 0.
- `logistique.lanceur.resume(request)` : `valeur` = `Bus.objects.filter(statut='actif').count()`, `libelle` « bus en service », `detail` « N alertes » / « Aucune alerte » (`service.alertes(timezone.localdate())`, même import que la vue), `ton` alerte si alertes.

- [ ] **Step 1 : tests**

```python
def test_finance_taux_et_retards(self)        # dossiers attendus 1 500 000, encaissés 300 000 → valeur 20.0, unite '%'
def test_finance_sans_frais_attendus(self)    # aucun dossier → valeur None, detail 'Aucun frais attendu', ton 'normal'
def test_rh_contrats_a_echeance(self)         # 1 contrat finissant dans 10 jours → valeur 1, ton 'alerte'
def test_logistique_bus_actifs(self)          # 2 actifs + 1 maintenance → valeur 2
```

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter** ; extraire `indicateurs_frais` sans changer la réponse du tableau de bord Finance.
- [ ] **Step 4 : lancer** `core edt scolarite rh finance logistique` — attendu : tout passe (dont les tests existants des tableaux de bord).
- [ ] **Step 5 : commit** `feat(rh,finance,logistique): résumés du launchpad`

### Task 4 : Launchpad dans l'interface

**Files :**
- Create : `erp/frontend/src/app/lanceur/TuileModule.jsx`, `AccesRapides.jsx`, `erp/frontend/src/api/lanceur.js`
- Modify : `erp/frontend/src/app/Lanceur.jsx` (réécriture), `erp/frontend/src/app/modules.js` (`rapide: true` sur : scolarite `saisie`, edt `seances`, rh `vacations`, finance `frais`, logistique `affectations`, parametres `utilisateurs`), `erp/frontend/src/app/Lanceur.test.jsx`

**Interfaces :**
- Consumes : `GET /api/core/lanceur/` (Tasks 1-3) ; `modulesVisibles`, `menuVisible`, `espacePersonnelSeul`, `CANVAS_MON_ESPACE` ; `dateLongue` (`lib/dates`).
- Produces : `lireLanceur() -> Promise<Entree[]>` (`apiClient.get('/core/lanceur/')`).
- Produces : `TuileModule({ titre, sousTitre, valeur, unite, detail, ton, icone, couleur, to, chargement })` ; `AccesRapides({ liens: { libelle, to }[] })`.

Tuile : `<Link>` carré `size-[11rem]` (≈ `size-[9.5rem]` sous `sm`), `rounded-md border bg-card` ; titre 14 px gras ; sous-titre 12 px `text-muted-foreground` ; valeur `text-[28px]` + unité `text-sm` ; détail 12 px ; `ton="alerte"` → valeur et détail `text-warning` ; icône `size-5` avec `style={{ color: hsl(couleur) }}` ; chargement → `…` ; `valeur == null` → `—`. Barre du haut `h-14 bg-card border-b` : logo, « UCCB · ERP », `dateLongue(new Date())`, `MenuUtilisateur`. Groupes : « Mon espace » (si rôle, une tuile « Mon espace », sous-titre « Planning, notes, documents », sans chiffre), « Modules », puis « Accès rapides ».

- [ ] **Step 1 : tests** (`Lanceur.test.jsx` : `vi.mock('@/api/lanceur')`, `QueryClientProvider`)

```js
it('affiche une tuile par module autorisé, avec chiffre, unité et détail', …)
// modules finance + rh ; réponse [{module:'finance', valeur:26.9, unite:'%', libelle:'des frais encaissés', detail:'24 dossiers en retard', ton:'alerte'}, {module:'rh', valeur:0, …}]
// → lien name /Finance/ href '/finance' contient '26,9' et '%' et '24 dossiers en retard' ; queryByRole('link', { name: /Logistique/ }) null
it('ton alerte en couleur d’avertissement', …)            // élément '26,9' a la classe 'text-warning'
it('valeur nulle ou erreur : tuile sans chiffre, lien actif', …)   // lireLanceur rejette → '—' et href '/finance'
it('accès rapides filtrés par niveau', …)                 // finance niveaux ['utilisateur'] + scolarite ['secretariat'] → lien 'Frais étudiants' présent, 'Saisie des notes' absent
it('tuile Mon espace pour un enseignant chef de département', …)   // roles ['enseignant','chef_departement'], module edt → lien 'Mon espace' href '/moi'
it('plus de bandeau ni de descriptions', …)               // queryByText('Inscriptions, notes, délibérations, documents officiels.') null ; pas de heading /Bonjour/
// conserver : état vide sans module ; redirection /moi d'un étudiant sans module
```

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter** ; retirer du registre les `description` devenues inutiles seulement si plus rien ne les lit (sinon les laisser).
- [ ] **Step 4 : lancer** `npx vitest run` et `npx eslint src` — attendu : tout passe.
- [ ] **Step 5 : contrôle visuel** `http://localhost:5180`, comptes `admin`, `finance_utilisateur`, `chef` ; 1280 px et 375 px.
- [ ] **Step 6 : commit** `feat(frontend): launchpad au style SAP Fiori`
