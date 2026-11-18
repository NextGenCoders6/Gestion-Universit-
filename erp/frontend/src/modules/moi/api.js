/** Espace personnel de l'enseignant (/api/edt/moi/…). */
import apiClient from '@/api/client';

const donnees = (r) => r.data;

export const monPlanning = (params = {}) => apiClient.get('/edt/moi/planning/', { params }).then(donnees);
export const mesEnseignements = () => apiClient.get('/edt/moi/enseignements/').then(donnees);
export const mesDocuments = () => apiClient.get('/edt/moi/documents/').then(donnees);
export const deposerDocument = (formData) => apiClient.post('/edt/moi/documents/', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120_000,
}).then(donnees);

/** Télécharge un document (le jeton passe par l'en-tête, pas par l'URL). */
export async function telechargerDocument(doc) {
  const r = await apiClient.get(`/edt/moi/documents/${doc.id}/telecharger/`, { responseType: 'blob', timeout: 120_000 });
  const url = URL.createObjectURL(r.data);
  const lien = document.createElement('a');
  lien.href = url;
  lien.download = doc.nom_fichier ?? doc.titre;
  lien.click();
  URL.revokeObjectURL(url);
}
