/**
 * Transforme une erreur d'API en messages affichables :
 * { champs: { nom: 'message' }, global: 'message' | null }.
 * DRF renvoie { champ: ['msg'] } (400), { detail: 'msg' }, ou { non_field_errors: ['msg'] }.
 *
 * `champsFormulaire` (facultatif) : noms des champs affichés. Une clé qui n'y
 * figure pas devient le message général, pour qu'aucune erreur ne disparaisse.
 */
const CLES_GENERALES = new Set(['detail', 'non_field_errors', '__all__']);

export function erreursServeur(error, champsFormulaire) {
  const data = error?.response?.data;
  const status = error?.response?.status;
  if (!error?.response) {
    return { champs: {}, global: 'Impossible de joindre le serveur. Vérifiez votre connexion.' };
  }
  if (status >= 500 || typeof data !== 'object' || data === null) {
    return { champs: {}, global: 'Le serveur a rencontré une erreur. Réessayez plus tard.' };
  }
  const premier = (v) => (Array.isArray(v) ? v[0] : typeof v === 'string' ? v : null);
  const connus = champsFormulaire ? new Set(champsFormulaire) : null;
  const champs = {};
  const generaux = [];
  for (const [cle, valeur] of Object.entries(data)) {
    const message = premier(valeur) ?? String(valeur);
    const estChamp = connus ? connus.has(cle) : !CLES_GENERALES.has(cle) && cle !== 'code';
    if (estChamp) champs[cle] = message;
    else if (cle !== 'code' || connus) generaux.push(message);
  }
  let global = generaux[0] ?? null;
  if (!global && Object.keys(champs).length === 0) global = 'Une erreur est survenue.';
  return { champs, global };
}

/** Un seul message à afficher (toast, dialogue) : le message général, sinon celui du premier champ. */
export function messageErreur(error) {
  const { champs, global } = erreursServeur(error);
  return global ?? Object.values(champs)[0] ?? 'Une erreur est survenue.';
}
