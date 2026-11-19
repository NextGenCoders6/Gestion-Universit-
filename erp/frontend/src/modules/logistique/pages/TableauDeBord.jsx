import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, BarChart3, MapPin, UserCheck, Users } from '@/components/ui/icons';
import { Anneau, BarresRepartition } from '@/components/shared/Graphiques';
import Indicateur from '@/components/shared/Indicateur';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';

const fcfa = (v) => `${Number(v ?? 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })} FCFA`;

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['logistique', 'tableau'], queryFn: api.tableauDeBord }).data;
  const couts = useQuery({ queryKey: ['logistique', 'couts'], queryFn: () => api.couts() }).data;
  if (!d) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  const s = d.bus_par_statut;
  return (
    <div className="space-y-6">
      <PageHeader titre="Tableau de bord" description="Parc, affectations et coûts de transport." />
      {d.alertes.length > 0 && (
        <ul className="space-y-2">{d.alertes.map((a) => (
          <li key={a.affectation} className="flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900 ring-1 ring-inset ring-amber-600/20 dark:bg-amber-500/10 dark:text-amber-100">
            <AlertTriangle className="size-4 shrink-0" />{a.message}</li>))}</ul>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur libelle="Bus actifs" valeur={s.actif} icone={MapPin} lien="../bus" detail={`${s.maintenance} en maintenance, ${s.hors_service} hors service`} />
        <Indicateur libelle="Affectations en cours" valeur={d.affectations_actives} icone={UserCheck} ton="info" lien="../affectations" />
        <Indicateur libelle="Chauffeurs disponibles" valeur={d.chauffeurs_disponibles} icone={Users} ton="success" lien="../affectations" detail="Sous contrat et sans bus" />
        <Indicateur libelle="Coûts du mois" valeur={fcfa(d.couts_mois)} icone={BarChart3} ton="warning" lien="../couts" detail={`${fcfa(d.couts_annee)} depuis septembre`} />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="carte p-5">
          <h2 className="font-semibold tracking-tight">État du parc</h2>
          <p className="mb-5 text-sm text-muted-foreground">Répartition des bus par statut.</p>
          <Anneau titre="Bus par statut" sousCentre="bus" segments={[
            { libelle: 'Actifs', valeur: s.actif, couleur: 'hsl(var(--success))' },
            { libelle: 'En maintenance', valeur: s.maintenance, couleur: 'hsl(var(--warning))' },
            { libelle: 'Hors service', valeur: s.hors_service, couleur: 'hsl(var(--destructive))' },
          ]} />
        </section>
        <section className="carte p-5 lg:col-span-2">
          <h2 className="font-semibold tracking-tight">Coûts par bus</h2>
          <p className="mb-5 text-sm text-muted-foreground">Carburant, entretien et réparations enregistrés par la Finance.</p>
          {couts
            ? <BarresRepartition formater={fcfa} lignes={couts.par_bus.map((b) => ({ libelle: `Bus ${b.numero}`, valeur: b.total }))} />
            : <p className="text-sm text-muted-foreground">Chargement…</p>}
        </section>
      </div>
    </div>
  );
}
