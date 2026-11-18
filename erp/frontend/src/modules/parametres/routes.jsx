import Audit from './pages/Audit';
import Classes from './pages/Classes';
import Enseignement from './pages/Enseignement';
import Etablissement from './pages/Etablissement';
import Personnes from './pages/Personnes';
import Referentiel from './pages/Referentiel';
import Utilisateurs from './pages/Utilisateurs';

export const ROUTES_PARAMETRES = [
  { path: 'referentiel', element: <Referentiel /> },
  { path: 'classes', element: <Classes /> },
  { path: 'enseignement', element: <Enseignement /> },
  { path: 'personnes', element: <Personnes /> },
  { path: 'utilisateurs', element: <Utilisateurs /> },
  { path: 'etablissement', element: <Etablissement /> },
  { path: 'audit', element: <Audit /> },
];
