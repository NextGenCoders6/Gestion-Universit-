/** Avatar à initiales, d'une couleur stable par personne (dérivée du nom). */
import { cn } from '@/lib/utils';

const TEINTES = [221, 262, 192, 147, 18, 36, 330, 173];

export function initiales(nom = '') {
  return nom.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
}

export default function AvatarInitiales({ nom, photo, taille = 'md', className }) {
  const h = TEINTES[[...(nom ?? '')].reduce((s, c) => s + c.charCodeAt(0), 0) % TEINTES.length];
  const dimension = taille === 'sm' ? 'size-7 text-[11px]' : taille === 'lg' ? 'size-12 text-base' : 'size-9 text-xs';
  if (photo) return <img src={photo} alt="" className={cn('shrink-0 rounded-full object-cover', dimension, className)} />;
  return (
    <span aria-hidden className={cn('flex shrink-0 items-center justify-center rounded-full font-semibold', dimension, className)}
      style={{ backgroundColor: `hsl(${h} 70% 94%)`, color: `hsl(${h} 55% 32%)` }}>
      {initiales(nom)}
    </span>
  );
}

/** Cellule « personne » des tableaux : avatar, nom, ligne secondaire. */
export function CellulePersonne({ nom, secondaire, photo }) {
  return (
    <span className="flex items-center gap-3">
      <AvatarInitiales nom={nom} photo={photo} />
      <span className="min-w-0">
        <span className="block truncate font-medium text-foreground">{nom}</span>
        {secondaire && <span className="block truncate text-xs text-muted-foreground">{secondaire}</span>}
      </span>
    </span>
  );
}
