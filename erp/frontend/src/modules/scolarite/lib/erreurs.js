import { erreursServeur } from '@/lib/erreurs';

/** Erreurs de création d'un étudiant : celles de la personne (imbriquées) remontent au niveau des champs. */
export function erreursEtudiant(e, champs) {
  const personne = e?.response?.data?.personne;
  if (personne && typeof personne === 'object') {
    const { personne: _p, ...reste } = e.response.data;
    const aplati = { ...e, response: { ...e.response, data: { ...reste, ...personne } } };
    return erreursServeur(aplati, champs);
  }
  return erreursServeur(e, champs);
}
