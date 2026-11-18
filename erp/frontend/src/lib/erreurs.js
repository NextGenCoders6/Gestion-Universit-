/**
 * Transforme une erreur d'API en messages affichables :
 * { champs: { nom: 'message' }, global: 'message' | null }.
 * DRF renvoie { champ: ['msg'] } (400), { detail: 'msg' }, ou { non_field_errors: ['msg'] }.
 */
export function erreursServeur(error) {
  const data = error?.response?.data;
  const status = error?.response?.status;
  if (!error?.response) {
    return { champs: {}, global: 'Impossible de joindre le serveur. Vérifiez votre connexion.' };
  }
  if (status >= 500 || typeof data !== 'object' || data === null) {
    return { champs: {}, global: 'Le serveur a rencontré une erreur. Réessayez plus tard.' };
  }
  const premier = (v) => (Array.isArray(v) ? v[0] : typeof v === 'string' ? v : null);
  const champs = {};
  let global = null;
  for (const [cle, valeur] of Object.entries(data)) {
    if (cle === 'detail' || cle === 'non_field_errors' || cle === 'code') {
      global = global ?? premier(valeur);
    } else {
      champs[cle] = premier(valeur) ?? String(valeur);
    }
  }
  if (!global && Object.keys(champs).length === 0) global = 'Une erreur est survenue.';
  return { champs, global };
}
