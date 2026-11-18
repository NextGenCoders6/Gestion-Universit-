/** Une carte par EC × classe : quota, avancement, affectations des enseignants. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { AlertTriangle, Pencil, Plus, Trash2 } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import BarreAvancement, { LegendeAvancement } from '../components/BarreAvancement';
import { useAnnee, useEnseignants, useEnseignements, usePeutGerer } from '../hooks';

const pct = (v, max) => (max ? Math.min(100, Math.round((v / max) * 100)) : 0);
const CHAMPS = ['enseignant', 'type_seance', 'heures_prevues', 'hors_departement'];

function AffectationDialog({ ligne, affectation, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const enseignants = useEnseignants();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({
    defaultValues: {
      enseignant: affectation ? String(affectation.enseignant) : '',
      type_seance: affectation?.type_seance ?? '',
      heures_prevues: affectation ? String(affectation.heures_prevues) : '',
      hors_departement: affectation?.hors_departement ?? false,
    },
  });
  const enregistrer = useMutation({
    mutationFn: (v) => {
      const d = { enseignant: Number(v.enseignant), type_seance: v.type_seance || null,
        heures_prevues: Number(v.heures_prevues), hors_departement: Boolean(v.hors_departement) };
      return affectation ? api.modifierAffectation(affectation.id, d)
        : api.creerAffectation({ ...d, ec: ligne.ec, classe: ligne.classe });
    },
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ['edt'] });
      toast({ title: 'Affectation enregistrée', description: r.warnings?.[0] });
      onFermer();
    },
    onError: (e) => setErreurs(erreursServeur(e, CHAMPS)),
  });
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;

  return (
    <FormModal open onClose={onFermer} title={`Affectation — ${ligne.ec_code} · ${ligne.classe_libelle}`}
      onConfirm={form.handleSubmit((v) => enregistrer.mutate(v))} isPending={enregistrer.isPending}>
      <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="enseignant" label="Enseignant" type="select" requis register={form.register} erreur={erreur('enseignant')}
          options={(enseignants.data ?? []).map((e) => ({ valeur: String(e.id), libelle: `${e.nom_complet} (${e.departement_libelle})` }))} />
        <Champ nom="type_seance" label="Type de séance" type="select" vide="Tous types" register={form.register}
          erreur={erreur('type_seance')} options={['CM', 'TD', 'TP'].map((t) => ({ valeur: t, libelle: t }))} />
        <Champ nom="heures_prevues" label="Heures prévues" type="number" requis register={form.register}
          erreur={erreur('heures_prevues')} />
        <Champ nom="hors_departement" label="Enseignant d’un autre département" type="checkbox" register={form.register} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function Enseignements() {
  const peutGerer = usePeutGerer();
  const client = useQueryClient();
  const { toast } = useToast();
  const annee = useAnnee();
  const lignes = useEnseignements(annee.data ? { annee: annee.data.id } : {});
  const [edition, setEdition] = useState(null);

  const supprimer = useMutation({
    mutationFn: (id) => api.supprimerAffectation(id),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['edt'] }); toast({ title: 'Affectation supprimée' }); },
    onError: (e) => toast({ title: 'Suppression impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  return (
    <div className="space-y-4">
      <PageHeader titre="Enseignements" description="Volume de chaque EC dans chaque classe et répartition entre enseignants.">
        <LegendeAvancement />
      </PageHeader>
      {lignes.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {lignes.data?.results?.length === 0 && <p className="text-sm text-muted-foreground">Aucun enseignement dans votre périmètre.</p>}
      <div className="grid gap-3 lg:grid-cols-2">
        {(lignes.data?.results ?? []).map((l) => {
          const totalAffecte = l.affectations.reduce((s, a) => s + a.heures_prevues, 0);
          return (
            <article key={`${l.ec}-${l.classe}`} className="space-y-3 rounded-lg border border-border bg-card p-4">
              <header className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-semibold text-foreground">{l.ec_code} — {l.ec_libelle}</h3>
                  <p className="text-xs text-muted-foreground">{l.classe_libelle} · {l.semestre} · {l.departement_libelle}</p>
                </div>
                <Badge variant="secondary">{l.heures_max} h</Badge>
              </header>
              <BarreAvancement faites={pct(l.heures_effectuees, l.heures_max)} planifiees={pct(l.heures_consommees, l.heures_max)}
                label={`Avancement de ${l.ec_code}`} valeur={`${l.heures_effectuees} h faites, ${l.heures_consommees} h planifiées sur ${l.heures_max} h`} />
              <p className="text-xs text-muted-foreground">{l.heures_effectuees} h faites · {l.heures_consommees} h planifiées · {l.heures_max} h prévues</p>
              {totalAffecte > l.heures_max && (
                <p className="flex items-center gap-1 text-xs font-medium text-amber-700">
                  <AlertTriangle className="size-3.5" /> Affectations ({totalAffecte} h) au-delà du volume de l’EC.
                </p>
              )}
              <ul className="space-y-1">
                {l.affectations.map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-2 rounded-md bg-muted/40 px-2 py-1 text-sm">
                    <span>{a.enseignant_nom} · {a.type_seance ?? 'tous types'} · {a.heures_consommees}/{a.heures_prevues} h{a.hors_departement ? ' · hors département' : ''}</span>
                    {peutGerer && (
                      <span className="flex gap-1">
                        <Button size="icon" variant="ghost" className="size-7" aria-label="Modifier l’affectation"
                          onClick={() => setEdition({ ligne: l, affectation: a })}><Pencil className="size-3.5" /></Button>
                        <Button size="icon" variant="ghost" className="size-7" aria-label="Supprimer l’affectation"
                          onClick={async () => {
                            if (await confirmer({ titre: 'Supprimer cette affectation ?', libelleConfirmer: 'Supprimer', destructif: true })) {
                              supprimer.mutate(a.id);
                            }
                          }}><Trash2 className="size-3.5" /></Button>
                      </span>
                    )}
                  </li>
                ))}
                {l.affectations.length === 0 && <li className="text-xs text-muted-foreground">Aucun enseignant affecté.</li>}
              </ul>
              {peutGerer && (
                <Button size="sm" variant="outline" onClick={() => setEdition({ ligne: l, affectation: null })}>
                  <Plus className="size-4" /> Affecter un enseignant
                </Button>
              )}
            </article>
          );
        })}
      </div>
      {edition && <AffectationDialog {...edition} onFermer={() => setEdition(null)} />}
    </div>
  );
}
