/**
 * Routes enfants de chaque module, par code. Un module absent d'ici affiche
 * « disponible dans une prochaine version ». Chaque phase ajoute les siennes.
 */
import { ROUTES_EDT } from '@/modules/edt/routes';
import { ROUTES_PARAMETRES } from '@/modules/parametres/routes';

export const ROUTES_MODULES = {
  edt: ROUTES_EDT,
  parametres: ROUTES_PARAMETRES,
};
