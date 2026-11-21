/** Tuile du launchpad (style SAP Fiori) : titre, ce que compte le chiffre, le chiffre, une ligne de détail.
 *  Ton alerte en ambre foncé (amber-700, ≈ 5:1 sur blanc) : --warning est trop clair pour du texte. */
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

const nombre = (v) => v.toLocaleString('fr-FR', { maximumFractionDigits: 1 });

const GRIS = 'text-[28px] font-semibold leading-none text-muted-foreground';

/** Chiffre de la tuile : « … » en chargement, « — » sans valeur, rien si la tuile n'a pas de chiffre. */
function Chiffre({ valeur, unite, alerte, chargement }) {
  if (chargement) return <span className={GRIS}>…</span>;
  if (valeur === undefined) return null;
  if (valeur === null) return <span className={GRIS}>—</span>;
  return (
    <span className="flex items-baseline gap-1">
      <span className={cn('chiffres text-[28px] font-semibold leading-none tracking-tight', alerte ? 'text-amber-700' : 'text-foreground')}>
        {nombre(valeur)}
      </span>
      {unite && <span className="text-sm font-medium text-muted-foreground">{unite}</span>}
    </span>
  );
}

export default function TuileModule({ titre, sousTitre, valeur, unite, detail, ton = 'normal', icone: Icone, couleur, to, chargement }) {
  const alerte = ton === 'alerte';
  return (
    <Link
      to={to}
      className="flex min-h-[9.5rem] w-full flex-col justify-between gap-3 rounded-md border border-border bg-card p-3.5 transition-shadow hover:shadow-card-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:min-h-[11rem] sm:p-4"
    >
      <span className="flex items-start justify-between gap-2">
        <span className="min-w-0">
          <span className="block text-sm font-semibold leading-tight text-foreground">{titre}</span>
          {sousTitre && <span className="mt-1 block text-xs leading-snug text-muted-foreground">{sousTitre}</span>}
        </span>
        {Icone && <Icone aria-hidden className="size-5 shrink-0" style={couleur ? { color: `hsl(${couleur})` } : undefined} />}
      </span>
      <span className="space-y-1">
        <Chiffre valeur={valeur} unite={unite} alerte={alerte} chargement={chargement} />
        {detail && <span className={cn('block text-xs leading-snug', alerte ? 'text-amber-700' : 'text-muted-foreground')}>{detail}</span>}
      </span>
    </Link>
  );
}
