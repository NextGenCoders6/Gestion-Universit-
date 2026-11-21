# Accueil de « Mon espace » — Conception courte

Date : 2026-11-21
Statut : validé par l'utilisateur le 2026-11-21

## Intention

Donner à « Mon espace » (étudiant et enseignant) l'esprit du shot Dribbble « Classroom: Faculty Workspace & Student
Portal » choisi par l'utilisateur : calme, vert sauge, un accueil qui résume l'essentiel, lisible sur téléphone.
Aujourd'hui l'étudiant arrive sur « Mes notes » et l'enseignant sur « Mon planning », sans vue d'ensemble.

## Objectifs, non-objectifs, anti-objectifs

- **Objectifs** : une page « Accueil » en tête du menu de « Mon espace », ouverte par défaut, pour chaque rôle ;
  fond vert sauge propre à « Mon espace » ; disposition adaptée au téléphone.
- **Non-objectifs** : modifier le contenu des pages existantes (notes, planning, frais, enseignements, documents) ;
  ajouter des endpoints ; changer le thème des autres modules.
- **Anti-objectifs** : mélanger deux styles dans l'ERP (la sauge reste confinée à « Mon espace ») ; recopier la
  maquette Dribbble (on reprend les principes, pas les écrans) ; un chiffre faux ou trompeur quand une donnée manque
  (afficher « — » et un texte clair).

## Approches

Une seule raisonnable : page React construite sur les endpoints existants (`/api/scolarite/moi/…`,
`/api/edt/moi/…`) et les composants partagés (`Indicateur`, `.carte`, `PageHeader`). Écartées : un endpoint
« tableau de bord » dédié (travail serveur inutile, les données existent déjà) ; un nouveau thème global (contraire
à l'anti-objectif).

## Conception

- **En-tête** : salutation selon l'heure (« Bonjour » / « Bonsoir ») + `nom_complet`, date du jour en toutes lettres
  (même logique que le lanceur, factorisée).
- **Étudiant** — 4 indicateurs : moyenne du dernier semestre délibéré (`/20`, détail : décision) ; heures de cours
  de la semaine en cours ; reste à payer (dossier de l'année en cours) ; prochaine échéance (montant restant, date
  limite ; « Une mensualité en retard » en ton danger si `en_retard`). 2 listes : « Prochains cours » (5 prochaines
  séances des 14 jours à venir : jour, heure, EC, enseignant) → lien `/moi/planning` ; « Mes enseignants » (nom,
  grade, EC) → lien `/moi/enseignants`.
- **Enseignant** — 4 indicateurs : heures de la semaine en cours ; heures faites / prévues (toutes affectations) ;
  nombre de classes distinctes ; documents déposés. 2 listes : « Prochaines séances » (5 prochaines sur 14 jours :
  jour, heure, EC, classe) → `/moi/planning` ; « Avancement » (une ligne par affectation avec la barre
  `BarreAvancement` existante) → `/moi/enseignements`.
- **Couleurs** : `--canvas` sauge clair dans « Mon espace » seulement (`hsl(105 12% 93%)`, proche de `#E4E8E3`
  éclairci), via le style du module ; cartes blanches inchangées ; accent `COULEUR_MON_ESPACE` inchangé.
- **Mobile** : indicateurs en 2 colonnes sous 768 px (4 au-delà), listes en 1 colonne (2 au-delà).
- **États** : chargement (squelettes), liste vide (« Aucun cours dans les 14 prochains jours. »), erreur d'une
  source (message dans la carte concernée, les autres restent affichées).

## Laissé au builder

Découpage des composants, textes exacts dans l'esprit ci-dessus, teinte exacte de la sauge (contraste AA du texte
`muted-foreground` sur le fond à conserver).
