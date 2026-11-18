/** Mise en forme des notes et résultats. */
export const note = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2).replace('.', ','));

export const couleurDecision = (decision) => (decision === 'ADMIS'
  ? 'bg-primary/10 text-primary' : 'bg-destructive/10 text-destructive');

export const STATUTS_ETUDIANT = [
  { valeur: 'actif', libelle: 'Actif' },
  { valeur: 'diplome', libelle: 'Diplômé' },
  { valeur: 'abandonne', libelle: 'Abandonné' },
];

export const optionsClasses = (classes = []) => classes.map((c) => ({ valeur: String(c.id), libelle: c.libelle }));
