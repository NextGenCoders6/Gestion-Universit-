/** Saisie des notes d'un EC pour une classe : grille au clavier, enregistrement groupé, erreurs par cellule. */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AlertTriangle, CheckCircle2 } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Selecteur from '@/components/shared/Selecteur';
import { useClasses, useSelection } from '../hooks';
import { note, optionsClasses } from '../lib/format';

const CHAMPS = [['devoir', 'Devoir'], ['session', 'Session'], ['sr', 'Rattrapage']];

const texte = (v) => (v === null || v === undefined ? '' : String(v).replace('.', ','));

/** Entrée : passe à la même colonne de la ligne suivante (saisie en colonne, comme sur papier). */
function allerEnBas(e) {
  if (e.key !== 'Enter') return;
  e.preventDefault();
  const { ligne, champ } = e.currentTarget.dataset;
  const suivante = document.querySelector(`[data-ligne="${Number(ligne) + 1}"][data-champ="${champ}"]`);
  suivante?.focus();
  suivante?.select?.();
}

export default function SaisieNotes() {
  const { toast } = useToast();
  const client = useQueryClient();
  const classes = useClasses();
  const [{ classe, ec }, choisir] = useSelection(['classe', 'ec']);
  const classeChoisie = (classes.data ?? []).find((c) => String(c.id) === classe);
  const grille = useQuery({
    queryKey: ['scolarite', 'saisie', classe, ec],
    queryFn: () => api.grilleSaisie({ classe, ec }),
    enabled: Boolean(classe && ec),
  });
  // Seules les lignes modifiées sont gardées ici ; les autres affichent la valeur du serveur.
  const [brouillon, setBrouillon] = useState({});
  const [erreurs, setErreurs] = useState({});

  const changerSelection = (modif) => { setBrouillon({}); setErreurs({}); choisir(modif); };
  const valeur = (l, champ) => brouillon[l.note_id]?.[champ] ?? (champ === 'absent' ? l.absent : texte(l[champ]));
  const modifier = (l, champ, v) => setBrouillon((b) => ({
    ...b, [l.note_id]: { devoir: valeur(l, 'devoir'), session: valeur(l, 'session'), sr: valeur(l, 'sr'),
      absent: valeur(l, 'absent'), ...b[l.note_id], [champ]: v },
  }));

  const enregistrer = useMutation({
    mutationFn: () => api.enregistrerSaisie(Object.entries(brouillon).map(([id, v]) => ({
      note_id: Number(id), devoir: v.devoir || null, session: v.session || null, sr: v.sr || null, absent: Boolean(v.absent),
    }))),
    onSuccess: (r) => {
      setErreurs(r.erreurs ?? {});
      setBrouillon((b) => Object.fromEntries(Object.entries(b).filter(([id]) => r.erreurs?.[id])));
      client.invalidateQueries({ queryKey: ['scolarite', 'saisie'] });
      const nbErreurs = Object.keys(r.erreurs ?? {}).length;
      toast({
        title: `${r.enregistrees} note(s) enregistrée(s)`,
        description: nbErreurs ? `${nbErreurs} ligne(s) à corriger, signalée(s) en rouge.` : undefined,
        variant: nbErreurs && !r.enregistrees ? 'destructive' : undefined,
      });
    },
    onError: (e) => toast({ title: 'Enregistrement impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const nbModifies = Object.keys(brouillon).length;
  const lignes = grille.data?.lignes ?? [];
  const lectureSeule = Boolean(grille.data?.archivee || grille.data?.deliberee);

  return (
    <div className="space-y-4">
      <PageHeader titre="Saisie des notes" description="Devoir et session sur 20 ; le rattrapage remplace la session s'il est meilleur.">
        <Button onClick={() => enregistrer.mutate()} disabled={!nbModifies || enregistrer.isPending || lectureSeule}>
          <CheckCircle2 /> Enregistrer{nbModifies ? ` (${nbModifies})` : ''}
        </Button>
      </PageHeader>
      <div className="grid gap-3 sm:grid-cols-2 lg:max-w-2xl">
        <Selecteur id="classe" label="Classe" valeur={classe} options={optionsClasses(classes.data)}
          onChange={(v) => changerSelection({ classe: v, ec: '' })} />
        <Selecteur id="ec" label="Élément constitutif" valeur={ec}
          options={(classeChoisie?.ecs ?? []).map((e) => ({ valeur: String(e.id), libelle: `${e.semestre} · ${e.code} — ${e.libelle}` }))}
          onChange={(v) => changerSelection({ ec: v })} />
      </div>
      {grille.data?.archivee && <p className="text-sm text-muted-foreground">Année archivée : les notes ne peuvent plus changer.</p>}
      {grille.data?.deliberee && !grille.data?.archivee && (
        <p className="text-sm text-muted-foreground">Ce semestre est déjà délibéré : rouvrez la délibération pour modifier les notes.</p>
      )}
      {grille.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {grille.isError && <p className="text-sm text-destructive">{erreursServeur(grille.error).global}</p>}
      {grille.data && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="px-3 py-2 text-left">Étudiant</th>
                {CHAMPS.map(([, libelle]) => <th key={libelle} className="w-28 px-2 py-2">{libelle}</th>)}
                <th className="w-20 px-2 py-2">Absent</th>
                <th className="w-24 px-2 py-2">Moyenne</th>
              </tr>
            </thead>
            <tbody>
              {lignes.length === 0 && (
                <tr><td colSpan={6} className="px-3 py-8 text-center text-muted-foreground">Aucun étudiant inscrit dans cette classe.</td></tr>
              )}
              {lignes.map((l, i) => {
                const err = erreurs[l.note_id] ?? {};
                const messages = Object.values(err);
                return (
                  <tr key={l.note_id} aria-label={l.nom_complet} className={`border-t border-border ${messages.length ? 'bg-destructive/5' : ''}`}>
                    <td className="px-3 py-1.5">
                      <div className="font-medium">{l.nom_complet}</div>
                      <div className="text-xs text-muted-foreground">{l.matricule}</div>
                      {messages.map((m) => (
                        <p key={m} className="mt-1 flex items-center gap-1 text-xs font-medium text-destructive">
                          <AlertTriangle className="size-3" />{m}
                        </p>
                      ))}
                    </td>
                    {CHAMPS.map(([champ, libelle]) => (
                      <td key={champ} className="px-2 py-1.5">
                        <Input inputMode="decimal" aria-label={`${libelle} — ${l.nom_complet}`} data-ligne={i} data-champ={champ}
                          aria-invalid={err[champ] ? 'true' : undefined} disabled={lectureSeule || (valeur(l, 'absent') && champ !== 'sr')}
                          className="h-8 text-center" value={valeur(l, champ)} onKeyDown={allerEnBas}
                          onChange={(e) => modifier(l, champ, e.target.value)} />
                      </td>
                    ))}
                    <td className="px-2 py-1.5 text-center">
                      <input type="checkbox" className="size-4 accent-primary" aria-label={`Absent — ${l.nom_complet}`}
                        disabled={lectureSeule} checked={Boolean(valeur(l, 'absent'))}
                        onChange={(e) => modifier(l, 'absent', e.target.checked)} />
                    </td>
                    <td className="px-2 py-1.5 text-center font-semibold">{brouillon[l.note_id] ? '…' : note(l.moyenne)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
