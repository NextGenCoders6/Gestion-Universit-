export const fcfa = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;
export const dateFr = (d) => (d ? new Date(`${String(d).slice(0, 10)}T00:00:00`).toLocaleDateString('fr-FR') : '—');
export const MODES = [
  { valeur: 'especes', libelle: 'Espèces' }, { valeur: 'mobile_money', libelle: 'Mobile Money' },
  { valeur: 'virement', libelle: 'Virement bancaire' }, { valeur: 'cheque', libelle: 'Chèque' },
];
export const ETATS_ECHEANCE = {
  payee: { libelle: 'Payée', classe: 'bg-primary/10 text-primary' },
  partielle: { libelle: 'Partielle', classe: 'bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-100' },
  en_retard: { libelle: 'En retard', classe: 'bg-destructive/10 text-destructive' },
  a_venir: { libelle: 'À venir', classe: 'bg-muted text-muted-foreground' },
};
export const STATUTS_FRAIS = { paye: 'Soldé', partiel: 'Partiel', non_paye: 'Non payé' };
export const STATUTS_PAIE = { paye: 'Payée', partiel: 'Partielle', en_attente: 'En attente' };
export const moisCourant = () => new Date().toISOString().slice(0, 7);
