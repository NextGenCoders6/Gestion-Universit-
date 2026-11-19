/** Recettes et dépenses des 12 derniers mois : barres SVG avec grille et axe des montants. */
import { fcfa } from '../lib/format';

const MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

function arrondiHaut(v) {
  if (v <= 0) return 1;
  const puissance = 10 ** Math.floor(Math.log10(v));
  return Math.ceil(v / puissance) * puissance;
}

const court = (v) => (v >= 1e6 ? `${(v / 1e6).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} M` : v >= 1e3 ? `${Math.round(v / 1e3)} k` : String(Math.round(v)));

export default function GraphiqueTresorerie({ donnees = [] }) {
  const max = arrondiHaut(Math.max(0, ...donnees.flatMap((d) => [d.recettes, d.depenses])));
  const L = 680; const H = 220; const G = 44; const B = 24;
  const largeurUtile = L - G;
  const pas = largeurUtile / Math.max(1, donnees.length);
  const barre = Math.max(5, Math.min(14, pas / 3.2));
  const y = (v) => H - B - (v / max) * (H - B - 10);
  return (
    <figure className="space-y-3">
      <figcaption className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5"><span className="inline-block size-2.5 rounded-sm bg-primary" /> Recettes</span>
        <span className="flex items-center gap-1.5"><span className="inline-block size-2.5 rounded-sm bg-module" /> Dépenses</span>
      </figcaption>
      <svg viewBox={`0 0 ${L} ${H}`} className="h-64 w-full" role="img" aria-label="Recettes et dépenses des douze derniers mois">
        <defs>
          <linearGradient id="grad-recettes" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="1" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0.55" />
          </linearGradient>
          <linearGradient id="grad-depenses" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--module))" stopOpacity="0.95" />
            <stop offset="100%" stopColor="hsl(var(--module))" stopOpacity="0.5" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={G} x2={L} y1={y(max * t)} y2={y(max * t)} className="stroke-border" strokeDasharray={t ? '3 4' : undefined} />
            <text x={G - 8} y={y(max * t) + 3} textAnchor="end" className="fill-muted-foreground text-[10px]">{court(max * t)}</text>
          </g>
        ))}
        {donnees.map((d, i) => {
          const x = G + i * pas + pas / 2;
          const libelle = MOIS[Number(d.mois.slice(5)) - 1];
          return (
            <g key={d.mois}>
              <rect x={x - barre - 1.5} y={y(d.recettes)} width={barre} height={H - B - y(d.recettes)} rx="3" fill="url(#grad-recettes)">
                <title>{`${libelle} : recettes ${fcfa(d.recettes)}`}</title>
              </rect>
              <rect x={x + 1.5} y={y(d.depenses)} width={barre} height={H - B - y(d.depenses)} rx="3" fill="url(#grad-depenses)">
                <title>{`${libelle} : dépenses ${fcfa(d.depenses)}`}</title>
              </rect>
              <text x={x} y={H - 6} textAnchor="middle" className="fill-muted-foreground text-[10px]">{libelle}</text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
