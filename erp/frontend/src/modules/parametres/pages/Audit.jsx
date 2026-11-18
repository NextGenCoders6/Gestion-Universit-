import { useState } from 'react';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';

const MODULES = [
  ['', 'Tous les modules'], ['parametres', 'Paramètres'], ['scolarite', 'Scolarité'], ['edt', 'Emploi du temps'],
  ['rh', 'Ressources humaines'], ['finance', 'Finance'], ['logistique', 'Logistique'],
];

export default function Audit() {
  const [module, setModule] = useState('');
  const [page, setPage] = useState(1);
  const requete = useQuery({
    queryKey: ['parametres', 'audit', module, page],
    queryFn: () => api.listerAudit({ module: module || undefined, page }),
    placeholderData: keepPreviousData,
  });
  const total = requete.data?.count ?? 0;
  const pages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-4">
      <PageHeader titre="Journal d’audit" description="Actions sensibles de tous les modules, les plus récentes d’abord.">
        <div className="flex items-center gap-2">
          <Label htmlFor="filtre-module">Module</Label>
          <select
            id="filtre-module"
            value={module}
            onChange={(e) => { setModule(e.target.value); setPage(1); }}
            className="h-9 rounded-md border border-border bg-background px-3 text-sm"
          >
            {MODULES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </PageHeader>
      <DataTable
        columns={[
          { key: 'date', label: 'Date', render: (e) => new Date(e.date).toLocaleString('fr-FR') },
          { key: 'utilisateur', label: 'Utilisateur' },
          { key: 'module', label: 'Module' },
          { key: 'action', label: 'Action' },
          { key: 'description', label: 'Détail' },
          { key: 'adresse_ip', label: 'Adresse IP' },
        ]}
        data={requete.data?.results ?? []}
        isLoading={requete.isLoading}
        isError={requete.isError}
        emptyMessage="Aucune entrée."
      />
      <div className="flex items-center justify-end gap-2 text-sm text-muted-foreground">
        <span>Page {page} / {pages}</span>
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Précédente</Button>
        <Button variant="outline" size="sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Suivante</Button>
      </div>
    </div>
  );
}
