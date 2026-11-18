/** Référents de classes : enseignants chargés de l'emploi du temps de certaines classes (les L1 surtout). */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Plus } from '@/components/ui/icons';
import { Label } from '@/components/ui/label';
import DataTable from '@/components/shared/DataTable';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import useAuthStore, { aDroit } from '@/store/authStore';
import * as api from '../api';
import { useAnnee, useEnseignants } from '../hooks';

export default function Referents() {
  const estResponsable = useAuthStore((s) => aDroit(s, 'edt', 'responsable'));
  const client = useQueryClient();
  const { toast } = useToast();
  const annee = useAnnee();
  const referents = useQuery({ queryKey: ['edt', 'referents'], queryFn: api.listerReferents });
  const enseignants = useEnseignants();
  const classes = useQuery({
    queryKey: ['edt', 'classes', annee.data?.id],
    queryFn: () => api.listerClasses({ annee: annee.data.id }),
    enabled: Boolean(annee.data),
  });
  const [edition, setEdition] = useState(null);
  const [erreur, setErreur] = useState(null);

  const enregistrer = useMutation({
    mutationFn: ({ id, ...d }) => (id ? api.modifierReferent(id, d) : api.creerReferent(d)),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['edt'] }); toast({ title: 'Référent enregistré' }); setEdition(null); },
    onError: (e) => { const { champs, global } = erreursServeur(e); setErreur(Object.values(champs)[0] ?? global); },
  });
  const supprimer = useMutation({
    mutationFn: (r) => api.supprimerReferent(r.id),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['edt'] }); toast({ title: 'Référent retiré' }); },
  });

  const ouvrir = (r) => {
    setErreur(null);
    setEdition(r ? { id: r.id, enseignant: String(r.enseignant), classes: r.classes } : { enseignant: '', classes: [] });
  };
  const basculer = (id) => setEdition((e) => ({
    ...e, classes: e.classes.includes(id) ? e.classes.filter((c) => c !== id) : [...e.classes, id],
  }));

  return (
    <div className="space-y-4">
      <PageHeader titre="Référents de classes" description="Ils gèrent l’emploi du temps de leurs classes sans être chefs de département.">
        {estResponsable && <Button onClick={() => ouvrir(null)}><Plus className="size-4" /> Nouveau référent</Button>}
      </PageHeader>
      <DataTable
        columns={[
          { key: 'enseignant_nom', label: 'Enseignant' },
          { key: 'classes_libelles', label: 'Classes', render: (r) => r.classes_libelles.join(', ') || '—' },
        ]}
        data={referents.data ?? []}
        isLoading={referents.isLoading}
        isError={referents.isError}
        onEdit={estResponsable ? ouvrir : undefined}
        onDelete={estResponsable ? (r) => supprimer.mutate(r) : undefined}
        libelleLigne={(r) => r.enseignant_nom}
        emptyMessage="Aucun référent."
      />
      {edition && (
        <FormModal open onClose={() => setEdition(null)} title={edition.id ? 'Modifier le référent' : 'Nouveau référent'}
          isPending={enregistrer.isPending}
          onConfirm={() => enregistrer.mutate({ id: edition.id, enseignant: Number(edition.enseignant), classes: edition.classes })}>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="ref-enseignant">Enseignant</Label>
              <select id="ref-enseignant" className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm"
                value={edition.enseignant} onChange={(e) => setEdition({ ...edition, enseignant: e.target.value })}>
                <option value="">—</option>
                {(enseignants.data ?? []).map((e) => <option key={e.id} value={e.id}>{e.nom_complet}</option>)}
              </select>
            </div>
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">Classes ({annee.data?.libelle})</legend>
              {(classes.data ?? []).map((c) => (
                <label key={c.id} className="flex items-center gap-2 text-sm">
                  <input type="checkbox" className="size-4 accent-primary" checked={edition.classes.includes(c.id)}
                    onChange={() => basculer(c.id)} />
                  {c.libelle}
                </label>
              ))}
            </fieldset>
            <ErreurFormulaire message={erreur} />
          </div>
        </FormModal>
      )}
    </div>
  );
}
