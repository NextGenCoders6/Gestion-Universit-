/** Aperçu de l'échéancier, même règle que le serveur (finance/frais.py) : mensualités égales, la dernière prend l'arrondi. */
const deux = (n) => String(n).padStart(2, '0');

export function echeancier(montant, nombre, premierMois, jour) {
  const total = Math.round(Number(montant) || 0);
  const n = Number(nombre) || 0;
  if (total <= 0 || n < 1 || !/^\d{4}-(0[1-9]|1[0-2])$/.test(premierMois ?? '')) return [];
  const base = Math.floor(total / n);
  let [annee, mois] = premierMois.split('-').map(Number);
  const lignes = [];
  for (let i = 0; i < n; i += 1) {
    const [aLim, mLim] = mois === 12 ? [annee + 1, 1] : [annee, mois + 1];
    lignes.push({ mois: `${annee}-${deux(mois)}`, date_limite: `${aLim}-${deux(mLim)}-${deux(jour)}`,
      montant: i < n - 1 ? base : total - base * (n - 1) });
    [annee, mois] = mois === 12 ? [annee + 1, 1] : [annee, mois + 1];
  }
  return lignes;
}
