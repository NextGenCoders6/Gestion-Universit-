/** Vacations en lecture pour la RH : volumes, état, historique (la faculté confirme dans la Scolarité). */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import { TableHistorique, TableVacations } from '../components/TablesVacations';

const ONGLETS = [['a_confirmer', 'À confirmer'], ['en_cours', 'En cours'], ['confirmee', 'Confirmées'], ['historique', 'Historique']];

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
