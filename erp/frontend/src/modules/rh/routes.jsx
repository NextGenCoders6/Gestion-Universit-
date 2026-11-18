import Contrats from './pages/Contrats';
import Enseignants from './pages/Enseignants';
import FicheEmploye from './pages/FicheEmploye';
import FicheEnseignant from './pages/FicheEnseignant';
import Personnel from './pages/Personnel';
import TableauDeBord from './pages/TableauDeBord';
import Vacations from './pages/Vacations';

export const ROUTES_RH = [
  { path: 'tableau-de-bord', element: <TableauDeBord /> },
  { path: 'enseignants', element: <Enseignants /> },
  { path: 'enseignants/:id', element: <FicheEnseignant /> },
  { path: 'personnel', element: <Personnel /> },
  { path: 'personnel/:id', element: <FicheEmploye /> },
  { path: 'contrats', element: <Contrats /> },
  { path: 'vacations', element: <Vacations /> },
];
