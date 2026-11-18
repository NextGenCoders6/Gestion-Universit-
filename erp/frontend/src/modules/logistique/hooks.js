import useAuthStore, { aDroit } from '@/store/authStore';

export const useEstResponsableLogistique = () => useAuthStore((s) => aDroit(s, 'logistique', 'responsable'));

export const STATUTS_BUS = [
  { valeur: 'actif', libelle: 'Actif' }, { valeur: 'maintenance', libelle: 'Maintenance' },
  { valeur: 'hors_service', libelle: 'Hors service' },
];
export const TYPES_DEPENSE = { carburant: 'Carburant', entretien: 'Entretien', reparation: 'Réparation' };
