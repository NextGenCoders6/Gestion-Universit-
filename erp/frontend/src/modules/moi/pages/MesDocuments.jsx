import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Download, Upload } from '@/components/ui/icons';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import DataTable from '@/components/shared/DataTable';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';

const SELECT = 'h-9 w-full rounded-md border border-border bg-background px-3 text-sm';
const TYPES = { cours: 'Cours', td: 'TD', tp: 'TP', autre: 'Autre' };

export default function MesDocuments() {
  const client = useQueryClient();
  const { toast } = useToast();
  const documents = useQuery({ queryKey: ['moi', 'documents'], queryFn: api.mesDocuments });
  const affectations = useQuery({ queryKey: ['moi', 'enseignements'], queryFn: api.mesEnseignements });
  const [saisie, setSaisie] = useState({ affectation: '', titre: '', type_doc: 'cours', fichier: null });
  const [erreur, setErreur] = useState(null);

  const deposer = useMutation({
    mutationFn: () => {
      const a = affectations.data.find((x) => String(x.id) === saisie.affectation);
      const fd = new FormData();
      fd.append('titre', saisie.titre);
      fd.append('type_doc', saisie.type_doc);
      fd.append('ec', a.ec);
      fd.append('classe', a.classe);
      fd.append('fichier', saisie.fichier);
      return api.deposerDocument(fd);
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['moi', 'documents'] });
      toast({ title: 'Document déposé' });
      setSaisie({ affectation: '', titre: '', type_doc: 'cours', fichier: null });
      setErreur(null);
    },
    onError: (e) => { const { champs, global } = erreursServeur(e); setErreur(Object.values(champs)[0] ?? global); },
  });

  const complet = saisie.affectation && saisie.titre.trim() && saisie.fichier;

  return (
    <div className="space-y-4">
      <PageHeader titre="Mes documents" description="Supports de cours déposés pour vos classes (PDF, Word, Excel, PowerPoint, texte)." />
      <form className="grid gap-3 rounded-lg border border-border bg-card p-4 md:grid-cols-2"
        onSubmit={(e) => { e.preventDefault(); if (complet) deposer.mutate(); }}>
        <div className="space-y-1.5">
          <Label htmlFor="doc-ens">Enseignement</Label>
          <select id="doc-ens" className={SELECT} value={saisie.affectation}
            onChange={(e) => setSaisie({ ...saisie, affectation: e.target.value })}>
            <option value="">—</option>
            {(affectations.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.ec_code} · {a.classe_libelle}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="doc-titre">Titre</Label>
          <Input id="doc-titre" value={saisie.titre} onChange={(e) => setSaisie({ ...saisie, titre: e.target.value })} />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="doc-type">Type</Label>
          <select id="doc-type" className={SELECT} value={saisie.type_doc}
            onChange={(e) => setSaisie({ ...saisie, type_doc: e.target.value })}>
            {Object.entries(TYPES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="doc-fichier">Fichier</Label>
          <Input id="doc-fichier" type="file" accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt"
            onChange={(e) => setSaisie({ ...saisie, fichier: e.target.files?.[0] ?? null })} />
        </div>
        <div className="md:col-span-2 space-y-2">
          <ErreurFormulaire message={erreur} />
          <Button type="submit" disabled={!complet || deposer.isPending}><Upload className="size-4" /> Déposer</Button>
        </div>
      </form>
      <DataTable
        columns={[
          { key: 'titre', label: 'Titre' },
          { key: 'type_doc', label: 'Type', render: (d) => TYPES[d.type_doc] },
          { key: 'ec_code', label: 'EC' },
          { key: 'classe_libelle', label: 'Classe' },
          { key: 'created_at', label: 'Déposé le', render: (d) => new Date(d.created_at).toLocaleDateString('fr-FR') },
        ]}
        data={documents.data ?? []}
        isLoading={documents.isLoading}
        isError={documents.isError}
        actionsSupplementaires={[{ libelle: 'Télécharger', icone: Download, onClick: (d) => api.telechargerDocument(d) }]}
        emptyMessage="Aucun document déposé."
      />
    </div>
  );
}
