/** Carte de l'accueil : titre, lien vers la page détaillée, puis une liste, un texte « vide » ou une erreur. */
import { Link } from 'react-router-dom';

export default function ListeCarte({ titre, lien, libelleLien = 'Tout voir', chargement, vide, erreur, children }) {
  let contenu = children;
  if (erreur) contenu = <p role="alert" className="text-sm text-destructive">{erreur}</p>;
  else if (chargement) contenu = <p className="text-sm text-muted-foreground">Chargement…</p>;
  else if (vide) contenu = <p className="text-sm text-muted-foreground">{vide}</p>;
  return (
    <section className="carte flex flex-col gap-3 p-4 sm:p-5">
      <header className="flex items-center justify-between gap-3">
        <h2 className="font-semibold text-foreground">{titre}</h2>
        <Link to={lien} aria-label={`${libelleLien} — ${titre}`}
          className="text-sm font-medium text-module underline-offset-4 hover:underline">
          {libelleLien}
        </Link>
      </header>
      {contenu}
    </section>
  );
}
