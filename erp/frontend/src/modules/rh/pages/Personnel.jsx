import * as api from '../api';
import ListeFiches from '../components/ListeFiches';
import { FONCTIONS } from '../lib/format';

export default function Personnel() {
  return (
    <ListeFiches role="employe" titre="Personnel" lister={api.listerEmployes}
      colonnes={[
        { key: 'fonction', label: 'Fonction', render: (e) => e.fonction_libelle },
        { key: 'lieu_travail', label: 'Lieu de travail', render: (e) => e.lieu_travail || '—' },
      ]}
      filtres={[{ cle: 'fonction', label: 'Fonction', vide: 'Toutes', options: FONCTIONS }]} />
  );
}
