/** Conversion séances ↔ événements du calendrier, et déplacement par glisser-déposer. */
import { erreursServeur } from '@/lib/erreurs';

const DEPLACABLES = new Set(['brouillon', 'Confirmée']);
const deux = (n) => String(n).padStart(2, '0');

/** Date locale AAAA-MM-JJ (sans passer par UTC). */
export const enIso = (d) => `${d.getFullYear()}-${deux(d.getMonth() + 1)}-${deux(d.getDate())}`;
export const enHeure = (d) => `${deux(d.getHours())}:${deux(d.getMinutes())}`;

export function evenementsDepuisSeances(seances = [], { modifiable = false } = {}) {
  return seances.map((s) => {
    const { jour, debut, fin } = s.creneau_effectif;
    return {
      id: String(s.id),
      title: `${s.ec_code} — ${s.classe_libelle}`,
      start: `${jour}T${debut}`,
      end: `${jour}T${fin}`,
      startEditable: modifiable && DEPLACABLES.has(s.statut),
      durationEditable: false,
      extendedProps: { ...s, heure_debut: debut, heure_fin: fin, is_mutualise: Boolean(s.seance_liee) },
    };
  });
}

/**
 * Enregistre le nouveau créneau d'une séance déplacée. En cas de refus, la
 * séance revient à sa place et le message du serveur est affiché.
 */
export async function deplacerSeance(info, { modifier, notifier }) {
  const { event } = info;
  try {
    await modifier(event.id, {
      date_seance: enIso(event.start),
      heure_debut: enHeure(event.start),
      heure_fin: enHeure(event.end),
    });
    return true;
  } catch (error) {
    info.revert();
    const { champs, global } = erreursServeur(error);
    notifier({
      title: 'Déplacement refusé',
      description: Object.values(champs)[0] ?? global,
      variant: 'destructive',
    });
    return false;
  }
}

/** Lundi et samedi de la semaine d'une date (bornes de requête). */
export function bornesSemaine(date = new Date()) {
  const lundi = new Date(date);
  lundi.setDate(date.getDate() - ((date.getDay() + 6) % 7));
  const samedi = new Date(lundi);
  samedi.setDate(lundi.getDate() + 5);
  return { debut: enIso(lundi), fin: enIso(samedi) };
}

/** « 2026-10-05 » → « 05/10/2026 ». */
export const jjmmaaaa = (iso) => (iso ? iso.split('-').reverse().join('/') : '');
