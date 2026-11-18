/** « Mon espace » : même layout qu'un module, menu selon les rôles de la personne. */
import { Navigate, Route, Routes } from 'react-router-dom';
import { BookOpen, CalendarDays, FileText, GraduationCap, Tag, UserCircle, Users } from '@/components/ui/icons';
import ModuleShell from '@/app/ModuleShell';
import Introuvable from '@/app/pages/Introuvable';
import useAuthStore, { aRole } from '@/store/authStore';
import MesDocuments from './pages/MesDocuments';
import MesEnseignants from './pages/MesEnseignants';
import MesEnseignements from './pages/MesEnseignements';
import MesFrais from './pages/MesFrais';
import MesNotes from './pages/MesNotes';
import MonPlanning from './pages/MonPlanning';
import MonPlanningEtudiant from './pages/MonPlanningEtudiant';

const MENU_ENSEIGNANT = [
  { chemin: 'planning', libelle: 'Mon planning', icone: CalendarDays, element: <MonPlanning /> },
  { chemin: 'enseignements', libelle: 'Mes enseignements', icone: BookOpen, element: <MesEnseignements /> },
  { chemin: 'documents', libelle: 'Mes documents', icone: FileText, element: <MesDocuments /> },
];

const MENU_ETUDIANT = [
  { chemin: 'notes', libelle: 'Mes notes', icone: GraduationCap, element: <MesNotes /> },
  { chemin: 'planning', libelle: 'Mon planning', icone: CalendarDays, element: <MonPlanningEtudiant /> },
  { chemin: 'enseignants', libelle: 'Mes enseignants', icone: Users, element: <MesEnseignants /> },
  { chemin: 'frais', libelle: 'Mes frais', icone: Tag, element: <MesFrais /> },
];

function EnAttente() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <UserCircle className="size-10 text-muted-foreground" />
      <p className="max-w-md text-sm text-muted-foreground">
        Aucun espace personnel n’est associé à votre compte : il s’ouvre aux enseignants et aux étudiants.
      </p>
    </div>
  );
}

export default function MoiShell() {
  const enseignant = useAuthStore((s) => aRole(s, 'enseignant'));
  const etudiant = useAuthStore((s) => aRole(s, 'etudiant'));
  const menu = enseignant ? MENU_ENSEIGNANT : etudiant ? MENU_ETUDIANT : [];
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

