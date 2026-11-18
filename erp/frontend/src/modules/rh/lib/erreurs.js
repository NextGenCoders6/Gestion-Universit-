import { erreursServeur } from '@/lib/erreurs';

/**
 * Erreurs d'une fiche RH : celles de la personne et du contrat (imbriquées) remontent au niveau
 * des champs ; celles du contrat sont préfixées « contrat_ » comme les champs du formulaire.
 */
export function erreursFiche(e, champs) {
  const data = e?.response?.data;
  if (!data || typeof data !== 'object') return erreursServeur(e, champs);
  const { personne, contrat, ...reste } = data;
  const aplati = { ...reste };
  if (personne && typeof personne === 'object') Object.assign(aplati, personne);
  if (contrat && typeof contrat === 'object') {
    for (const [cle, valeur] of Object.entries(contrat)) aplati[`contrat_${cle}`] = valeur;
  }
  return erreursServeur({ ...e, response: { ...e.response, data: aplati } }, champs);
}
