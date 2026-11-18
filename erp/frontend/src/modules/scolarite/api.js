/** Appels à l'API du module Scolarité (/api/scolarite/…). */
import apiClient from '@/api/client';

const donnees = (r) => r.data;

export const listerClasses = (params = {}) => apiClient.get('/scolarite/classes/', { params }).then(donnees);

export const listerEtudiants = (params = {}) => apiClient.get('/scolarite/etudiants/', { params }).then(donnees);
export const ficheEtudiant = (id) => apiClient.get(`/scolarite/etudiants/${id}/`).then(donnees);
export const creerEtudiant = (d) => apiClient.post('/scolarite/etudiants/', d).then(donnees);
export const changerStatut = (id, statut) => apiClient.post(`/scolarite/etudiants/${id}/statut/`, { statut }).then(donnees);
export const notesEtudiant = (id, params = {}) => apiClient.get(`/scolarite/etudiants/${id}/notes/`, { params }).then(donnees);
export const creerInscription = (d) => apiClient.post('/scolarite/inscriptions/', d).then(donnees);
export const modifierInscription = (id, d) => apiClient.patch(`/scolarite/inscriptions/${id}/`, d).then(donnees);

export const grilleSaisie = (params) => apiClient.get('/scolarite/saisie/', { params }).then(donnees);
/** Les erreurs par cellule arrivent aussi avec un statut 400 (aucune ligne valide) : on les renvoie telles quelles. */
export const enregistrerSaisie = (notes) => apiClient.post('/scolarite/saisie/', { notes })
  .then(donnees)
  .catch((e) => { if (e?.response?.status === 400 && e.response.data?.erreurs) return e.response.data; throw e; });

export const deliberation = (params) => apiClient.get('/scolarite/deliberation/', { params }).then(donnees);
export const enregistrerDeliberation = (d) => apiClient.post('/scolarite/deliberation/', d).then(donnees);
export const rouvrirDeliberation = (params) => apiClient.delete('/scolarite/deliberation/', { params }).then(donnees);

export const promotion = (params) => apiClient.get('/scolarite/promotion/', { params }).then(donnees);
export const appliquerPromotion = (d) => apiClient.post('/scolarite/promotion/', d).then(donnees);
export const orientation = (params) => apiClient.get('/scolarite/orientation/', { params }).then(donnees);
export const appliquerOrientation = (d) => apiClient.post('/scolarite/orientation/', d).then(donnees);

/** Télécharge un fichier produit par l'API (PDF, Excel) ; le jeton passe par l'en-tête. */
export async function telecharger(chemin, params, nomFichier) {
  const r = await apiClient.get(chemin, { params, responseType: 'blob', timeout: 120_000 });
  const url = URL.createObjectURL(r.data);
  const lien = document.createElement('a');
  lien.href = url;
  lien.download = nomFichier;
  lien.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Les erreurs d'un fichier demandé en blob arrivent en Blob : on en relit le message JSON. */
export async function messageErreurBlob(e) {
  const data = e?.response?.data;
  if (data instanceof Blob) {
    try { return JSON.parse(await data.text()).detail ?? 'Téléchargement impossible.'; } catch { return 'Téléchargement impossible.'; }
  }
  return data?.detail ?? 'Téléchargement impossible.';
}
