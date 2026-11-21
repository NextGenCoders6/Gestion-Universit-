# Launchpad de l'ERP (écran des modules) — Document de conception

Date : 2026-11-21
Statut : validé par l'utilisateur le 2026-11-21

## 1. Intention

L'écran qui suit la connexion (le « lanceur », `/`) paraît « trop IA » à l'utilisateur : grand bandeau vert foncé
avec un « Bonjour » géant, six cartes identiques avec pastille colorée, bande de couleur, phrase descriptive et lien
« Ouvrir ». C'est décoratif et rien n'y dit ce qui se passe dans l'université.

L'utilisateur a choisi pour modèle le **launchpad de SAP Fiori** : tuiles sobres, de même taille, qui portent un
**chiffre vivant** à la place d'une description, rangées par groupe, avec une ligne d'**accès rapides** en liens
texte. Il a choisi de servir ces chiffres par **un seul appel serveur** (approche A).

Ce lanceur est la première étape de l'extension du style de « Mon espace » (toile vert sauge, cartes blanches) à
toute l'application ; le reste viendra après, une fois ce résultat vu.

## 2. Objectifs, non-objectifs, anti-objectifs

**Objectifs**
- Lanceur au style Fiori : barre du haut fine, tuiles carrées sobres avec chiffre, groupes, accès rapides.
- Un endpoint `GET /api/core/lanceur/` qui renvoie le chiffre de chaque module autorisé, calculé dans le périmètre
  de la personne.
- Toile vert sauge (celle de « Mon espace ») sur le lanceur.
- Lisible sur téléphone : au moins deux tuiles côte à côte.

**Non-objectifs**
- Personnalisation (déplacer, masquer, ajouter des tuiles), recherche d'applications, notifications.
- Graphiques dans les tuiles.
- Restyler les écrans internes des modules (étape suivante).
- Changer la page de connexion.

**Anti-objectifs** (échec même si « ça marche »)
- Un chiffre visible par quelqu'un qui n'a pas le droit de le voir, ou calculé hors de son périmètre (faculté
  rattachée, classes d'un chef de département ou d'un référent).
- Un module en erreur qui empêche l'affichage du lanceur.
- Un lanceur plus lent qu'aujourd'hui : un seul appel, sans calcul lourd.
- Retour des éléments décoratifs : bandeau en dégradé, bandes de couleur, pastilles teintées, phrases descriptives.

## 3. Contraintes

- Stack existante : Django 5.2 / DRF côté serveur ; React 18, TanStack Query, Tailwind côté interface.
- Droits existants : `core.droits.modules_accessibles(user)`, `a_droit` ; périmètres `scolarite.perimetre`
  (faculté rattachée) et `edt.perimetre.classes_autorisees`.
- Les tableaux de bord RH, Finance et Logistique (`*/views.py` `TableauDeBordView`) calculent déjà les valeurs
  utiles ; on ne duplique pas leurs calculs.
- Le registre frontend `app/modules.js` (`REGISTRE`, `menuVisible`) reste la source des modules et des menus.

## 4. Approches envisagées

- **A. Un endpoint unique `/api/core/lanceur/`** (retenue par l'utilisateur) : une requête, droits et périmètres
  vérifiés côté serveur, un module sans droit n'apparaît pas. Coût : écrire les résumés Scolarité, EDT, Paramètres et
  brancher les trois tableaux de bord existants.
- **B. Les tuiles appellent les tableaux de bord existants** : pas de travail serveur pour trois modules, mais six
  requêtes et des refus d'accès à gérer ; écartée.
- **C. Allure Fiori sans chiffres** : rapide, mais perd ce qui rend le modèle vivant ; écartée.

## 5. Conception

### 5.1 Serveur : `GET /api/core/lanceur/`

- Authentifié (permissions par défaut de l'API).
- Mécanisme de registre, comme `core.droits.ROLES_CONTEXTUELS` : `core/lanceur.py` expose `RESUMES = {}` ; chaque
  app enregistre dans son `AppConfig.ready()` une fonction `resume(user) -> dict`. *(choix du concepteur)*
- La vue parcourt `modules_accessibles(user)` dans l'ordre du registre frontend et appelle le résumé de chaque module.
  Un résumé qui lève une exception est journalisé (`logger.exception`) et donne une entrée sans chiffre :
  `{"module": "...", "valeur": null}` ; les autres modules s'affichent.
- Réponse : liste d'objets
  `{ "module": "finance", "valeur": 26.9, "unite": "%", "libelle": "des frais encaissés",
     "detail": "24 dossiers en retard", "ton": "alerte" | "normal" }`.
- Résumés (tous calculés dans le périmètre de l'utilisateur, année académique courante quand elle compte) :

| Module | `valeur` / `unite` / `libelle` | `detail` | `ton` alerte si |
|---|---|---|---|
| scolarite | inscriptions actives de l'année courante, restreintes à la faculté rattachée / — / « étudiants inscrits » | « Année 2026-2027 » ; sans année courante : `valeur: null`, « Aucune année en cours » | jamais |
| edt | séances publiées de la semaine (lundi → dimanche) dans `classes_autorisees(user)` / — / « séances cette semaine » | « N brouillons à publier » (même périmètre) | jamais |
| rh | contrats arrivant à échéance sous 30 jours / — / « contrats à échéance » | « N vacations à confirmer » | valeur > 0 |
| finance | taux de recouvrement de l'année courante / « % » / « des frais encaissés » | « N dossiers en retard » | dossiers en retard > 0 |
| logistique | bus au statut `actif` / — / « bus en service » | « N alertes » (ou « Aucune alerte ») | alertes > 0 |
| parametres | comptes utilisateurs actifs / — / « comptes actifs » | « Année en cours : 2026-2027 » ; sans année courante : « Aucune année en cours » | pas d'année courante |

- RH, Finance, Logistique : extraire le calcul de leur `TableauDeBordView` dans une fonction partagée par la vue et le
  résumé (pas de copie de logique). *(choix du concepteur)*

### 5.2 Interface : `app/Lanceur.jsx`

- **Barre du haut** fine (hauteur 56 px), fond blanc, bordure basse : logo, « UCCB · ERP », date du jour à droite,
  menu utilisateur. Le bandeau vert foncé et le grand « Bonjour » disparaissent.
- **Toile** : `--canvas` vert sauge (`CANVAS_MON_ESPACE`) posé sur le lanceur.
- **Groupe « Mon espace »** (si rôle étudiant ou enseignant) : une tuile « Mon espace » sans chiffre, sous-titre
  « Planning, notes, documents ».
- **Groupe « Modules »** : une tuile par module autorisé, dans l'ordre de `REGISTRE`.
- **Tuile** (une seule taille pour toutes) : carré de 176 px (`11rem`) sur ordinateur, ~ 150 px sur téléphone ;
  carte blanche, bordure fine, coins peu arrondis (6 px), légère ombre au survol ; contenu :
  titre du module (14 px, gras) ; `libelle` en sous-titre (12 px, discret) ; en bas, `valeur` en grand (28 px)
  suivie de `unite`, puis `detail` (12 px). Icône du module, petite (20 px), en haut à droite, dans la couleur du
  module — c'est le seul usage de la couleur du module sur cet écran. `ton: "alerte"` → valeur et détail en couleur
  d'avertissement. Toute la tuile est un lien vers le module.
- **Chargement** : tuiles affichées tout de suite avec `…` à la place du chiffre. **Erreur** de l'endpoint ou
  `valeur: null` : tuile sans chiffre, `—`, le lien reste utilisable.
- **Accès rapides** : sous le groupe « Modules », une ligne de liens texte (titre « Accès rapides »), séparés par
  « · », retour à la ligne entre liens et jamais au milieu d'un lien. Entrées : les éléments de menu marqués
  `rapide: true` dans `REGISTRE`, filtrés par `menuVisible` selon les niveaux de la personne :
  Scolarité « Saisie des notes », EDT « Séances », RH « Vacations », Finance « Frais étudiants »,
  Logistique « Affectations », Paramètres « Utilisateurs et droits ».
- **Grille** : `grid-template-columns: repeat(auto-fill, minmax(…, 1fr))` bornée à la taille de tuile ; au moins
  2 colonnes à 375 px.
- La redirection vers `/moi` d'une personne sans module (déjà en place) est conservée ; l'état vide « Aucun module ne
  vous est attribué » aussi.

## 6. Tests attendus

- Serveur : un test par résumé (valeur, détail, ton) ; périmètre (utilisateur Scolarité rattaché à une faculté ne
  compte que ses étudiants ; chef de département EDT ne compte que ses classes) ; module sans droit absent de la
  réponse ; résumé en erreur → entrée `valeur: null` et les autres présentes ; tableaux de bord RH/Finance/Logistique
  inchangés après extraction (leurs tests existants passent).
- Interface : tuiles rendues depuis la réponse (valeur, unité, détail, lien) ; ton alerte ; état de chargement et
  d'erreur ; accès rapides filtrés par niveau ; tuile « Mon espace » pour un enseignant chef de département ; absence
  du bandeau et des descriptions.
- Contrôle visuel bureau 1280 px et mobile 375 px, comptes `admin`, `finance_utilisateur`, `chef`.

## 7. Choix du concepteur à relire

- Les chiffres retenus par module (tableau 5.1), dont le taux de recouvrement pour la Finance et les comptes actifs
  pour les Paramètres.
- La couleur du module ne subsiste que sur la petite icône des tuiles.
- La toile sauge s'applique au lanceur dès cette étape.
- Finance sans frais attendus sur l'année (taux incalculable) : `valeur: null`, détail « Aucun frais attendu ».
- Pas de salutation : la date et le nom passent dans la barre du haut.

## 8. Laissé au builder

Noms exacts des fonctions extraites des tableaux de bord, découpage des composants React (`TuileModule`,
`AccesRapides`…), libellés exacts dans l'esprit ci-dessus, détail des requêtes (agrégats `count()`), tests de
non-régression des tableaux de bord.
