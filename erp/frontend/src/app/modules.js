/**
 * Registre des modules de l'ERP (frontend).
 *
 * Même ordre et mêmes codes que core/droits.py côté serveur. Chaque phase
 * remplit le `menu` de son module ; un module au menu vide affiche une page
 * « disponible dans une prochaine version ».
 *
 * menu : [{ chemin (relatif au module), libelle, icone, niveaux? }]
 *        `niveaux` absent = visible pour tout niveau du module.
 */
import {
  ArrowRightCircle, BarChart3, BookOpen, CalendarDays, Clock, FileSpreadsheet, FileText, GraduationCap, Layers, List, MapPin,
  Pencil, School, SlidersHorizontal, UserCheck, Users,
} from '@/components/ui/icons';

export const REGISTRE = [
  {
    code: 'scolarite',
    libelle: 'Scolarité',
    description: 'Inscriptions, notes, délibérations et documents officiels.',
    icone: GraduationCap,
    chemin: '/scolarite',
    menu: [
      { chemin: 'etudiants', libelle: 'Étudiants', icone: Users },
      { chemin: 'saisie', libelle: 'Saisie des notes', icone: Pencil, niveaux: ['faculte'] },
      { chemin: 'deliberation', libelle: 'Délibérations', icone: FileSpreadsheet, niveaux: ['faculte'] },
      { chemin: 'promotion', libelle: 'Promotion et orientation', icone: ArrowRightCircle, niveaux: ['faculte'] },
      { chemin: 'vacations', libelle: 'Vacations', icone: Clock, niveaux: ['faculte'] },
    ],
  },
  {
    code: 'edt',
    libelle: 'Emploi du temps',
    description: 'Planning des séances, affectations et progression des enseignements.',
    icone: CalendarDays,
    chemin: '/edt',
    menu: [
      { chemin: 'planning', libelle: 'Planning', icone: CalendarDays },
      { chemin: 'seances', libelle: 'Séances', icone: List },
      { chemin: 'enseignements', libelle: 'Enseignements', icone: BookOpen },
      { chemin: 'referents', libelle: 'Référents de classes', icone: UserCheck, niveaux: ['responsable', 'perimetre', 'utilisateur'] },
    ],
  },
  {
    code: 'rh',
    libelle: 'Ressources humaines',
    description: 'Enseignants, personnel, contrats et vacations.',
    icone: Users,
    chemin: '/rh',
    menu: [
      { chemin: 'tableau-de-bord', libelle: 'Tableau de bord', icone: BarChart3 },
      { chemin: 'enseignants', libelle: 'Enseignants', icone: GraduationCap },
      { chemin: 'personnel', libelle: 'Personnel', icone: Users },
      { chemin: 'contrats', libelle: 'Contrats', icone: FileText },
      { chemin: 'vacations', libelle: 'Vacations', icone: Clock },
    ],
  },
  {
    code: 'finance',
    libelle: 'Finance',
    description: 'Frais de scolarité, paie et journal des opérations.',
    icone: BarChart3,
    chemin: '/finance',
    menu: [],
  },
  {
    code: 'logistique',
    libelle: 'Logistique',
    description: 'Bus, trajets et affectations des chauffeurs.',
    icone: MapPin,
    chemin: '/logistique',
    menu: [],
  },
  {
    code: 'parametres',
    libelle: 'Paramètres',
    description: 'Utilisateurs et droits, référentiel académique, établissement.',
    icone: SlidersHorizontal,
    chemin: '/parametres',
    menu: [
      { chemin: 'referentiel', libelle: 'Référentiel', icone: Layers },
      { chemin: 'classes', libelle: 'Classes', icone: School },
      { chemin: 'enseignement', libelle: 'Enseignements', icone: BookOpen },
      { chemin: 'personnes', libelle: 'Personnes', icone: Users },
      { chemin: 'utilisateurs', libelle: 'Utilisateurs et droits', icone: UserCheck },
      { chemin: 'etablissement', libelle: 'Établissement', icone: SlidersHorizontal },
      { chemin: 'audit', libelle: 'Journal d’audit', icone: FileText },
    ],
  },
];

export const moduleParCode = (code) => REGISTRE.find((m) => m.code === code);

/** Modules du registre auxquels l'utilisateur a droit, dans l'ordre du registre. */
export function modulesVisibles(moi) {
  const autorises = new Set((moi?.modules ?? []).map((m) => m.code));
  return REGISTRE.filter((m) => autorises.has(m.code));
}

/** Entrées de menu visibles pour les niveaux de l'utilisateur dans ce module. */
export function menuVisible(module, niveaux = []) {
  return (module?.menu ?? []).filter(
    (item) => !item.niveaux || item.niveaux.some((n) => niveaux.includes(n)),
  );
}
