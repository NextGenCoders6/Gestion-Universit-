import Enseignements from './pages/Enseignements';
import Planning from './pages/Planning';
import Referents from './pages/Referents';
import Seances from './pages/Seances';

export const ROUTES_EDT = [
  { path: 'planning', element: <Planning /> },
  { path: 'seances', element: <Seances /> },
  { path: 'enseignements', element: <Enseignements /> },
  { path: 'referents', element: <Referents /> },
];
