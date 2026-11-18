/** « Mon espace » : même layout qu'un module, menu selon les rôles de la personne. */
import { Navigate, Route, Routes } from 'react-router-dom';
import { BookOpen, CalendarDays, FileText, UserCircle } from '@/components/ui/icons';
import ModuleShell from '@/app/ModuleShell';
import Introuvable from '@/app/pages/Introuvable';
import useAuthStore, { aRole } from '@/store/authStore';
import MesDocuments from './pages/MesDocuments';
import MesEnseignements from './pages/MesEnseignements';
import MonPlanning from './pages/MonPlanning';

const MENU_ENSEIGNANT = [
  { chemin: 'planning', libelle: 'Mon planning', icone: CalendarDays, element: <MonPlanning /> },
  { chemin: 'enseignements', libelle: 'Mes enseignements', icone: BookOpen, element: <MesEnseignements /> },
  { chemin: 'documents', libelle: 'Mes documents', icone: FileText, element: <MesDocuments /> },
];

function EnAttente() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <UserCircle className="size-10 text-muted-foreground" />
      <p className="max-w-md text-sm text-muted-foreground">
        Votre planning arrivera avec la Scolarité : il dépend de votre inscription dans une classe.
      </p>
    </div>
  );
}

function MoiShell() {
  const enseignant = useAuthStore((s) => aRole(s, 'enseignant'));
  const menu = enseignant ? MENU_ENSEIGNANT : [];
  const module = { code: 'moi', libelle: 'Mon espace', chemin: '/moi', menu };
  return (
    <ModuleShell module={module}>
      <Routes>
        <Route index element={menu.length ? <Navigate to={menu[0].chemin} replace /> : <EnAttente />} />
        {menu.map((m) => <Route key={m.chemin} path={m.chemin} element={m.element} />)}
        <Route path="*" element={<Introuvable />} />
      </Routes>
    </ModuleShell>
  );
}

export const routesMoi = () => <MoiShell />;
