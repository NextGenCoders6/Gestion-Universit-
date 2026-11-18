/** Mise en forme partagée par les écrans RH. */
export const FONCTIONS = [
  { valeur: 'menage', libelle: 'Agent de ménage' },
  { valeur: 'gardien', libelle: 'Gardien / Agent de sécurité' },
  { valeur: 'cuisinier', libelle: 'Cuisinier' },
  { valeur: 'chauffeur', libelle: 'Chauffeur' },
  { valeur: 'technicien', libelle: 'Technicien de maintenance' },
  { valeur: 'autre', libelle: 'Autre' },
];

export const TYPES_CONTRAT = [
  { valeur: 'permanent', libelle: 'Permanent' },
  { valeur: 'vacataire', libelle: 'Vacataire' },
];

export const ETATS_CONTRAT = { en_cours: 'En cours', expire: 'Expiré', a_venir: 'À venir' };

export const dateFr = (d) => (d ? new Date(d).toLocaleDateString('fr-FR') : '—');
export const montant = (v) => (v === null || v === undefined ? '—'
  : `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} FCFA`);
export const heures = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} h`;

export const libelleContrat = (c) => (c
  ? `${c.type === 'permanent' ? 'Permanent' : 'Vacataire'}${c.date_fin ? ` jusqu’au ${dateFr(c.date_fin)}` : ''}`
  : 'Aucun contrat en cours');
