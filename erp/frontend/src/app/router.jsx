// Arbre de routage : connexion, lanceur, un sous-arbre par module, espace personnel.
import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import ActivationPage from '@/features/auth/ActivationPage';
import MotDePasseOubliePage from '@/features/auth/MotDePasseOubliePage';
import ReinitialisationPage from '@/features/auth/ReinitialisationPage';
import LoginPage from '@/features/auth/LoginPage';
import Lanceur from './Lanceur';
import ModuleShell from './ModuleShell';
import RequireAuth from './RequireAuth';
import RequireModule from './RequireModule';
import { REGISTRE } from './modules';
import { ROUTES_MODULES } from './routesModules';
import Introuvable from './pages/Introuvable';
import ModuleAVenir from './pages/ModuleAVenir';
import { routesMoi } from '@/modules/moi/routes';

function routeModule(module) {
  const enfants = ROUTES_MODULES[module.code];
  return {
    path: module.chemin,
    element: (
      <ModuleShell module={module}>
        <RequireModule module={module.code}>
          {enfants ? <Outlet /> : <ModuleAVenir module={module} />}
        </RequireModule>
      </ModuleShell>
    ),
    children: enfants
      ? [
          { index: true, element: <Navigate to={module.menu[0]?.chemin ?? ''} replace /> },
          ...enfants,
          { path: '*', element: <Introuvable /> },
        ]
      : undefined,
  };
}

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/activation', element: <ActivationPage /> },
  { path: '/mot-de-passe-oublie', element: <MotDePasseOubliePage /> },
  { path: '/reinitialisation/:uid/:jeton', element: <ReinitialisationPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: '/', element: <Lanceur /> },
      { path: '/moi/*', element: routesMoi() },
      ...REGISTRE.map(routeModule),
    ],
  },
  { path: '*', element: <Introuvable /> },
]);
