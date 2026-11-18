/** Champs et conversion d'un contrat pour les formulaires RH. */
export const CHAMPS_CONTRAT = ['type', 'date_debut', 'date_fin', 'taux_horaire', 'salaire_mensuel', 'rib', 'numero_secu', 'diplome'];

/** Valeurs du formulaire → contrat pour l'API (null si aucun type choisi). */
export function contratDepuis(v, prefixe = '') {
  const g = (c) => v[`${prefixe}${c}`];
  if (!g('type')) return null;
  return {
    type: g('type'), date_debut: g('date_debut') || null, date_fin: g('date_fin') || null,
    taux_horaire: g('type') === 'vacataire' ? (g('taux_horaire') || null) : null,
    salaire_mensuel: g('type') === 'permanent' ? (g('salaire_mensuel') || null) : null,
    rib: g('rib') ?? '', numero_secu: g('numero_secu') ?? '', diplome: g('diplome') ?? '',
  };
}
