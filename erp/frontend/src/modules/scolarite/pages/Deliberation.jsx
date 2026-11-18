/** Délibération d'une classe pour un semestre : calcul à la volée, enregistrement, Excel et procès-verbal A3. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Printer } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Selecteur from '../components/Selecteur';
import { useClasses, useSelection } from '../hooks';
import { couleurDecision, note, optionsClasses } from '../lib/format';

export default function Deliberation() {
  const { toast } = useToast();
  const client = useQueryClient();
  const classes = useClasses();
  const [{ classe, semestre }, choisir] = useSelection(['classe', 'semestre']);
  const classeChoisie = (classes.data ?? []).find((c) => String(c.id) === classe);
  const params = { classe, semestre };
  const resultat = useQuery({
    queryKey: ['scolarite', 'deliberation', classe, semestre],
    queryFn: () => api.deliberation(params),
    enabled: Boolean(classe && semestre),
  });
  const d = resultat.data;

  const enregistrer = useMutation({
    mutationFn: () => api.enregistrerDeliberation({ classe: Number(classe), semestre }),
    onSuccess: (r) => {
      client.setQueryData(['scolarite', 'deliberation', classe, semestre], r);
      toast({ title: 'Délibération enregistrée', description: `${r.lignes.length} résultat(s) enregistré(s).` });
    },
    onError: (e) => toast({ title: 'Enregistrement impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const rouvrir = useMutation({
    mutationFn: () => api.rouvrirDeliberation(params),
    onSuccess: (r) => {
      client.setQueryData(['scolarite', 'deliberation', classe, semestre], r);
      client.invalidateQueries({ queryKey: ['scolarite', 'saisie'] });
      toast({ title: 'Délibération rouverte', description: 'Les notes du semestre sont de nouveau modifiables.' });
    },
    onError: (e) => toast({ title: 'Réouverture impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const telecharger = async (chemin, nom) => {
    try { await api.telecharger(chemin, params, nom); } catch (e) {
      toast({ title: 'Téléchargement impossible', description: await api.messageErreurBlob(e), variant: 'destructive' });
    }
  };

  const valider = async () => {
    const ok = await confirmer({
      titre: d?.deliberee ? 'Mettre à jour la délibération ?' : 'Enregistrer la délibération ?',
      description: d?.ecs_non_saisis ? `${d.ecs_non_saisis} note(s) ne sont pas saisies : elles seront ignorées du calcul.`
        : 'Les résultats deviennent officiels : relevés et espace étudiant les afficheront.',
      libelleConfirmer: 'Enregistrer',
    });
    if (ok) enregistrer.mutate();
  };

  return (
    <div className="space-y-4">
      <PageHeader titre="Délibérations" description="Résultats calculés en direct ; enregistrez-les pour les rendre officiels.">
        {d && (
          <>
            <Button variant="outline" onClick={() => telecharger('/scolarite/deliberation/excel/', `deliberation-${semestre}.xlsx`)}>
              <FileSpreadsheet /> Excel
            </Button>
            <Button variant="outline" onClick={() => telecharger('/scolarite/matrice-a3.pdf', `pv-${semestre}.pdf`)}>
              <Printer /> Procès-verbal A3
            </Button>
            {d.deliberee ? (
              <Button variant="outline" disabled={rouvrir.isPending || d.archivee} onClick={async () => {
                if (await confirmer({ titre: 'Rouvrir la délibération ?', destructif: true, libelleConfirmer: 'Rouvrir',
                  description: 'Les résultats enregistrés sont retirés (relevés et espace étudiant) jusqu’à la prochaine délibération.' })) rouvrir.mutate();
              }}>Rouvrir la délibération</Button>
            ) : (
              <Button onClick={valider} disabled={enregistrer.isPending || d.archivee || !d.lignes.length}>
                <CheckCircle2 /> Enregistrer la délibération
              </Button>
            )}
          </>
        )}
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <Selecteur id="classe" label="Classe" valeur={classe} options={optionsClasses(classes.data)}
          onChange={(v) => choisir({ classe: v, semestre: '' })} />
        <Selecteur id="semestre" label="Semestre" valeur={semestre}
          options={(classeChoisie?.semestres ?? []).map((s) => ({ valeur: s, libelle: s }))}
          onChange={(v) => choisir({ semestre: v })} />
      </div>
      {resultat.isLoading && <p className="text-sm text-muted-foreground">Calcul en cours…</p>}
      {resultat.isError && <p className="text-sm text-destructive">{erreursServeur(resultat.error).global}</p>}
      {d && (
        <>
          <div className="flex flex-wrap gap-2 text-sm">
            {d.deliberee
              ? <span className="rounded-md bg-primary/10 px-2 py-1 text-primary">Délibérée le {new Date(d.delibere_le).toLocaleString('fr-FR')}</span>
              : <span className="rounded-md bg-muted px-2 py-1 text-muted-foreground">Pas encore délibérée</span>}
            {d.ecs_non_saisis > 0 && (
              <span role="alert" className="flex items-center gap-1 rounded-md bg-amber-100 px-2 py-1 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200">
                <AlertTriangle className="size-4" /> {d.ecs_non_saisis} notes non saisies : ignorées du calcul (pas comptées 0).
              </span>
            )}
          </div>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="px-2 py-2">Rang</th>
                  <th className="px-3 py-2 text-left">Étudiant</th>
                  {d.ues.map((u) => <th key={u.id} className="px-2 py-2" title={u.libelle}>{u.code}</th>)}
                  <th className="px-2 py-2">Moyenne</th>
                  <th className="px-2 py-2">Crédits</th>
                  <th className="px-2 py-2">Décision</th>
                </tr>
              </thead>
              <tbody>
                {d.lignes.length === 0 && (
                  <tr><td colSpan={d.ues.length + 5} className="px-3 py-8 text-center text-muted-foreground">Aucun étudiant inscrit.</td></tr>
                )}
                {d.lignes.map((l) => (
                  <tr key={l.inscription} className="border-t border-border">
                    <td className="px-2 py-1.5 text-center">{l.rang}</td>
                    <td className="px-3 py-1.5">
                      <div className="font-medium">{l.nom_complet}</div>
                      <div className="text-xs text-muted-foreground">
                        {l.matricule}{l.ecs_non_saisis.length > 0 && ` · non saisi : ${l.ecs_non_saisis.join(', ')}`}
                      </div>
                    </td>
                    {l.ues.map((u) => (
                      <td key={u.id} className={`px-2 py-1.5 text-center ${u.validee ? '' : 'text-destructive'}`}>{note(u.moyenne_ue)}</td>
                    ))}
                    <td className="px-2 py-1.5 text-center font-semibold">{note(l.moyenne)}</td>
                    <td className="px-2 py-1.5 text-center">{l.credits_valides}/{l.credits_totaux}</td>
                    <td className="px-2 py-1.5 text-center">
                      <span className={`rounded px-2 py-0.5 text-xs font-semibold ${couleurDecision(l.decision)}`}>{l.decision}</span>
                      {l.mention !== 'NÉANT' && <div className="text-xs text-muted-foreground">{l.mention}</div>}
                      {l.eliminatoire && <div className="text-xs text-destructive">note éliminatoire</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
