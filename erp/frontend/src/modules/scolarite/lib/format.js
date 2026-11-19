/** Mise en forme des notes et résultats. */
export const note = (v) => (v === null || v === undefined ? '—' : Number(v).toFixed(2).replace('.', ','));

export const couleurDecision = (decision) => (decision === 'ADMIS'
  ? 'bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300'
  : 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/15 dark:bg-red-500/10 dark:text-red-300');

export const STATUTS_ETUDIANT = [
  { valeur: 'actif', libelle: 'Actif' },
  { valeur: 'diplome', libelle: 'Diplômé' },
  { valeur: 'abandonne', libelle: 'Abandonné' },
];

export const optionsClasses = (classes = []) => classes.map((c) => ({ valeur: String(c.id), libelle: c.libelle }));
