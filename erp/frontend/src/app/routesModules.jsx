/**
 * Routes enfants de chaque module, par code. Un module absent d'ici affiche
 * « disponible dans une prochaine version ». Chaque phase ajoute les siennes.
 */
import { ROUTES_EDT } from '@/modules/edt/routes';
import { ROUTES_FINANCE } from '@/modules/finance/routes';
import { ROUTES_LOGISTIQUE } from '@/modules/logistique/routes';
import { ROUTES_PARAMETRES } from '@/modules/parametres/routes';
import { ROUTES_RH } from '@/modules/rh/routes';
import { ROUTES_SCOLARITE } from '@/modules/scolarite/routes';

export const ROUTES_MODULES = {
  edt: ROUTES_EDT,
  finance: ROUTES_FINANCE,
  logistique: ROUTES_LOGISTIQUE,
  parametres: ROUTES_PARAMETRES,
  rh: ROUTES_RH,
  scolarite: ROUTES_SCOLARITE,
};
