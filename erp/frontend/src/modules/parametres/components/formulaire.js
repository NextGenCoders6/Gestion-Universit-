/** Conversion entre les valeurs d'un formulaire (chaînes) et les données de l'API. */

const VIDE_EST_NULL = new Set(['date', 'email', 'number']);

export function valeursInitiales(champs, ligne) {
  return Object.fromEntries(champs.map((c) => {
    const v = ligne ? ligne[c.nom] : c.defaut;
    if (c.type === 'checkbox') return [c.nom, Boolean(v)];
    return [c.nom, v === null || v === undefined ? '' : String(v)];
  }));
}

export function versApi(champs, valeurs) {
  return Object.fromEntries(champs.map((c) => {
    const v = valeurs[c.nom];
    if (c.type === 'checkbox') return [c.nom, Boolean(v)];
    const vide = v === '' || v === undefined || v === null;
    if (c.source || c.type === 'number') return [c.nom, vide ? null : Number(v)];
    if (VIDE_EST_NULL.has(c.type)) return [c.nom, vide ? null : v];
    return [c.nom, v ?? ''];
  }));
}
