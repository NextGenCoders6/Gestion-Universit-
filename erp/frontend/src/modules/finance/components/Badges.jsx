import { ETATS_ECHEANCE } from '../lib/format';

export function BadgeEcheance({ etat }) {
  const e = ETATS_ECHEANCE[etat];
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${e.classe}`}>{e.libelle}</span>;
}

export function BadgeStatut({ libelle, ok, alerte }) {
  const classe = ok ? 'bg-primary/10 text-primary' : alerte ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground';
  return <span className={`rounded px-2 py-0.5 text-xs font-semibold ${classe}`}>{libelle}</span>;
}
