/** Liste paginée d'enseignants ou de membres du personnel : recherche, filtres, ajout. */
import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChevronLeft, ChevronRight, Eye, Plus, Search } from '@/components/ui/icons';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import Selecteur from '@/components/shared/Selecteur';
import { useEstResponsableRH } from '../hooks';
import { libelleContrat } from '../lib/format';
import NouvelleFicheDialog from './NouvelleFicheDialog';
import { CellulePersonne } from '@/components/shared/AvatarInitiales';
import Pastille from '@/components/shared/Pastille';

export default function ListeFiches({ role, titre, lister, colonnes, filtres = [] }) {
  const navigate = useNavigate();
  const responsable = useEstResponsableRH();
  const [params, setParams] = useSearchParams();
  const valeur = (c) => params.get(c) ?? '';
  const choisir = (modif) => {
    const suivant = new URLSearchParams(params);
    for (const [c, v] of Object.entries(modif)) { if (v) suivant.set(c, v); else suivant.delete(c); }
    setParams(suivant, { replace: true });
  };
  const [recherche, setRecherche] = useState(valeur('q'));
  const [creation, setCreation] = useState(false);
  const requete = { q: valeur('q') || undefined, actif: valeur('actif') || undefined, page: valeur('page') || 1,
    ...Object.fromEntries(filtres.map((f) => [f.cle, valeur(f.cle) || undefined])) };
  const liste = useQuery({ queryKey: ['rh', role, requete], queryFn: () => lister(requete), placeholderData: keepPreviousData });
  const numero = Number(valeur('page') || 1);
  const pages = Math.max(1, Math.ceil((liste.data?.count ?? 0) / 20));

  const toutes = [
    { key: 'nom_complet', label: 'Nom et prénom', render: (f) => <CellulePersonne nom={f.nom_complet} secondaire={f.matricule} /> },
    ...colonnes,
    { key: 'contrat', label: 'Contrat', render: (f) => (
      <Pastille ton={f.actif ? 'vert' : 'gris'}>{libelleContrat(f.contrat_en_cours)}</Pastille>) },
  ];

  return (
    <div className="space-y-4">
      <PageHeader titre={titre} description={`${liste.data?.count ?? 0} fiche(s).`}>
        {responsable && (
          <Button onClick={() => setCreation(true)}><Plus /> {role === 'enseignant' ? 'Nouvel enseignant' : 'Nouveau membre'}</Button>
        )}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <form className="space-y-1.5 sm:col-span-2" onSubmit={(e) => { e.preventDefault(); choisir({ q: recherche.trim(), page: '' }); }}>
          <label htmlFor="recherche" className="text-sm font-medium">Rechercher</label>
          <div className="flex gap-2">
            <Input id="recherche" placeholder="Nom, prénom ou matricule" value={recherche} onChange={(e) => setRecherche(e.target.value)} />
            <Button type="submit" variant="outline" size="icon-lg" aria-label="Rechercher"><Search /></Button>
          </div>
        </form>
        {filtres.map((f) => (
          <Selecteur key={f.cle} id={`filtre-${f.cle}`} label={f.label} vide={f.vide} valeur={valeur(f.cle)} options={f.options}
            onChange={(v) => choisir({ [f.cle]: v, page: '' })} />
        ))}
        <Selecteur id="filtre-actif" label="Contrat" vide="Tous" valeur={valeur('actif')}
          options={[{ valeur: 'true', libelle: 'Contrat en cours' }, { valeur: 'false', libelle: 'Sans contrat en cours' }]}
          onChange={(v) => choisir({ actif: v, page: '' })} />
      </div>
      <DataTable columns={toutes} data={liste.data?.results ?? []} isLoading={liste.isLoading} isError={liste.isError}
        emptyMessage="Aucune fiche ne correspond." libelleLigne={(f) => f.nom_complet} actionsEnMenu
        actionsSupplementaires={[{ libelle: 'Ouvrir la fiche', icone: Eye, onClick: (f) => navigate(`${f.id}`) }]} />
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={numero <= 1} onClick={() => choisir({ page: String(numero - 1) })}><ChevronLeft /> Précédente</Button>
          <span>Page {numero} / {pages}</span>
          <Button variant="outline" size="sm" disabled={numero >= pages} onClick={() => choisir({ page: String(numero + 1) })}>Suivante <ChevronRight /></Button>
        </div>
      )}
      {creation && <NouvelleFicheDialog role={role} onFermer={() => setCreation(false)} onCree={(f) => navigate(`${f.id}`)} />}
    </div>
  );
}
