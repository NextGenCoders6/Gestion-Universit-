/** Grille de tarifs par année et niveau, avec la modalité de paiement mensuelle et l'aperçu de l'échéancier. */
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Pencil, Plus, Trash2 } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '@/modules/finance/api';
import { echeancier } from '@/modules/finance/lib/echeancier';
import { dateFr, fcfa } from '@/modules/finance/lib/format';

const CHAMPS = ['annee', 'parcours', 'montant', 'nombre_mensualites', 'premier_mois', 'jour_echeance'];

function TarifDialog({ tarif, annees, parcours, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: tarif
    ? { ...tarif, annee: String(tarif.annee), parcours: String(tarif.parcours), montant: String(Number(tarif.montant)) }
    : { annee: '', parcours: '', montant: '', nombre_mensualites: 10, premier_mois: '', jour_echeance: 5 } });
  const v = useWatch({ control: form.control });
  const annee = annees.find((a) => String(a.id) === String(v.annee));
  const premier = v.premier_mois || (annee ? `${annee.date_debut.slice(0, 4)}-10` : '');
  const apercu = echeancier(v.montant, v.nombre_mensualites, premier, Number(v.jour_echeance) || 5);
  const enregistrer = useMutation({
    mutationFn: (x) => {
      const d = { annee: Number(x.annee), parcours: Number(x.parcours), montant: x.montant, nombre_mensualites: Number(x.nombre_mensualites),
        premier_mois: x.premier_mois || '', jour_echeance: Number(x.jour_echeance) };
      return tarif ? api.modifierTarif(tarif.id, d) : api.creerTarif(d);
    },
    onSuccess: () => { client.invalidateQueries({ queryKey: ['tarifs'] }); toast({ title: 'Tarif enregistré', description: 'Les dossiers de frais concernés sont recalculés.' }); onFermer(); },
    onError: (e) => setErreurs(erreursServeur(e, CHAMPS)),
  });
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  const r = form.register;
  return (
    <FormModal open onClose={onFermer} title={tarif ? 'Modifier le tarif' : 'Nouveau tarif'} onConfirm={form.handleSubmit((x) => enregistrer.mutate(x))} isPending={enregistrer.isPending}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="annee" label="Année" type="select" requis register={r} erreur={erreur('annee')} options={annees.map((a) => ({ valeur: String(a.id), libelle: a.libelle }))} />
        <Champ nom="parcours" label="Niveau" type="select" requis register={r} erreur={erreur('parcours')}
          options={parcours.filter((p) => p.type_parcours !== 'Doctorat').map((p) => ({ valeur: String(p.id), libelle: p.code }))} />
        <Champ nom="montant" label="Montant de l’année (FCFA)" type="number" requis register={r} erreur={erreur('montant')} />
        <Champ nom="nombre_mensualites" label="Nombre de mensualités" type="number" requis register={r} erreur={erreur('nombre_mensualites')} />
        <Champ nom="premier_mois" label="Premier mois couvert" register={r} erreur={erreur('premier_mois')} aide="AAAA-MM ; octobre de l’année si vide." />
        <Champ nom="jour_echeance" label="Jour d’échéance" type="number" requis register={r} erreur={erreur('jour_echeance')} aide="La mensualité d’un mois est due ce jour-là du mois suivant (1 à 28)." />
        <div className="rounded-md bg-muted/40 p-3 text-sm sm:col-span-2">
          {apercu.length === 0 ? <span className="text-muted-foreground">Renseignez le montant et l’année pour voir l’échéancier.</span> : (
            <>
              <p className="font-medium">{apercu.length} mensualités de {fcfa(apercu[0].montant)}{apercu[apercu.length - 1].montant !== apercu[0].montant && ` (la dernière : ${fcfa(apercu[apercu.length - 1].montant)})`}</p>
              <p className="text-xs text-muted-foreground">{apercu.map((l) => `${l.mois} → ${dateFr(l.date_limite)}`).join(' · ')}</p>
            </>
          )}
        </div>
        <div className="sm:col-span-2"><ErreurFormulaire message={erreurs.global} /></div>
      </form>
    </FormModal>
  );
}

export default function Tarifs() {
  const client = useQueryClient();
  const { toast } = useToast();
  const tarifs = useQuery({ queryKey: ['tarifs'], queryFn: () => api.listerTarifs() });
  const annees = useQuery({ queryKey: ['annees'], queryFn: api.listerAnnees });
  const parcours = useQuery({ queryKey: ['parcours'], queryFn: api.listerParcours });
  const [edition, setEdition] = useState(null);
  const supprimer = async (t) => {
    if (!(await confirmer({ titre: `Supprimer le tarif ${t.parcours_code} ${t.annee_libelle} ?`, description: 'Les dossiers déjà créés gardent leur montant.', libelleConfirmer: 'Supprimer', destructif: true }))) return;
    try { await api.supprimerTarif(t.id); client.invalidateQueries({ queryKey: ['tarifs'] }); } catch (e) {
      toast({ title: 'Suppression impossible', description: erreursServeur(e).global, variant: 'destructive' });
    }
  };
  return (
    <div className="space-y-4">
      <PageHeader titre="Tarifs" description="Frais de scolarité par année et par niveau, payables par mensualités.">
        <Button onClick={() => setEdition('nouveau')}><Plus /> Nouveau tarif</Button>
      </PageHeader>
      <div className="carte overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-[11px] uppercase tracking-wider text-muted-foreground"><tr>
            <th className="px-3 py-2 text-left">Année</th><th className="px-3 py-2 text-left">Niveau</th><th className="px-3 py-2 text-right">Montant</th><th className="px-3 py-2 text-left">Modalité</th><th className="px-2 py-2" />
          </tr></thead>
          <tbody>
            {(tarifs.data ?? []).length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucun tarif.</td></tr>}
            {(tarifs.data ?? []).map((t) => (
              <tr key={t.id} className="border-t border-border">
                <td className="px-3 py-1.5">{t.annee_libelle}</td><td className="px-3 py-1.5 font-medium">{t.parcours_code}</td>
                <td className="px-3 py-1.5 text-right">{fcfa(t.montant)}</td>
                <td className="px-3 py-1.5 text-xs">{t.nombre_mensualites} × {fcfa(t.echeancier?.[0]?.montant)} à partir de {t.premier_mois}, le {t.jour_echeance} du mois suivant</td>
                <td className="px-2 py-1.5 text-right whitespace-nowrap">
                  <Button size="icon-sm" variant="ghost" aria-label={`Modifier ${t.parcours_code}`} onClick={() => setEdition(t)}><Pencil /></Button>
                  <Button size="icon-sm" variant="ghost" aria-label={`Supprimer ${t.parcours_code}`} className="text-destructive" onClick={() => supprimer(t)}><Trash2 /></Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {edition && <TarifDialog tarif={edition === 'nouveau' ? null : edition} annees={annees.data ?? []} parcours={parcours.data ?? []} onFermer={() => setEdition(null)} />}
    </div>
  );
}
