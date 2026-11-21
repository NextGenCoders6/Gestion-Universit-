/** Valeurs communes aux deux accueils de « Mon espace ». */
import { enIso } from '@/lib/dates';

export const INDISPONIBLE = 'Donnée indisponible pour le moment.';

/** Aujourd'hui et dans 14 jours, en ISO local : fenêtre des prochaines séances. */
export function quatorzeJours(date) {
  const fin = new Date(date.getFullYear(), date.getMonth(), date.getDate() + 14);
  return { debut: enIso(date), fin: enIso(fin) };
}
