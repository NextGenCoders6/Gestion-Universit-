/** Ligne d'accès rapides du launchpad : liens texte, retour à la ligne entre liens, jamais au milieu. */
import { Link } from 'react-router-dom';

export default function AccesRapides({ liens }) {
  if (!liens.length) return null;
  return (
    <nav aria-label="Accès rapides" className="space-y-2">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Accès rapides</h2>
      <ul className="flex flex-wrap gap-x-1 gap-y-1.5 text-sm">
        {liens.map((l, i) => (
          <li key={l.to} className="whitespace-nowrap">
            <Link to={l.to} className="font-medium text-primary underline-offset-4 hover:underline">{l.libelle}</Link>
            {i < liens.length - 1 && <span aria-hidden className="mx-1.5 text-muted-foreground">·</span>}
          </li>
        ))}
      </ul>
    </nav>
  );
}
