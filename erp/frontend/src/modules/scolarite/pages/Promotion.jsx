/** Passage à l'année suivante : promotion dans la filière (L2 et plus), orientation par filière pour la L1. */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { ArrowRightCircle } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Selecteur from '@/components/shared/Selecteur';
import { useClasses, useSelection } from '../hooks';
import { couleurDecision, optionsClasses } from '../lib/format';

export default function Promotion() {
  const { toast } = useToast();
  const client = useQueryClient();
  const classes = useClasses();
  const [{ classe }, choisir] = useSelection(['classe']);
  const classeChoisie = (classes.data ?? []).find((c) => String(c.id) === classe);
  const l1 = classeChoisie?.niveau === 'L1';
  const donnees = useQuery({
    queryKey: ['scolarite', l1 ? 'orientation' : 'promotion', classe],
    queryFn: () => (l1 ? api.orientation({ classe }) : api.promotion({ classe })),
    enabled: Boolean(classeChoisie),
  });
  const [coches, setCoches] = useState({});
  const [filieres, setFilieres] = useState({});
  const [bilan, setBilan] = useState(null);

  const appliquer = useMutation({
    mutationFn: () => (l1
      ? api.appliquerOrientation({ classe: Number(classe), choix: Object.fromEntries(Object.entries(filieres).filter(([, f]) => f).map(([e, f]) => [e, Number(f)])) })
      : api.appliquerPromotion({ classe: Number(classe), etudiants: Object.keys(coches).filter((k) => coches[k]).map(Number) })),
    onSuccess: (r) => {
      setBilan(r);
      setCoches({});
      setFilieres({});
      client.invalidateQueries({ queryKey: ['scolarite'] });
      toast({ title: `${r.promus} étudiant(s) inscrit(s) pour l'année suivante` });
    },
    onError: (e) => toast({ title: 'Passage impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const etudiants = donnees.data?.etudiants ?? [];
  const nbChoisis = l1 ? Object.values(filieres).filter(Boolean).length : Object.values(coches).filter(Boolean).length;
  const valider = async () => {
    if (await confirmer({ titre: `Inscrire ${nbChoisis} étudiant(s) pour l'année suivante ?`,
      description: 'Leur inscription actuelle sera clôturée.', libelleConfirmer: 'Inscrire' })) appliquer.mutate();
  };

  return (
    <div className="space-y-4">
      <PageHeader titre="Promotion et orientation"
        description="Inscrit les étudiants choisis dans la classe du niveau suivant, l'année suivante. Les deux semestres doivent être délibérés.">
        <Button onClick={valider} disabled={!nbChoisis || appliquer.isPending}><ArrowRightCircle /> Inscrire ({nbChoisis})</Button>
      </PageHeader>
      <Selecteur id="classe" label="Classe" valeur={classe} options={optionsClasses(classes.data)} className="max-w-sm"
        onChange={(v) => { setBilan(null); setCoches({}); setFilieres({}); choisir({ classe: v }); }} />
      {donnees.isError && <p className="text-sm text-destructive">{erreursServeur(donnees.error).global}</p>}
      {classeChoisie && !l1 && donnees.data && !donnees.data.classe_cible && (
        <p className="text-sm text-amber-700">Aucune classe de niveau suivant pour l'année suivante (fin de cycle ou classe à créer dans Paramètres).</p>
      )}
      {bilan?.ignores?.length > 0 && (
        <div role="alert" className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-900/20 dark:text-amber-100">
          <p className="font-medium">{bilan.ignores.length} étudiant(s) non inscrit(s) :</p>
          <ul className="list-disc pl-5">{bilan.ignores.map((x) => <li key={x.etudiant}>{x.motif}</li>)}</ul>
        </div>
      )}
      {donnees.data && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="w-10 px-2 py-2" />
                <th className="px-3 py-2 text-left">Étudiant</th>
                <th className="px-2 py-2">Résultats</th>
                <th className="px-2 py-2">Inscription</th>
                {l1 && <th className="px-2 py-2">Filière en L2</th>}
              </tr>
            </thead>
            <tbody>
              {etudiants.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucun étudiant.</td></tr>}
              {etudiants.map((e) => (
                <tr key={e.etudiant} className="border-t border-border">
                  <td className="px-2 py-1.5 text-center">
                    {!l1 && (
                      <input type="checkbox" className="size-4 accent-primary" aria-label={`Promouvoir ${e.nom_complet}`}
                        disabled={e.statut !== 'active'} checked={Boolean(coches[e.etudiant])}
                        onChange={(ev) => setCoches((c) => ({ ...c, [e.etudiant]: ev.target.checked }))} />
                    )}
                  </td>
                  <td className="px-3 py-1.5"><div className="font-medium">{e.nom_complet}</div><div className="text-xs text-muted-foreground">{e.matricule}</div></td>
                  <td className="px-2 py-1.5 text-center">
                    {e.resultats.length === 0 ? <span className="text-muted-foreground">non délibéré</span> : e.resultats.map((r) => (
                      <span key={r.semestre} className={`mr-1 rounded px-1.5 py-0.5 text-xs font-semibold ${couleurDecision(r.decision)}`}>{r.semestre} {r.decision}</span>
                    ))}
                  </td>
                  <td className="px-2 py-1.5 text-center text-xs">{e.statut === 'active' ? 'en cours' : e.statut}</td>
                  {l1 && (
                    <td className="px-2 py-1.5">
                      <select aria-label={`Filière de ${e.nom_complet}`} disabled={e.statut !== 'active'}
                        className="h-8 w-full rounded-md border border-border bg-background px-2 text-sm"
                        value={filieres[e.etudiant] ?? ''} onChange={(ev) => setFilieres((f) => ({ ...f, [e.etudiant]: ev.target.value }))}>
                        <option value="">—</option>
                        {(donnees.data.filieres ?? []).map((f) => <option key={f.id} value={f.id}>{f.code} — {f.nom}</option>)}
                      </select>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
