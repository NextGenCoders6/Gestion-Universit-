import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Clock, GraduationCap, Users } from '@/components/ui/icons';
import { CellulePersonne } from '@/components/shared/AvatarInitiales';
import { Anneau } from '@/components/shared/Graphiques';
import Indicateur from '@/components/shared/Indicateur';
import PageHeader from '@/components/shared/PageHeader';
import Pastille from '@/components/shared/Pastille';
import * as api from '../api';
import { dateFr } from '../lib/format';

function joursRestants(date) {
  return Math.ceil((new Date(`${date}T00:00:00`) - new Date()) / 86_400_000);
}

export default function TableauDeBord() {
  const d = useQuery({ queryKey: ['rh', 'tableau'], queryFn: api.tableauDeBord }).data;
  return (
    <div className="space-y-6">
      <PageHeader titre="Tableau de bord" description="Effectifs sous contrat, échéances et vacations." />
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Indicateur libelle="Enseignants actifs" valeur={d?.enseignants_actifs} icone={GraduationCap} lien="../enseignants?actif=true"
          detail={d && `${d.enseignants_permanents} permanent(s), ${d.enseignants_vacataires} vacataire(s), ${d.chefs_departement} chef(s) de département`} />
        <Indicateur libelle="Personnel actif" valeur={d?.personnel_actif} icone={Users} ton="info" lien="../personnel?actif=true"
          detail="Employés sous contrat en cours" />
        <Indicateur libelle="Vacations à confirmer" valeur={d?.vacations_a_confirmer} icone={Clock} ton="warning" lien="../vacations"
          detail="Affectations terminées, en attente de la faculté" />
        <Indicateur libelle="Sans contrat en cours" valeur={d?.personnes_sans_contrat_en_cours} icone={CalendarClock} ton="danger" lien="../contrats?etat=expire"
          detail="Contrat expiré ou jamais signé" />
      </div>
      <div className="grid gap-4 xl:grid-cols-5">
        <section className="carte p-5 xl:col-span-2">
          <h2 className="font-semibold tracking-tight">Personnel par fonction</h2>
          <p className="mb-5 text-sm text-muted-foreground">Employés sous contrat en cours.</p>
          <Anneau titre="Personnel par fonction" sousCentre="employés"
            segments={(d?.personnel_par_fonction ?? []).map((f) => ({ libelle: f.libelle, valeur: f.n }))} />
        </section>
        <section className="carte p-5 xl:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="font-semibold tracking-tight">Contrats arrivant à échéance</h2>
              <p className="text-sm text-muted-foreground">Dans les 30 prochains jours, hors contrats déjà renouvelés.</p>
            </div>
            <Link to="../contrats" className="text-sm font-medium text-module hover:underline">Tous les contrats</Link>
          </div>
          {d?.contrats_a_echeance?.length === 0 && <p className="py-6 text-center text-sm text-muted-foreground">Aucune échéance proche.</p>}
          <ul className="divide-y divide-border/70">
            {(d?.contrats_a_echeance ?? []).map((c) => {
              const jours = joursRestants(c.date_fin);
              return (
                <li key={c.id} className="flex items-center justify-between gap-3 py-3">
                  <CellulePersonne nom={c.personne_nom} secondaire={`${c.type === 'permanent' ? 'Permanent' : 'Vacataire'} · fin le ${dateFr(c.date_fin)}`} />
                  <Pastille ton={jours <= 7 ? 'rouge' : 'ambre'}>{jours <= 0 ? 'Aujourd’hui' : `J-${jours}`}</Pastille>
                </li>
              );
            })}
          </ul>
        </section>
      </div>
    </div>
  );
}
