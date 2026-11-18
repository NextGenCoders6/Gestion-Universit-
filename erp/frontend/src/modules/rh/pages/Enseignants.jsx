import * as api from '../api';
import ListeFiches from '../components/ListeFiches';
import { useDepartements } from '../hooks';

export default function Enseignants() {
  const departements = useDepartements();
  return (
    <ListeFiches role="enseignant" titre="Enseignants" lister={api.listerEnseignants}
      colonnes={[
        { key: 'departement', label: 'Département', render: (e) => `${e.departement_libelle} (${e.faculte})${e.est_chef ? ' · chef' : ''}` },
        { key: 'grade', label: 'Grade', render: (e) => e.grade || '—' },
      ]}
      filtres={[
        { cle: 'departement', label: 'Département', vide: 'Tous',
          options: (departements.data ?? []).map((d) => ({ valeur: String(d.id), libelle: `${d.libelle} (${d.faculte_code})` })) },
        { cle: 'type', label: 'Type de contrat', vide: 'Tous', options: [
          { valeur: 'permanent', libelle: 'Permanent' }, { valeur: 'vacataire', libelle: 'Vacataire' }] },
      ]} />
  );
}
