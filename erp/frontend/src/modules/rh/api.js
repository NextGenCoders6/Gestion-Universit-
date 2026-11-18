/** Appels à l'API du module RH (/api/rh/…). */
import apiClient, { fetchAllPages } from '@/api/client';

const donnees = (r) => r.data;

export const tableauDeBord = () => apiClient.get('/rh/tableau-de-bord/').then(donnees);

export const listerEnseignants = (params = {}) => apiClient.get('/rh/enseignants/', { params }).then(donnees);
export const ficheEnseignant = (id) => apiClient.get(`/rh/enseignants/${id}/`).then(donnees);
export const creerEnseignant = (d) => apiClient.post('/rh/enseignants/', d).then(donnees);
export const modifierEnseignant = (id, d) => apiClient.patch(`/rh/enseignants/${id}/`, d).then(donnees);

export const listerEmployes = (params = {}) => apiClient.get('/rh/employes/', { params }).then(donnees);
export const ficheEmploye = (id) => apiClient.get(`/rh/employes/${id}/`).then(donnees);
export const creerEmploye = (d) => apiClient.post('/rh/employes/', d).then(donnees);

export const listerContrats = (params = {}) => apiClient.get('/rh/contrats/', { params }).then(donnees);
export const creerContrat = (d) => apiClient.post('/rh/contrats/', d).then(donnees);
export const terminerContrat = (id, dateFin) => apiClient.post(`/rh/contrats/${id}/terminer/`, { date_fin: dateFin }).then(donnees);

export const listerVacations = (params = {}) => apiClient.get('/rh/vacations/', { params }).then(donnees);
export const historiqueVacations = (params = {}) => apiClient.get('/rh/vacations/historique/', { params }).then(donnees);

export const listerDepartements = () => fetchAllPages('/core/departements/');
export const listerFacultes = () => fetchAllPages('/core/facultes/');
