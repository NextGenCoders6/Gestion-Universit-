import DossierFrais from './pages/DossierFrais';
import Frais from './pages/Frais';
import Journal from './pages/Journal';
import Paie from './pages/Paie';
import TableauDeBord from './pages/TableauDeBord';

export const ROUTES_FINANCE = [
  { path: 'tableau-de-bord', element: <TableauDeBord /> },
  { path: 'frais', element: <Frais /> },
  { path: 'frais/:id', element: <DossierFrais /> },
  { path: 'paie-enseignants', element: <Paie key="enseignant" role="enseignant" titre="Paie des enseignants" /> },
  { path: 'paie-personnel', element: <Paie key="employe" role="employe" titre="Paie du personnel" /> },
  { path: 'journal', element: <Journal /> },
];
