/** Petits graphiques SVG sans dépendance : anneau de répartition et barres de répartition. */
// Teintes fixes et distinctes : la couleur du module n'y figure pas, sinon elle doublait
// l'une d'elles (le violet des RH, par exemple).
const PALETTE = ['hsl(221 83% 53%)', 'hsl(147.6 70% 34%)', 'hsl(36 88% 46%)', 'hsl(262 62% 56%)', 'hsl(330 65% 52%)', 'hsl(192 82% 38%)', 'hsl(215 16% 52%)'];

const nombre = (v) => Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

/** Anneau : segments [{ libelle, valeur, couleur? }], texte central, légende dessous
 *  (les cartes qui l'accueillent sont étroites : à droite, les libellés étaient tronqués). */
export function Anneau({ segments = [], centre, sousCentre, formater = nombre, titre }) {
  const total = segments.reduce((s, x) => s + Math.max(0, x.valeur), 0);
  const rayon = 52;
  const circonference = 2 * Math.PI * rayon;
  let decalage = 0;
  return (
    <div className="flex flex-col items-center gap-5">
      <svg viewBox="0 0 140 140" className="size-36 shrink-0 -rotate-90" role="img" aria-label={titre}>
        <circle cx="70" cy="70" r={rayon} fill="none" strokeWidth="16" className="stroke-muted" />
        {total > 0 && segments.map((s, i) => {
          const part = (Math.max(0, s.valeur) / total) * circonference;
          const el = (
            <circle key={s.libelle} cx="70" cy="70" r={rayon} fill="none" strokeWidth="16" strokeLinecap="butt"
              stroke={s.couleur ?? PALETTE[i % PALETTE.length]} strokeDasharray={`${part} ${circonference - part}`}
              strokeDashoffset={-decalage}>
              <title>{`${s.libelle} : ${formater(s.valeur)}`}</title>
            </circle>
          );
          decalage += part;
          return el;
        })}
        <g className="rotate-90" style={{ transformOrigin: '70px 70px' }}>
          <text x="70" y={sousCentre ? 68 : 75} textAnchor="middle" className="fill-foreground text-[20px] font-semibold">{centre ?? nombre(total)}</text>
          {sousCentre && <text x="70" y="86" textAnchor="middle" className="fill-muted-foreground text-[10px]">{sousCentre}</text>}
        </g>
      </svg>
      <ul className="w-full space-y-2 text-sm">
        {segments.map((s, i) => (
          <li key={s.libelle} className="flex items-center justify-between gap-3">
            <span className="flex min-w-0 items-center gap-2">
              <span aria-hidden className="size-2.5 shrink-0 rounded-sm" style={{ background: s.couleur ?? PALETTE[i % PALETTE.length] }} />
              <span className="truncate text-muted-foreground">{s.libelle}</span>
            </span>
            <span className="chiffres whitespace-nowrap font-medium">{formater(s.valeur)}</span>
          </li>
        ))}
        {segments.length === 0 && <li className="text-muted-foreground">Aucune donnée.</li>}
      </ul>
    </div>
  );
}

/** Barres horizontales : lignes [{ libelle, valeur }] proportionnelles à la plus grande. */
export function BarresRepartition({ lignes = [], formater = nombre, couleur = 'bg-module' }) {
  const max = Math.max(1, ...lignes.map((l) => l.valeur));
  if (lignes.length === 0) return <p className="text-sm text-muted-foreground">Aucune donnée.</p>;
  return (
    <ul className="space-y-3">
      {lignes.map((l) => (
        <li key={l.libelle} className="text-sm">
          <div className="mb-1 flex justify-between gap-3"><span className="truncate text-muted-foreground">{l.libelle}</span><span className="chiffres font-medium">{formater(l.valeur)}</span></div>
          <div className="h-2 overflow-hidden rounded-full bg-muted"><div className={`h-2 rounded-full ${couleur}`} style={{ width: `${(l.valeur / max) * 100}%` }} /></div>
        </li>
      ))}
    </ul>
  );
}
