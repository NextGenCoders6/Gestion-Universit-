/**
 * Registre des modules de l'ERP (frontend).
 *
 * Même ordre et mêmes codes que core/droits.py côté serveur. Chaque phase
 * remplit le `menu` de son module ; un module au menu vide affiche une page
 * « disponible dans une prochaine version ».
 *
 * couleur : teinte d'accent du module (triplet HSL, posé dans --module par ModuleShell).
 * menu : [{ chemin (relatif au module), libelle, icone, niveaux? }]
 *        `niveaux` absent = visible pour tout niveau du module.
 */
import {
  ArrowRightCircle, BarChart3, BookOpen, CalendarDays, Clock, FileSpreadsheet, FileText, GraduationCap, Layers, List, MapPin,
  Pencil, School, SlidersHorizontal, Tag, UserCheck, Users,
} from '@/components/ui/icons';

export const REGISTRE = [
  {
    code: 'scolarite',
    couleur: '221 83% 53%',
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
    couleur: '192 82% 38%',
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
    couleur: '262 62% 56%',
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
    couleur: '36 88% 44%',
    libelle: 'Finance',
    description: 'Frais de scolarité, paie et journal des opérations.',
    icone: BarChart3,
    chemin: '/finance',
    menu: [
      { chemin: 'tableau-de-bord', libelle: 'Tableau de bord', icone: BarChart3 },
      { chemin: 'frais', libelle: 'Frais étudiants', icone: GraduationCap },
      { chemin: 'paie-enseignants', libelle: 'Paie des enseignants', icone: BookOpen },
      { chemin: 'paie-personnel', libelle: 'Paie du personnel', icone: Users },
      { chemin: 'journal', libelle: 'Journal', icone: List },
      { chemin: 'transports', libelle: 'Transports', icone: MapPin },
    ],
  },
  {
    code: 'logistique',
    couleur: '18 85% 50%',
    libelle: 'Logistique',
    description: 'Bus, trajets et affectations des chauffeurs.',
    icone: MapPin,
    chemin: '/logistique',
    menu: [
      { chemin: 'tableau-de-bord', libelle: 'Tableau de bord', icone: BarChart3 },
      { chemin: 'bus', libelle: 'Bus', icone: MapPin },
      { chemin: 'trajets', libelle: 'Trajets', icone: List },
      { chemin: 'affectations', libelle: 'Affectations', icone: UserCheck },
      { chemin: 'couts', libelle: 'Coûts', icone: FileSpreadsheet },
    ],
  },
  {
    code: 'parametres',
    couleur: '215 16% 42%',
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
      { chemin: 'tarifs', libelle: 'Tarifs', icone: Tag },
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

/** Vrai quand la personne n'a que son espace personnel (étudiant ou enseignant, aucun module). */
export function espacePersonnelSeul(moi) {
  const roles = moi?.roles ?? [];
  return modulesVisibles(moi).length === 0 && (roles.includes('etudiant') || roles.includes('enseignant'));
}

/** Entrées de menu visibles pour les niveaux de l'utilisateur dans ce module. */
export function menuVisible(module, niveaux = []) {
  return (module?.menu ?? []).filter(
    (item) => !item.niveaux || item.niveaux.some((n) => niveaux.includes(n)),
  );
}

/** Style à poser sur un conteneur pour que `bg-module`, `text-module`… prennent la couleur du module. */
/** Variables CSS d'un module : sa couleur d'accent et, pour « Mon espace », sa toile de fond. */
export function styleModule(module) {
  if (!module?.couleur) return undefined;
  return module.canvas ? { '--module': module.couleur, '--canvas': module.canvas } : { '--module': module.couleur };
}

/** Couleur d'accent de « Mon espace » : le vert UCCB. */
export const COULEUR_MON_ESPACE = '147.6 83.4% 30%';

/** Toile vert sauge de « Mon espace », proche de #E4E8E3 éclairci ; les autres modules gardent la toile commune. */
export const CANVAS_MON_ESPACE = '105 12% 93%';
