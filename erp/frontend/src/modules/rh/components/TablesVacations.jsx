/** Tableaux des vacations et de leur historique (RH en lecture, faculté avec actions). */
import { Badge } from '@/components/ui/badge';
import { dateFr, heures, montant } from '../lib/format';

export function TableVacations({ lignes, actions }) {
  if (!lignes.length) return <p className="py-6 text-center text-sm text-muted-foreground">Aucune vacation.</p>;
  return (
    <div className="carte overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground">
          <tr><th className="px-3 py-2 text-left">Enseignant</th><th className="px-3 py-2 text-left">EC · classe</th>
            <th className="px-2 py-2">Heures faites / prévues</th><th className="px-2 py-2">Heures dues</th><th className="px-2 py-2">Vacation</th>
            {actions && <th className="px-2 py-2" />}</tr>
        </thead>
        <tbody>
          {lignes.map((l) => (
            <tr key={l.affectation} className="border-t border-border">
              <td className="px-3 py-1.5 font-medium">{l.enseignant_nom}</td>
              <td className="px-3 py-1.5">{l.ec_code} — {l.ec_libelle}<div className="text-xs text-muted-foreground">{l.classe_libelle}{l.type_seance ? ` · ${l.type_seance}` : ''}</div></td>
              <td className="px-2 py-1.5 text-center">{heures(l.heures_effectuees)} / {heures(l.heures_prevues)}</td>
              <td className="px-2 py-1.5 text-center">{heures(l.heures_dues)}{l.heures_jumelles > 0 && <div className="text-xs text-muted-foreground">dont {heures(l.heures_jumelles)} mutualisées</div>}</td>
              <td className="px-2 py-1.5 text-center">
                {l.vacation
                  ? <><Badge variant="secondary">{montant(l.vacation.montant)}</Badge><div className="text-xs text-muted-foreground">{heures(l.vacation.heures_retenues)} × {montant(l.vacation.taux_horaire)}{l.vacation.motif && ` · ${l.vacation.motif}`}</div></>
                  : l.motif_blocage ? <span className="text-xs text-amber-700">{l.motif_blocage}</span>
                    : <span className="text-xs text-muted-foreground">{l.terminee ? 'Terminée' : 'En cours'}</span>}
              </td>
              {actions && <td className="px-2 py-1.5 text-right">{actions(l)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function TableHistorique({ lignes }) {
  if (!lignes.length) return <p className="py-6 text-center text-sm text-muted-foreground">Aucun historique.</p>;
  return (
    <ul className="space-y-1 text-sm">
      {lignes.map((h) => (
        <li key={h.id} className="rounded-md bg-muted/40 px-3 py-2">
          <strong>{h.action_libelle}</strong> · {h.enseignant_nom} · {h.ec_code} ({h.classe_libelle}) · {heures(h.heures_retenues)}, {montant(h.montant)}
          <div className="text-xs text-muted-foreground">{dateFr(h.le)}{h.par && ` par ${h.par}`}{h.motif && ` · ${h.motif}`}</div>
        </li>
      ))}
    </ul>
  );
}
