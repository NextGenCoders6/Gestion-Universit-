/** Liste des étudiants du périmètre : recherche, filtre par classe, ajout avec inscription. */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ChevronLeft, ChevronRight, Eye, Plus, Search } from '@/components/ui/icons';
import DataTable from '@/components/shared/DataTable';
import PageHeader from '@/components/shared/PageHeader';
import * as api from '../api';
import NouvelEtudiantDialog from '../components/NouvelEtudiantDialog';
import Selecteur from '../components/Selecteur';
import { useClasses, useEstSecretariat, useSelection } from '../hooks';
import { optionsClasses, STATUTS_ETUDIANT } from '../lib/format';

const libelleStatut = (s) => STATUTS_ETUDIANT.find((x) => x.valeur === s)?.libelle ?? s;

export default function Etudiants() {
  const navigate = useNavigate();
  const secretariat = useEstSecretariat();
  const classes = useClasses();
  const [{ q, classe, page }, choisir] = useSelection(['q', 'classe', 'page']);
  const [recherche, setRecherche] = useState(q);
  const [creation, setCreation] = useState(false);
  const params = { q: q || undefined, classe: classe || undefined, page: page || 1 };
  const liste = useQuery({ queryKey: ['scolarite', 'etudiants', params], queryFn: () => api.listerEtudiants(params),
    placeholderData: keepPreviousData });
  const numero = Number(page || 1);
  const pages = Math.max(1, Math.ceil((liste.data?.count ?? 0) / 20));

  const colonnes = [
    { key: 'matricule', label: 'Matricule' },
    { key: 'nom_complet', label: 'Nom et prénom' },
    { key: 'classe', label: 'Classe', render: (e) => e.inscription_courante?.classe_libelle ?? '—' },
    { key: 'statut', label: 'Statut', render: (e) => (
      <Badge variant={e.statut === 'actif' ? 'secondary' : 'outline'}>{libelleStatut(e.statut)}</Badge>) },
    { key: 'compte', label: 'Compte', render: (e) => (e.a_un_compte ? 'Activé' : 'Non activé') },
  ];

  return (
    <div className="space-y-4">
      <PageHeader titre="Étudiants" description={`${liste.data?.count ?? 0} étudiant(s) dans votre périmètre.`}>
        {secretariat && <Button onClick={() => setCreation(true)}><Plus /> Nouvel étudiant</Button>}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-[1fr_280px] lg:max-w-3xl">
        <form className="space-y-1.5" onSubmit={(e) => { e.preventDefault(); choisir({ q: recherche.trim(), page: '' }); }}>
          <label htmlFor="recherche" className="text-sm font-medium">Rechercher</label>
          <div className="flex gap-2">
            <Input id="recherche" placeholder="Nom, prénom ou matricule" value={recherche} onChange={(e) => setRecherche(e.target.value)} />
            <Button type="submit" variant="outline" size="icon-lg" aria-label="Rechercher"><Search /></Button>
          </div>
        </form>
        <Selecteur id="filtre-classe" label="Classe" vide="Toutes les classes" valeur={classe}
          options={optionsClasses(classes.data)} onChange={(v) => choisir({ classe: v, page: '' })} />
      </div>
      <DataTable columns={colonnes} data={liste.data?.results ?? []} isLoading={liste.isLoading} isError={liste.isError}
        emptyMessage="Aucun étudiant ne correspond." libelleLigne={(e) => e.nom_complet}
        actionsSupplementaires={[{ libelle: 'Ouvrir la fiche', icone: Eye, onClick: (e) => navigate(`${e.id}`) }]} actionsEnMenu />
      {pages > 1 && (
        <div className="flex items-center justify-end gap-2 text-sm">
          <Button variant="outline" size="sm" disabled={numero <= 1} onClick={() => choisir({ page: String(numero - 1) })}>
            <ChevronLeft /> Précédente
          </Button>
          <span>Page {numero} / {pages}</span>
          <Button variant="outline" size="sm" disabled={numero >= pages} onClick={() => choisir({ page: String(numero + 1) })}>
            Suivante <ChevronRight />
          </Button>
        </div>
      )}
      {creation && <NouvelEtudiantDialog onFermer={() => setCreation(false)} onCree={(e) => navigate(`${e.id}`)} />}
    </div>
  );
}
