# Accueil de « Mon espace » — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal :** une page « Accueil » ouverte par défaut dans « Mon espace », pour l'étudiant et pour l'enseignant, sur fond vert sauge.

**Architecture :** frontend seul. Les calculs (salutation, semaine, heures, prochaines séances, dernier résultat) sont des fonctions pures testées à part ; deux pages React les combinent avec les endpoints existants de `modules/moi/api.js` et les composants partagés `Indicateur`, `PageHeader`, `.carte`, `BarreAvancement`.

**Tech Stack :** React 18, react-router 6, TanStack Query, Tailwind, Vitest 4 + Testing Library.

**Spec :** `docs/superpowers/specs/2026-11-21-accueil-mon-espace-design.md`

## Global Constraints

- Aucun endpoint nouveau ; aucune modification des pages existantes de « Mon espace ».
- Sauge confinée à « Mon espace » : `--canvas: 105 12% 93%` posé par le style du module, rien dans `index.css` global.
- Donnée absente → valeur `—` et un détail en clair, jamais un `0` trompeur.
- Grilles : indicateurs `grid-cols-2 lg:grid-cols-4`, listes `grid-cols-1 lg:grid-cols-2`.
- 5 prochaines séances, sur les 14 jours à venir.

**Lancer les tests** (depuis `erp/`, pile de dev démarrée) :
`docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T frontend npx vitest run <fichier>`

## Review Focus

1. Résultats masqués (`resultats_masques: true`, frais impayés) : l'accueil ne montre pas la moyenne, il affiche `message_resultats`.
2. Aucun semestre délibéré, ou aucun dossier de frais : indicateurs à `—` avec un détail clair.
3. Séance reportée : tri et heure d'après `creneau_effectif`, pas `date_seance`.
4. Une source en erreur (frais en 500) : les autres cartes restent affichées, la carte concernée dit que la donnée est indisponible.
5. Fin de journée : une séance terminée aujourd'hui n'apparaît plus dans « Prochains cours ».

Chaque point a son test : 1, 2, 3, 5 en Task 1 (fonctions pures) et 1, 4 en Task 2.

---

### Task 1 : Calculs de l'accueil

**Files :**
- Create : `erp/frontend/src/lib/dates.js` (+ `dates.test.js`)
- Create : `erp/frontend/src/modules/moi/accueil/calculs.js` (+ `calculs.test.js`)
- Modify : `erp/frontend/src/app/Lanceur.jsx:31-39` (supprimer `dateDuJour` et `salutation` locales, importer celles de `lib/dates.js`)

**Interfaces :**
- Produces (`lib/dates.js`) :
  - `salutation(date: Date) -> 'Bonjour' | 'Bonsoir'` — `Bonsoir` à partir de 18 h.
  - `dateLongue(date: Date) -> string` — `Intl` `fr-FR` weekday/day/month/year, première lettre en capitale (logique actuelle du lanceur).
  - `enIso(date: Date) -> 'YYYY-MM-DD'` en heure locale.
  - `bornesSemaine(date: Date) -> { debut: string, fin: string }` — lundi et dimanche de la semaine de `date`, en ISO local.
- Produces (`modules/moi/accueil/calculs.js`) :
  - `debutFin(seance) -> { debut: Date, fin: Date }` — d'après `seance.creneau_effectif` (`jour`, `debut`, `fin`), à défaut `date_seance`/`heure_debut`/`heure_fin`.
  - `heuresSeances(seances: Seance[]) -> number` — somme des durées, en heures, arrondie à 0,5.
  - `prochainesSeances(seances, maintenant: Date, n = 5) -> Seance[]` — séances dont la fin est après `maintenant`, triées par début.
  - `dernierResultat(notes) -> { semestre, moyenne, decision } | { masque: string } | null` — inscription la plus récente ; si `resultats_masques`, `{ masque: message_resultats }` ; sinon dernier semestre `deliberee` avec `resultat`.
  - `dossierCourant(frais: Dossier[]) -> Dossier | null` — dossier dont `inscription_statut === 'active'`, à défaut le premier.
  - `bilanEnseignements(affectations) -> { faites: number, prevues: number, classes: number }` — `classes` = nombre de `classe` distincts.

- [ ] **Step 1 : tests** (`dates.test.js`, `calculs.test.js`)

```js
expect(salutation(new Date(2026, 10, 21, 17, 59))).toBe('Bonjour');
expect(salutation(new Date(2026, 10, 21, 18, 0))).toBe('Bonsoir');
expect(dateLongue(new Date(2026, 10, 21))).toBe('Samedi 21 novembre 2026');
expect(bornesSemaine(new Date(2026, 10, 19))).toEqual({ debut: '2026-11-16', fin: '2026-11-22' });
expect(bornesSemaine(new Date(2026, 10, 22))).toEqual({ debut: '2026-11-16', fin: '2026-11-22' }); // dimanche

const s = (jour, debut, fin, extra = {}) => ({ id: `${jour}${debut}`, creneau_effectif: { jour, debut, fin }, ...extra });
expect(heuresSeances([s('2026-11-16', '09:00', '11:00'), s('2026-11-17', '14:00', '15:30')])).toBe(3.5);
// séance reportée : date_seance ancienne, créneau effectif futur → retenue et triée sur le créneau
const reportee = s('2026-11-25', '08:00', '10:00', { date_seance: '2026-11-18', heure_debut: '08:00', heure_fin: '10:00' });
expect(prochainesSeances([s('2026-11-24', '09:00', '11:00'), reportee], new Date(2026, 10, 21)).map((x) => x.id))
  .toEqual(['2026-11-2409:00', '2026-11-2508:00']);
// terminée aujourd'hui → exclue ; en cours → gardée
expect(prochainesSeances([s('2026-11-21', '08:00', '10:00'), s('2026-11-21', '10:00', '12:00')], new Date(2026, 10, 21, 11)).length).toBe(1);
expect(prochainesSeances(Array.from({ length: 8 }, (_, i) => s(`2026-11-2${i + 2}`, '09:00', '10:00')), new Date(2026, 10, 21)).length).toBe(5);

expect(dernierResultat({ inscriptions: [] })).toBeNull();
expect(dernierResultat({ inscriptions: [{ resultats_masques: true, message_resultats: 'Réglez vos frais.', semestres: [] }] }))
  .toEqual({ masque: 'Réglez vos frais.' });
expect(dernierResultat({ inscriptions: [{ resultats_masques: false, semestres: [
  { semestre: 'S1', deliberee: true, resultat: { moyenne: 6.98, decision: 'AJOURNÉ' } },
  { semestre: 'S2', deliberee: false, resultat: null }] }] }))
  .toEqual({ semestre: 'S1', moyenne: 6.98, decision: 'AJOURNÉ' });
expect(dernierResultat({ inscriptions: [{ resultats_masques: false, semestres: [{ semestre: 'S1', deliberee: false }] }] })).toBeNull();

expect(dossierCourant([{ id: 1, inscription_statut: 'terminee' }, { id: 2, inscription_statut: 'active' }]).id).toBe(2);
expect(dossierCourant([])).toBeNull();
expect(bilanEnseignements([{ classe: 1, heures_effectuees: 6, heures_prevues: 24 }, { classe: 1, heures_effectuees: 12, heures_prevues: 48 },
  { classe: 3, heures_effectuees: 4, heures_prevues: 4 }])).toEqual({ faites: 22, prevues: 76, classes: 2 });
```

- [ ] **Step 2 : lancer** `src/lib/dates.test.js src/modules/moi/accueil/calculs.test.js` — attendu : échec (modules absents).
- [ ] **Step 3 : implémenter** les deux fichiers ; `Lanceur.jsx` importe `salutation`, `dateLongue` (rendu identique : `dateLongue(new Date())`, `` `${salutation(new Date())}, …` ``).
- [ ] **Step 4 : lancer** ces tests + `src/app/Lanceur.test.jsx` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(frontend): calculs de l'accueil de Mon espace`

### Task 2 : Accueil étudiant

**Files :**
- Create : `erp/frontend/src/modules/moi/accueil/EnTeteAccueil.jsx`, `ListeCarte.jsx`, `AccueilEtudiant.jsx` (+ `AccueilEtudiant.test.jsx`)

**Interfaces :**
- Consumes : Task 1 ; `api.mesNotes()`, `api.monPlanningEtudiant({ date_debut, date_fin })`, `api.mesEnseignants()`, `api.mesFrais()` ; `Indicateur` ; `fcfa`, `dateFr` (`@/modules/finance/lib/format`).
- Produces : `EnTeteAccueil({ nomComplet })` — `<h1>` `` `${salutation(now)}, ${nomComplet}` `` + `dateLongue(now)`.
- Produces : `ListeCarte({ titre, lien, libelleLien = 'Tout voir', vide, erreur, enfants })` — `<section className="carte">` avec titre, lien (`Link`), contenu, ou texte `vide`, ou `erreur` en `role="alert"`.
- Produces : `AccueilEtudiant()` (export par défaut).

Contenu (spec) : indicateurs « Moyenne du dernier semestre » (`6,98 /20`, détail `S1 · AJOURNÉ` ; masqué → `—` + `message_resultats` ; aucun → `—` + `Pas encore de résultat délibéré.`), « Cours cette semaine » (`heuresSeances` sur `bornesSemaine(now)`, `12 h`), « Reste à payer » (`fcfa(reste)` du `dossierCourant`), « Prochaine échéance » (`fcfa(montant - paye)`, détail `avant le 05/01/2027` ; `en_retard` → ton `danger`, détail `Une mensualité en retard`). Listes « Prochains cours » (14 jours, `prochainesSeances`, ligne : jour court + heure, `ec_code — ec_libelle`, `enseignant_nom`, lien `/moi/planning`, vide `Aucun cours dans les 14 prochains jours.`) et « Mes enseignants » (nom, grade, codes des EC, lien `/moi/enseignants`). Erreur d'une requête : `Donnée indisponible pour le moment.` dans l'indicateur ou la carte concernée. Aucun dossier de frais : `—` + `Aucun dossier de frais.` Pendant le chargement : valeur `…` dans les indicateurs, `Chargement…` dans les cartes.

- [ ] **Step 1 : tests** (`vi.mock('../api')`, `QueryClientProvider` retry false, `MemoryRouter`, `vi.setSystemTime(new Date(2026, 10, 19, 9))`, utilisateur `MABIALA Grâce` dans le store)

```js
it('salue, résume notes, cours, frais et enseignants', …)
// attend : heading 'Bonjour, MABIALA Grâce' ; '6,98 /20' ; 'S1 · AJOURNÉ' ; '1 200 000 FCFA' (reste, selon fcfa) ;
// 'avant le 05/01/2027' ; 'ALGO1 — Algorithmique 1' ; 'MBEMBA Christelle' ; liens href '/moi/planning' et '/moi/enseignants'
it('résultats masqués : pas de moyenne, message affiché', …)          // mesNotes masqué → queryByText('6,98 /20') null ; 'Réglez vos frais.'
it('frais en erreur : les autres cartes restent', …)                  // mesFrais rejette → 'Donnée indisponible pour le moment.' ; 'MBEMBA Christelle' visible
it('aucun cours à venir', …)                                          // planning [] → 'Aucun cours dans les 14 prochains jours.'
```

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter** les trois composants.
- [ ] **Step 4 : lancer** `src/modules/moi/accueil` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(frontend): accueil étudiant de Mon espace`

### Task 3 : Accueil enseignant

**Files :**
- Create : `erp/frontend/src/modules/moi/accueil/AccueilEnseignant.jsx` (+ `AccueilEnseignant.test.jsx`)

**Interfaces :**
- Consumes : Task 1, `EnTeteAccueil`, `ListeCarte` (Task 2) ; `api.monPlanning(params)`, `api.mesEnseignements()`, `api.mesDocuments()` ; `BarreAvancement`.
- Produces : `AccueilEnseignant()` (export par défaut).

Contenu (spec) : indicateurs « Cours cette semaine » (heures), « Heures faites » (`22 h / 76 h`), « Classes » (`bilanEnseignements().classes`), « Documents déposés » (nombre). Listes « Prochaines séances » (ligne : jour + heure, `ec_code`, `classe_libelle`, lien `/moi/planning`) et « Avancement » (une ligne par affectation : `ec_code — ec_libelle`, `BarreAvancement` comme `MesEnseignements.jsx`, lien `/moi/enseignements`).

- [ ] **Step 1 : tests**

```js
it('résume séances, heures, classes et documents', …)   // '22 h / 76 h' ; classes '2' ; documents '0' ; 'L1 MIP — 2026-2027' ; lien '/moi/enseignements'
it('aucune séance à venir', …)                          // 'Aucune séance dans les 14 prochains jours.'
```

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer** `src/modules/moi/accueil` — attendu : tout passe.
- [ ] **Step 5 : commit** `feat(frontend): accueil enseignant de Mon espace`

### Task 4 : Branchement dans « Mon espace » et fond sauge

**Files :**
- Modify : `erp/frontend/src/modules/moi/MoiShell.jsx` (entrée `{ chemin: 'accueil', libelle: 'Accueil', icone: Home }` en tête de `MENU_ENSEIGNANT` et `MENU_ETUDIANT` ; l'index redirige déjà vers `menu[0]`)
- Modify : `erp/frontend/src/app/modules.js:135` — `styleModule` pose aussi `--canvas` quand `module.canvas` existe ; `export const CANVAS_MON_ESPACE = '105 12% 93%'`
- Modify : `erp/frontend/src/modules/moi/MoiShell.test.jsx`, et `vi.mock('./api')` y gagne les mêmes fonctions
- Check : `Home` exporté par `@/components/ui/icons` (sinon l'ajouter depuis `lucide-react`, comme les autres)

- [ ] **Step 1 : tests**

```js
it('ouvre l’accueil par défaut pour un étudiant', …)      // rendre('/moi') → heading /Bonjour|Bonsoir/ ; lien 'Accueil' actif
it('ouvre l’accueil par défaut pour un enseignant', …)
// modules.test.js (nouveau) :
expect(styleModule({ couleur: '1 2% 3%', canvas: '105 12% 93%' })).toEqual({ '--module': '1 2% 3%', '--canvas': '105 12% 93%' });
expect(styleModule({ couleur: '1 2% 3%' })).toEqual({ '--module': '1 2% 3%' });
```

Mettre à jour les tests existants de `MoiShell.test.jsx` qui supposaient « Mes notes » / « Mon planning » ouverts sur `/moi` (ils passent par `/moi/notes` ou attendent l'accueil).

- [ ] **Step 2 : lancer** — attendu : échec.
- [ ] **Step 3 : implémenter.**
- [ ] **Step 4 : lancer** toute la suite `npx vitest run` et `npx eslint src` — attendu : tout passe, aucune erreur.
- [ ] **Step 5 : vérification visuelle** dans le navigateur (`http://localhost:5180`, comptes `etudiant` et `enseignant`) : bureau 1280 px et mobile 375 px ; contraste du texte secondaire sur la sauge.
- [ ] **Step 6 : commit** `feat(frontend): accueil par défaut et fond sauge dans Mon espace`
