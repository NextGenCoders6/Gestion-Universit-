/** Une séance dans les listes de l'accueil : jour et heures, élément constitutif, détail (enseignant ou classe). */
import { debutFin } from './calculs';

const jourCourt = (date) => new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: '2-digit', month: '2-digit' }).format(date);
const heure = (date) => date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

export default function LigneSeance({ seance, detail }) {
  const { debut, fin } = debutFin(seance);
  return (
    <li className="flex items-start gap-3 py-2.5">
      <div className="w-24 shrink-0 text-xs leading-5 text-muted-foreground">
        <p className="font-medium capitalize text-foreground">{jourCourt(debut)}</p>
        <p className="chiffres">{heure(debut)} – {heure(fin)}</p>
      </div>
      <div className="min-w-0">
        <p className="truncate font-medium text-foreground">{seance.ec_code} — {seance.ec_libelle}</p>
        {detail && <p className="truncate text-xs text-muted-foreground">{detail}</p>}
      </div>
    </li>
  );
}
