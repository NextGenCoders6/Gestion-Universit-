/** Carte indicateur (KPI) : libellé, valeur en grand, détail, icône teintée ; cliquable si `lien`. */
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';

const TONS = {
  module: 'bg-module/10 text-module ring-module/20',
  primary: 'bg-primary/10 text-primary ring-primary/20',
  success: 'bg-success/10 text-success ring-success/20',
  warning: 'bg-warning/10 text-warning ring-warning/25',
  danger: 'bg-destructive/10 text-destructive ring-destructive/20',
  info: 'bg-info/10 text-info ring-info/20',
};

export default function Indicateur({ libelle, valeur, detail, icone: Icone, ton = 'module', lien, enfants }) {
  const contenu = (
    <>
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{libelle}</p>
        {Icone && (
          <span className={cn('flex size-10 shrink-0 items-center justify-center rounded-xl ring-1', TONS[ton])}>
            <Icone className="size-5" />
          </span>
        )}
      </div>
      <p className="chiffres mt-1 text-[28px] font-semibold leading-tight tracking-tight text-foreground">{valeur ?? '—'}</p>
      {detail && <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{detail}</p>}
      {enfants}
    </>
  );
  return lien
    ? <Link to={lien} className="carte-interactive block p-5 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring">{contenu}</Link>
    : <div className="carte p-5">{contenu}</div>;
}
