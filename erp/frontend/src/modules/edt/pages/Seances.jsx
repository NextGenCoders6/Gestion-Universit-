/** Liste des séances : filtres, publication en masse des brouillons, conflits. */
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Plus, Send } from '@/components/ui/icons';
import { Label } from '@/components/ui/label';
import DataTable from '@/components/shared/DataTable';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import { formatDate } from '@/lib/utils';
import { jjmmaaaa } from '../lib/planning';
import * as api from '../api';
import SeanceDetailsDialog from '../components/SeanceDetailsDialog';
import SeanceFormDialog from '../components/SeanceFormDialog';
import { classesEtEcs, useAnnee, useEnseignements, usePeutGerer, useSeances } from '../hooks';
import { STATUT_COLORS, STATUT_LABELS } from '../lib/constantes';

const SELECT = 'h-9 rounded-md border border-border bg-background px-3 text-sm';

export default function Seances() {
  const peutGerer = usePeutGerer();
  const client = useQueryClient();
  const { toast } = useToast();
  const annee = useAnnee();
  const [filtres, setFiltres] = useState({ classe: '', statut: '' });
  const params = useMemo(() => ({
    ...(annee.data ? { annee: annee.data.id } : {}),
    ...(filtres.classe ? { classe: filtres.classe } : {}),
    ...(filtres.statut ? { statut: filtres.statut } : {}),
  }), [annee.data, filtres]);
  const seances = useSeances(params);
  const classes = classesEtEcs(useEnseignements(annee.data ? { annee: annee.data.id } : {}).data?.results);
  const [selection, setSelection] = useState(new Set());
  const [erreursPublication, setErreursPublication] = useState(null);
  const [formulaire, setFormulaire] = useState(null);
  const [details, setDetails] = useState(null);
  const [voirConflits, setVoirConflits] = useState(false);
  const conflits = useQuery({
    queryKey: ['edt', 'conflits', annee.data?.id],
    queryFn: () => api.listerConflits({ annee: annee.data.id }),
    enabled: voirConflits && Boolean(annee.data),
  });

  const publier = useMutation({
    mutationFn: () => api.publierEnMasse([...selection]),
    onSuccess: (r) => {
      setErreursPublication(null);
      setSelection(new Set());
      client.invalidateQueries({ queryKey: ['edt'] });
      toast({ title: r.detail });
    },
    onError: (e) => {
      const data = e?.response?.data;
      setErreursPublication(data?.erreurs?.length ? data : { detail: erreursServeur(e).global, erreurs: [] });
    },
  });

  const basculer = (id) => setSelection((s) => {
    const n = new Set(s);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });

  const colonnes = [
    ...(peutGerer ? [{
      key: 'choix', label: '',
      render: (s) => (s.statut === 'brouillon' ? (
        <input type="checkbox" className="size-4 accent-primary" checked={selection.has(s.id)} onChange={() => basculer(s.id)}
          aria-label={`Sélectionner la séance du ${jjmmaaaa(s.date_seance)}`} />
      ) : null),
    }] : []),
    { key: 'date', label: 'Date', render: (s) => `${formatDate(s.creneau_effectif.jour)} · ${s.creneau_effectif.debut}–${s.creneau_effectif.fin}` },
    { key: 'ec', label: 'EC', render: (s) => <span title={s.ec_code}>{s.ec_libelle}</span> },
    { key: 'classe_libelle', label: 'Classe' },
    { key: 'enseignant_nom', label: 'Enseignant' },
    { key: 'type_seance', label: 'Type' },
    {
      key: 'statut', label: 'Statut',
      render: (s) => <Badge variant="outline" className={`${STATUT_COLORS[s.statut]?.bg} ${STATUT_COLORS[s.statut]?.text}`}>{STATUT_LABELS[s.statut]}</Badge>,
    },
  ];

  return (
    <div className="space-y-4">
      <PageHeader titre="Séances" description={annee.data ? `Année ${annee.data.libelle}` : undefined}>
        <Button variant="outline" onClick={() => setVoirConflits((v) => !v)}>
          {voirConflits ? 'Masquer les conflits' : 'Voir les conflits'}
        </Button>
        {peutGerer && (
          <>
            <Button variant="outline" disabled={selection.size === 0 || publier.isPending} onClick={() => publier.mutate()}>
              <Send className="size-4" /> Publier la sélection{selection.size ? ` (${selection.size})` : ''}
            </Button>
            <Button onClick={() => setFormulaire({})}><Plus className="size-4" /> Nouvelle séance</Button>
          </>
        )}
      </PageHeader>

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="f-classe">Classe</Label>
          <select id="f-classe" className={SELECT} value={filtres.classe}
            onChange={(e) => setFiltres({ ...filtres, classe: e.target.value })}>
            <option value="">Toutes</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.libelle}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="f-statut">Statut</Label>
          <select id="f-statut" className={SELECT} value={filtres.statut}
            onChange={(e) => setFiltres({ ...filtres, statut: e.target.value })}>
            <option value="">Tous</option>
            {Object.entries(STATUT_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </div>
      </div>

      {erreursPublication && (
        <div role="alert" className="space-y-1 rounded-md border border-destructive/20 bg-destructive/10 p-3 text-sm text-destructive">
          <p className="font-medium">{erreursPublication.detail}</p>
          {erreursPublication.erreurs.map((m) => <p key={m}>{m}</p>)}
        </div>
      )}

      {voirConflits && (
        <div className="rounded-lg border border-border p-3">
          <p className="mb-2 text-sm font-semibold">Séances publiées en conflit</p>
          {conflits.isLoading ? <p className="text-sm text-muted-foreground">Recherche…</p>
            : conflits.data?.count ? (
              <ul className="space-y-1 text-sm">
                {conflits.data.results.map((s) => (
                  <li key={s.id}>{formatDate(s.creneau_effectif.jour)} {s.creneau_effectif.debut}–{s.creneau_effectif.fin} · {s.ec_code} · {s.classe_libelle} · {s.enseignant_nom}</li>
                ))}
              </ul>
            ) : <p className="text-sm text-muted-foreground">Aucun conflit.</p>}
          <ErreurFormulaire message={conflits.isError ? erreursServeur(conflits.error).global : null} />
        </div>
      )}

      <DataTable
        columns={colonnes}
        data={seances.data ?? []}
        isLoading={seances.isLoading}
        isError={seances.isError}
        actionsSupplementaires={[{ libelle: 'Ouvrir', onClick: (s) => setDetails(s) }]}
        emptyMessage="Aucune séance."
      />

      {formulaire && (
        <SeanceFormDialog seance={formulaire.id ? formulaire : null} onFermer={() => setFormulaire(null)} />
      )}
      <SeanceDetailsDialog seance={details} peutGerer={peutGerer} onFermer={() => setDetails(null)}
        onModifier={(s) => { setDetails(null); setFormulaire(s); }} />
    </div>
  );
}
