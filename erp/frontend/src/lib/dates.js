/** Dates de l'interface : salutation, date en toutes lettres, ISO local, bornes de semaine (lundi → dimanche). */

export function salutation(date) {
  return date.getHours() < 18 ? 'Bonjour' : 'Bonsoir';
}

export function dateLongue(date) {
  const texte = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(date);
  return texte.charAt(0).toUpperCase() + texte.slice(1);
}

const deuxChiffres = (n) => String(n).padStart(2, '0');

/** 'YYYY-MM-DD' en heure locale (toISOString passerait en UTC et pourrait changer de jour). */
export function enIso(date) {
  return `${date.getFullYear()}-${deuxChiffres(date.getMonth() + 1)}-${deuxChiffres(date.getDate())}`;
}

export function bornesSemaine(date) {
  const lundi = new Date(date.getFullYear(), date.getMonth(), date.getDate() - ((date.getDay() + 6) % 7));
  const dimanche = new Date(lundi.getFullYear(), lundi.getMonth(), lundi.getDate() + 6);
  return { debut: enIso(lundi), fin: enIso(dimanche) };
}
