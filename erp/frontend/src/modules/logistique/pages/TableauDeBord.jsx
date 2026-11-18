import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';

const fcfa = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;

function Tuile({ libelle, valeur, detail, lien }) {
  return (
    <Link to={lien} className="block rounded-lg border border-border bg-card p-4 hover:opacity-90">
      <p className="text-xs uppercase text-muted-foreground">{libelle}</p><p className="text-2xl font-bold">{valeur}</p>
      {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
    </Link>
  );
}

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['logistique', 'tableau'], queryFn: api.tableauDeBord }).data;
  if (!d) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  const s = d.bus_par_statut;
  return (
    <div className="space-y-4">
      <PageHeader titre="Tableau de bord" description="Parc, affectations et coûts de transport." />
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Tuile libelle="Bus actifs" valeur={s.actif} detail={`${s.maintenance} en maintenance, ${s.hors_service} hors service`} lien="../bus" />
        <Tuile libelle="Affectations en cours" valeur={d.affectations_actives} lien="../affectations" />
        <Tuile libelle="Chauffeurs disponibles" valeur={d.chauffeurs_disponibles} detail="Sous contrat et sans bus" lien="../affectations" />
        <Tuile libelle="Coûts du mois" valeur={fcfa(d.couts_mois)} detail={`${fcfa(d.couts_annee)} depuis septembre`} lien="../couts" />
      </div>
      {d.alertes.length > 0 && (
        <ul className="space-y-1">{d.alertes.map((a) => (
          <li key={a.affectation} className="flex items-center gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-100">
            <AlertTriangle className="size-4" />{a.message}</li>))}</ul>
      )}
    </div>
  );
}
