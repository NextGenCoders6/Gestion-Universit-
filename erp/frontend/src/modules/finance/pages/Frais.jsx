import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChevronLeft, ChevronRight, Eye, Search } from '@/components/ui/icons';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import Selecteur from '@/components/shared/Selecteur';
import * as api from '../api';
import { BadgeStatut } from '../components/Badges';
import { dateFr, fcfa, STATUTS_FRAIS } from '../lib/format';
import { CellulePersonne } from '@/components/shared/AvatarInitiales';

export default function Frais() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const v = (c) => params.get(c) ?? '';
  const choisir = (modif) => {
    const suivant = new URLSearchParams(params);
    for (const [c, x] of Object.entries(modif)) { if (x) suivant.set(c, x); else suivant.delete(c); }
    setParams(suivant, { replace: true });
  };
  const [recherche, setRecherche] = useState(v('q'));
  const requete = { q: v('q') || undefined, statut: v('statut') || undefined, retard: v('retard') || undefined, page: v('page') || 1 };
  const liste = useQuery({ queryKey: ['finance', 'frais', requete], queryFn: () => api.listerFrais(requete), placeholderData: keepPreviousData });
  const numero = Number(v('page') || 1);
  const pages = Math.max(1, Math.ceil((liste.data?.count ?? 0) / 20));
  const colonnes = [
    { key: 'nom_complet', label: 'Étudiant', render: (d) => <CellulePersonne nom={d.nom_complet} secondaire={`${d.matricule} · ${d.classe_libelle}`} /> },
    { key: 'montant', label: 'Payé / dû', render: (d) => <>{fcfa(d.montant_paye)}<div className="text-xs text-muted-foreground">sur {fcfa(d.montant_du)}</div></> },
    { key: 'statut', label: 'Statut', render: (d) => (d.sans_tarif ? <BadgeStatut libelle="Sans tarif" alerte /> : <BadgeStatut libelle={STATUTS_FRAIS[d.statut]} ok={d.statut === 'paye'} />) },
    { key: 'echeance', label: 'Mensualités', render: (d) => (d.en_retard
      ? <BadgeStatut libelle={`En retard : ${fcfa(d.montant_en_retard)}`} alerte />
      : d.prochaine_echeance ? <span className="text-xs text-muted-foreground">Prochaine : {fcfa(d.prochaine_echeance.montant - d.prochaine_echeance.paye)} avant le {dateFr(d.prochaine_echeance.date_limite)}</span>
        : <span className="text-xs text-muted-foreground">—</span>) },
  ];
  return (
    <div className="space-y-4">
      <PageHeader titre="Frais étudiants" description={`${liste.data?.count ?? 0} dossier(s).`} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <form className="space-y-1.5 sm:col-span-2" onSubmit={(e) => { e.preventDefault(); choisir({ q: recherche.trim(), page: '' }); }}>
          <label htmlFor="recherche" className="text-sm font-medium">Rechercher</label>
          <div className="flex gap-2">
            <Input id="recherche" placeholder="Nom, prénom ou matricule" value={recherche} onChange={(e) => setRecherche(e.target.value)} />
            <Button type="submit" variant="outline" size="icon-lg" aria-label="Rechercher"><Search /></Button>
          </div>
        </form>
        <Selecteur id="statut" label="Statut" vide="Tous" valeur={v('statut')} onChange={(x) => choisir({ statut: x, page: '' })}
          options={Object.entries(STATUTS_FRAIS).map(([valeur, libelle]) => ({ valeur, libelle }))} />
        <Selecteur id="retard" label="Mensualités" vide="Toutes" valeur={v('retard')} onChange={(x) => choisir({ retard: x, page: '' })}
          options={[{ valeur: 'true', libelle: 'En retard' }]} />
      </div>
      <DataTable columns={colonnes} data={liste.data?.results ?? []} isLoading={liste.isLoading} isError={liste.isError}
        emptyMessage="Aucun dossier." libelleLigne={(d) => d.nom_complet} actionsEnMenu
        actionsSupplementaires={[{ libelle: 'Ouvrir le dossier', icone: Eye, onClick: (d) => navigate(`${d.id}`) }]} />
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={numero <= 1} onClick={() => choisir({ page: String(numero - 1) })}><ChevronLeft /> Précédente</Button>
          <span>Page {numero} / {pages}</span>
          <Button variant="outline" size="sm" disabled={numero >= pages} onClick={() => choisir({ page: String(numero + 1) })}>Suivante <ChevronRight /></Button>
        </div>
      )}
    </div>
  );
}
