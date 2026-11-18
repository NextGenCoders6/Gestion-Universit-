import Affectations from './pages/Affectations';
import Bus from './pages/Bus';
import Couts from './pages/Couts';
import TableauDeBord from './pages/TableauDeBord';
import Trajets from './pages/Trajets';

export const ROUTES_LOGISTIQUE = [
  { path: 'tableau-de-bord', element: <TableauDeBord /> },
  { path: 'bus', element: <Bus /> },
  { path: 'trajets', element: <Trajets /> },
  { path: 'affectations', element: <Affectations /> },
  { path: 'couts', element: <Couts /> },
];
