/** Calculs de l'accueil de « Mon espace », à partir des réponses des endpoints /moi/. */

function enDate(jour, heure) {
  const [a, m, j] = jour.split('-').map(Number);
  const [h, min] = heure.split(':').map(Number);
  return new Date(a, m - 1, j, h, min);
}

/** Début et fin réels d'une séance : le créneau effectif tient compte d'un report. */
export function debutFin(seance) {
  const c = seance.creneau_effectif;
  return c
    ? { debut: enDate(c.jour, c.debut), fin: enDate(c.jour, c.fin) }
    : { debut: enDate(seance.date_seance, seance.heure_debut), fin: enDate(seance.date_seance, seance.heure_fin) };
}

/** Total des heures de cours, arrondi à la demi-heure. */
export function heuresSeances(seances) {
  const minutes = (seances ?? []).reduce((total, s) => {
    const { debut, fin } = debutFin(s);
    return total + (fin - debut) / 60000;
  }, 0);
  return Math.round(minutes / 30) / 2;
}

/** Séances pas encore terminées, de la plus proche à la plus lointaine. */
export function prochainesSeances(seances, maintenant, n = 5) {
  return (seances ?? [])
    .map((s) => ({ s, ...debutFin(s) }))
    .filter(({ fin }) => fin > maintenant)
    .sort((a, b) => a.debut - b.debut)
    .slice(0, n)
    .map(({ s }) => s);
}

/** Dernier semestre délibéré de l'inscription la plus récente, ou le message si les résultats sont masqués. */
export function dernierResultat(notes) {
  const inscription = notes?.inscriptions?.[0];
  if (!inscription) return null;
  if (inscription.resultats_masques) return { masque: inscription.message_resultats };
  const semestre = [...(inscription.semestres ?? [])].reverse().find((x) => x.deliberee && x.resultat);
  return semestre
    ? { semestre: semestre.semestre, moyenne: semestre.resultat.moyenne, decision: semestre.resultat.decision }
    : null;
}

export function dossierCourant(frais) {
  if (!frais?.length) return null;
  return frais.find((d) => d.inscription_statut === 'active') ?? frais[0];
}

export function bilanEnseignements(affectations) {
  const liste = affectations ?? [];
  return {
    faites: liste.reduce((t, a) => t + a.heures_effectuees, 0),
    prevues: liste.reduce((t, a) => t + a.heures_prevues, 0),
    classes: new Set(liste.map((a) => a.classe)).size,
  };
}
