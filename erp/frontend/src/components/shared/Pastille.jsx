/** Pastille de statut aux tons doux (fond pâle, texte foncé, liseré), lisible en clair comme en sombre. */
import { cn } from '@/lib/utils';

const TONS = {
  vert: 'bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-500/10 dark:text-emerald-300 dark:ring-emerald-400/25',
  rouge: 'bg-red-50 text-red-700 ring-red-600/15 dark:bg-red-500/10 dark:text-red-300 dark:ring-red-400/25',
  ambre: 'bg-amber-50 text-amber-800 ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-200 dark:ring-amber-400/25',
  bleu: 'bg-blue-50 text-blue-700 ring-blue-600/15 dark:bg-blue-500/10 dark:text-blue-300 dark:ring-blue-400/25',
  violet: 'bg-violet-50 text-violet-700 ring-violet-600/15 dark:bg-violet-500/10 dark:text-violet-300 dark:ring-violet-400/25',
  gris: 'bg-zinc-100 text-zinc-700 ring-zinc-500/15 dark:bg-zinc-500/10 dark:text-zinc-300 dark:ring-zinc-400/20',
};

export default function Pastille({ ton = 'gris', point = true, className, children }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-inset', TONS[ton], className)}>
      {point && <span aria-hidden className="size-1.5 rounded-full bg-current opacity-70" />}
      {children}
    </span>
  );
}
