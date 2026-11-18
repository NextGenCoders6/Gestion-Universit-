import { useParams } from 'react-router-dom';
import * as api from '../api';
import FicheRH from '../components/FicheRH';

export default function FicheEmploye() {
  const { id } = useParams();
  return (
    <FicheRH id={id} cle="employe" charger={api.ficheEmploye} retour="Tout le personnel"
      infosRole={(f) => [['Fonction', f.fonction_libelle], ['Lieu de travail', f.lieu_travail]]} />
  );
}
