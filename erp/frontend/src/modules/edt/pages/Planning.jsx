/** Planning hebdomadaire : grille, filtres, création au clic, déplacement par glisser-déposer. */
import { useCallback, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Plus } from '@/components/ui/icons';
import { Label } from '@/components/ui/label';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import * as api from '../api';
import PlanningGrid from '../components/PlanningGrid';
import SeanceDetailsDialog from '../components/SeanceDetailsDialog';
import SeanceFormDialog from '../components/SeanceFormDialog';
import { classesEtEcs, useAnnee, useEnseignants, useEnseignements, usePeutGerer, useSeances } from '../hooks';
import { deplacerSeance, enHeure, enIso, evenementsDepuisSeances } from '../lib/planning';

const SELECT = 'h-9 rounded-md border border-border bg-background px-3 text-sm';

export default function Planning() {
  const peutGerer = usePeutGerer();
  const client = useQueryClient();
  const { toast } = useToast();
  const annee = useAnnee();
  const enseignants = useEnseignants();
  const classes = classesEtEcs(useEnseignements(annee.data ? { annee: annee.data.id } : {}).data?.results);
  const [semaine, setSemaine] = useState(null);
  const [filtres, setFiltres] = useState({ classe: '', enseignant: '' });
  const [formulaire, setFormulaire] = useState(null);
  const [details, setDetails] = useState(null);

  const params = useMemo(() => (semaine ? {
    date_debut: enIso(semaine.start),
    date_fin: enIso(new Date(semaine.end.getTime() - 1)),
    ...(filtres.classe ? { classe: filtres.classe } : {}),
    ...(filtres.enseignant ? { enseignant: filtres.enseignant } : {}),
  } : null), [semaine, filtres]);
  const seances = useSeances(params, { enabled: Boolean(params) });
  const evenements = useMemo(
    () => evenementsDepuisSeances(seances.data ?? [], { modifiable: peutGerer }),
    [seances.data, peutGerer],
  );

  const changerSemaine = useCallback(({ start, end }) => setSemaine({ start, end }), []);

  const deposer = async (info) => {
    const ok = await deplacerSeance(info, { modifier: api.modifierSeance, notifier: toast });
    if (ok) {
      toast({ title: 'Séance déplacée' });
      client.invalidateQueries({ queryKey: ['edt'] });
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader titre="Planning" description="Glissez une séance pour la déplacer ; cliquez sur un créneau libre pour en créer une.">
        {peutGerer && <Button onClick={() => setFormulaire({})}><Plus className="size-4" /> Nouvelle séance</Button>}
      </PageHeader>

      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label htmlFor="p-classe">Classe</Label>
          <select id="p-classe" className={SELECT} value={filtres.classe}
            onChange={(e) => setFiltres({ ...filtres, classe: e.target.value })}>
            <option value="">Toutes</option>
            {classes.map((c) => <option key={c.id} value={c.id}>{c.libelle}</option>)}
          </select>
        </div>
        <div className="space-y-1">
          <Label htmlFor="p-enseignant">Enseignant</Label>
          <select id="p-enseignant" className={SELECT} value={filtres.enseignant}
            onChange={(e) => setFiltres({ ...filtres, enseignant: e.target.value })}>
            <option value="">Tous</option>
            {(enseignants.data ?? []).map((e) => <option key={e.id} value={e.id}>{e.nom_complet}</option>)}
          </select>
        </div>
      </div>

      <PlanningGrid
        events={evenements}
        isLoading={false}
        isError={seances.isError}
        onRangeChange={changerSemaine}
        onEventClick={(info) => setDetails(info.event.extendedProps)}
        onDateClick={(info) => peutGerer && setFormulaire({
          date_seance: enIso(info.date), heure_debut: enHeure(info.date),
          classe: filtres.classe || undefined, enseignant: filtres.enseignant || undefined,
        })}
        onEventDrop={peutGerer ? deposer : undefined}
      />

      {formulaire && (
        <SeanceFormDialog seance={formulaire.id ? formulaire : null} initial={formulaire.id ? null : formulaire}
          onFermer={() => setFormulaire(null)} />
      )}
      <SeanceDetailsDialog seance={details} peutGerer={peutGerer} onFermer={() => setDetails(null)}
        onModifier={(s) => { setDetails(null); setFormulaire(s); }} />
    </div>
  );
}
