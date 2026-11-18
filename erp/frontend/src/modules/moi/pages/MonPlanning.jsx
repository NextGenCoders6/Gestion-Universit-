import { useCallback, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import PageHeader from '@/components/shared/PageHeader';
import PlanningGrid from '@/modules/edt/components/PlanningGrid';
import SeanceDetailsDialog from '@/modules/edt/components/SeanceDetailsDialog';
import { enIso, evenementsDepuisSeances } from '@/modules/edt/lib/planning';
import * as api from '../api';

export default function MonPlanning() {
  const [semaine, setSemaine] = useState(null);
  const [details, setDetails] = useState(null);
  const params = semaine ? { date_debut: enIso(semaine.start), date_fin: enIso(new Date(semaine.end.getTime() - 1)) } : null;
  const seances = useQuery({ queryKey: ['moi', 'planning', params], queryFn: () => api.monPlanning(params), enabled: Boolean(params) });
  const evenements = useMemo(() => evenementsDepuisSeances(seances.data ?? []), [seances.data]);
  const changerSemaine = useCallback(({ start, end }) => setSemaine({ start, end }), []);

  return (
    <div className="space-y-4">
      <PageHeader titre="Mon planning" description="Vos séances publiées." />
      <PlanningGrid events={evenements} isLoading={false} isError={seances.isError} onRangeChange={changerSemaine}
        onEventClick={(info) => setDetails(info.event.extendedProps)} />
      <SeanceDetailsDialog seance={details} peutGerer={false} onFermer={() => setDetails(null)} onModifier={() => {}} />
    </div>
  );
}
