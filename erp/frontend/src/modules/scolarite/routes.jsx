import Deliberation from './pages/Deliberation';
import Etudiants from './pages/Etudiants';
import FicheEtudiant from './pages/FicheEtudiant';
import Promotion from './pages/Promotion';
import SaisieNotes from './pages/SaisieNotes';

export const ROUTES_SCOLARITE = [
  { path: 'etudiants', element: <Etudiants /> },
  { path: 'etudiants/:id', element: <FicheEtudiant /> },
  { path: 'saisie', element: <SaisieNotes /> },
  { path: 'deliberation', element: <Deliberation /> },
  { path: 'promotion', element: <Promotion /> },
];
