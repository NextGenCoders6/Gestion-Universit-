/** Recettes et dépenses des 12 derniers mois, en barres SVG (sans bibliothèque de graphiques). */
import { fcfa } from '../lib/format';

const MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

export default function GraphiqueTresorerie({ donnees = [] }) {
  const max = Math.max(1, ...donnees.flatMap((d) => [d.recettes, d.depenses]));
  const largeur = 640;
  const hauteur = 200;
  const pas = largeur / Math.max(1, donnees.length);
  const barre = Math.max(4, pas / 3);
  const h = (v) => (v / max) * (hauteur - 24);
  return (
    <figure className="space-y-2">
      <svg viewBox={`0 0 ${largeur} ${hauteur + 20}`} className="h-56 w-full" role="img"
        aria-label="Recettes et dépenses des douze derniers mois">
        {donnees.map((d, i) => {
          const x = i * pas + pas / 2;
          const libelle = MOIS[Number(d.mois.slice(5)) - 1];
          return (
            <g key={d.mois}>
              <rect x={x - barre - 1} y={hauteur - h(d.recettes)} width={barre} height={h(d.recettes)} className="fill-primary" rx="2">
                <title>{`${libelle} : recettes ${fcfa(d.recettes)}`}</title>
              </rect>
              <rect x={x + 1} y={hauteur - h(d.depenses)} width={barre} height={h(d.depenses)} className="fill-destructive/70" rx="2">
                <title>{`${libelle} : dépenses ${fcfa(d.depenses)}`}</title>
              </rect>
              <text x={x} y={hauteur + 14} textAnchor="middle" className="fill-muted-foreground text-[10px]">{libelle}</text>
            </g>
          );
        })}
        <line x1="0" x2={largeur} y1={hauteur} y2={hauteur} className="stroke-border" />
      </svg>
      <figcaption className="flex gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1"><span className="inline-block size-2.5 rounded-sm bg-primary" /> Recettes</span>
        <span className="flex items-center gap-1"><span className="inline-block size-2.5 rounded-sm bg-destructive/70" /> Dépenses</span>
      </figcaption>
    </figure>
  );
}
