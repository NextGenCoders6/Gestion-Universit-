/** Vacations en lecture pour la RH : volumes, état, historique (la faculté confirme dans la Scolarité). */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import { dateFr, heures, montant } from '../lib/format';

const ONGLETS = [['a_confirmer', 'À confirmer'], ['en_cours', 'En cours'], ['confirmee', 'Confirmées'], ['historique', 'Historique']];

export function TableVacations({ lignes, actions }) {
  if (!lignes.length) return <p className="py-6 text-center text-sm text-muted-foreground">Aucune vacation.</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
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

export default function Vacations() {
  const [onglet, setOnglet] = useState('a_confirmer');
  const lignes = useQuery({ queryKey: ['rh', 'vacations', onglet], queryFn: () => api.listerVacations({ etat: onglet }),
    enabled: onglet !== 'historique' });
  const historique = useQuery({ queryKey: ['rh', 'vacations', 'historique'], queryFn: () => api.historiqueVacations(),
    enabled: onglet === 'historique' });
  return (
    <div className="space-y-4">
      <PageHeader titre="Vacations" description="Affectations des vacataires : la faculté confirme les heures, la Finance paiera." />
      <Tabs value={onglet} onValueChange={setOnglet}>
        <TabsList>{ONGLETS.map(([v, l]) => <TabsTrigger key={v} value={v}>{l}</TabsTrigger>)}</TabsList>
      </Tabs>
      {onglet === 'historique'
        ? <TableHistorique lignes={historique.data ?? []} />
        : lignes.isLoading ? <p className="text-sm text-muted-foreground">Chargement…</p> : <TableVacations lignes={lignes.data ?? []} />}
    </div>
  );
}
