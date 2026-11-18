/** Appels à l'API Finance (/api/finance/…). */
import apiClient, { fetchAllPages } from '@/api/client';

const donnees = (r) => r.data;

export const tableauDeBord = (params = {}) => apiClient.get('/finance/tableau-de-bord/', { params }).then(donnees);

export const listerFrais = (params = {}) => apiClient.get('/finance/frais/', { params }).then(donnees);
export const dossierFrais = (id) => apiClient.get(`/finance/frais/${id}/`).then(donnees);
export const encaisser = (id, d) => apiClient.post(`/finance/frais/${id}/paiements/`, d).then(donnees);
export const ajusterFrais = (id, montant) => apiClient.post(`/finance/frais/${id}/ajuster/`, { montant }).then(donnees);
export const adapterEcheancier = (id, echeances) => apiClient.put(`/finance/frais/${id}/echeancier/`, { echeances }).then(donnees);
export const annulerPaiement = (id, motif) => apiClient.post(`/finance/paiements/${id}/annuler/`, { motif }).then(donnees);

export const listerPaie = (params = {}) => apiClient.get('/finance/paie/', { params }).then(donnees);
export const genererPaie = (mois) => apiClient.post('/finance/paie/generer/', { mois }).then(donnees);
export const payer = (id, d) => apiClient.post(`/finance/paie/${id}/paiements/`, d).then(donnees);
export const ajusterPaie = (id, montant) => apiClient.post(`/finance/paie/${id}/ajuster/`, { montant }).then(donnees);
export const lignePaie = (id) => apiClient.get(`/finance/paie/${id}/`).then(donnees);
export const annulerPaiementPaie = (id, motif) => apiClient.post(`/finance/paiements-paie/${id}/annuler/`, { motif }).then(donnees);

export const listerOperations = (params = {}) => apiClient.get('/finance/operations/', { params }).then(donnees);
export const creerOperation = (d) => apiClient.post('/finance/operations/', d).then(donnees);
export const annulerOperation = (id, motif) => apiClient.post(`/finance/operations/${id}/annuler/`, { motif }).then(donnees);

export const listerTarifs = (params = {}) => fetchAllPages('/finance/tarifs/', params);
export const creerTarif = (d) => apiClient.post('/finance/tarifs/', d).then(donnees);
export const modifierTarif = (id, d) => apiClient.patch(`/finance/tarifs/${id}/`, d).then(donnees);
export const supprimerTarif = (id) => apiClient.delete(`/finance/tarifs/${id}/`);
export const listerAnnees = () => fetchAllPages('/core/annees/');
export const listerParcours = () => fetchAllPages('/core/parcours/');

/** Télécharge un reçu PDF (le jeton passe par l'en-tête). */
export async function telecharger(chemin, nomFichier) {
  const r = await apiClient.get(chemin, { responseType: 'blob', timeout: 120_000 });
  const url = URL.createObjectURL(r.data);
  const lien = document.createElement('a');
  lien.href = url;
  lien.download = nomFichier;
  lien.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const listerTransports = (params = {}) => apiClient.get('/finance/transports/', { params }).then(donnees);
export const creerDepense = (d) => apiClient.post('/finance/transports/', d).then(donnees);
export const annulerDepense = (id, motif) => apiClient.post(`/finance/transports/${id}/annuler/`, { motif }).then(donnees);
export const listerBusFinance = () => apiClient.get('/finance/transports/bus/').then(donnees);
