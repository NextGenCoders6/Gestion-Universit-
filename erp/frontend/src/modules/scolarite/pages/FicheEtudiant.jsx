/** Fiche d'un étudiant : identité, inscriptions, notes par semestre, documents officiels, statut. */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { ArrowLeft, FileText, Printer } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Selecteur from '@/components/shared/Selecteur';
import { useEstSecretariat } from '../hooks';
import { couleurDecision, note, STATUTS_ETUDIANT } from '../lib/format';

function Info({ label, children }) {
  return <div><dt className="text-xs text-muted-foreground">{label}</dt><dd className="text-sm font-medium">{children || '—'}</dd></div>;
}

function Semestre({ s, onReleve, secretariat }) {
  const { ligne, resultat } = s;
  return (
    <section className="space-y-2 rounded-lg border border-border bg-card p-4">
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{s.semestre}</h3>
        <div className="flex items-center gap-2 text-sm">
          {resultat ? (
            <>
              <span className={`rounded px-2 py-0.5 text-xs font-semibold ${couleurDecision(resultat.decision)}`}>{resultat.decision}</span>
              <span>{note(resultat.moyenne)} / 20 · {resultat.credits_obtenus}/{resultat.credits_totaux} crédits · rang {resultat.rang}</span>
              {secretariat && <Button size="sm" variant="outline" onClick={onReleve}><Printer /> Relevé PDF</Button>}
            </>
          ) : <span className="text-muted-foreground">Pas encore délibéré</span>}
        </div>
      </header>
      <table className="w-full text-sm">
        <thead className="text-xs text-muted-foreground"><tr>
          <th className="py-1 text-left">EC</th><th>Crédits</th><th>Devoir</th><th>Session</th><th>SR</th><th>Moyenne</th>
        </tr></thead>
        <tbody>
          {ligne.ues.flatMap((u) => [
            <tr key={`ue-${u.id}`} className="border-t border-border bg-muted/30">
              <td className="py-1 font-medium" colSpan={5}>{u.code} — {u.libelle}</td>
              <td className="text-center font-semibold">{note(u.moyenne_ue)}</td>
            </tr>,
            ...u.ecs.map((e) => (
              <tr key={e.id} className="border-t border-border/60">
                <td className="py-1 pl-3">{e.code} — {e.libelle}</td>
                <td className="text-center">{e.credits}</td>
                <td className="text-center">{e.absent ? 'ABS' : note(e.devoir)}</td>
                <td className="text-center">{e.absent ? 'ABS' : note(e.session)}</td>
                <td className="text-center">{note(e.sr)}</td>
                <td className={`text-center ${e.note !== null && e.note < 6 ? 'font-semibold text-destructive' : ''}`}>{note(e.note)}</td>
              </tr>
            )),
          ])}
        </tbody>
      </table>
    </section>
  );
}

export default function FicheEtudiant() {
  const { id } = useParams();
  const { toast } = useToast();
  const client = useQueryClient();
  const secretariat = useEstSecretariat();
  const fiche = useQuery({ queryKey: ['scolarite', 'etudiant', id], queryFn: () => api.ficheEtudiant(id) });
  const [annee, setAnnee] = useState('');
  const notes = useQuery({ queryKey: ['scolarite', 'etudiant', id, 'notes', annee],
    queryFn: () => api.notesEtudiant(id, annee ? { annee } : {}) });

  const statut = useMutation({
    mutationFn: (v) => api.changerStatut(id, v),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['scolarite'] }); toast({ title: 'Statut mis à jour' }); },
    onError: (e) => toast({ title: 'Changement impossible', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const telecharger = async (chemin, params, nom) => {
    try { await api.telecharger(chemin, params, nom); } catch (e) {
      toast({ title: 'Document indisponible', description: await api.messageErreurBlob(e), variant: 'destructive' });
    }
  };

  if (fiche.isLoading) return <p className="text-sm text-muted-foreground">Chargement…</p>;
  if (fiche.isError) return <p className="text-sm text-destructive">{erreursServeur(fiche.error).global}</p>;
  const e = fiche.data;
  const p = e.personne;
  const params = annee ? { annee } : {};

  return (
    <div className="space-y-4">
      <Link to=".." relative="path" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> Tous les étudiants
      </Link>
      <PageHeader titre={p.nom_complet} description={`Matricule ${e.matricule} · ${e.a_un_compte ? 'compte activé' : 'compte non activé'}`}>
        {secretariat && (
          <Button variant="outline" onClick={() => telecharger(`/scolarite/etudiants/${id}/attestation.pdf`, params, `attestation-${e.matricule}.pdf`)}>
            <FileText /> Attestation PDF
          </Button>
        )}
      </PageHeader>
      <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
        <dl className="grid grid-cols-2 gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-3">
          <Info label="Genre">{p.genre === 'F' ? 'Féminin' : 'Masculin'}</Info>
          <Info label="Date de naissance">{p.date_naissance && new Date(p.date_naissance).toLocaleDateString('fr-FR')}</Info>
          <Info label="Lieu de naissance">{p.lieu_naissance}</Info>
          <Info label="E-mail">{p.email}</Info>
          <Info label="Téléphone">{p.telephone}</Info>
          <Info label="Nationalité">{p.nationalite}</Info>
        </dl>
        <div className="space-y-3 rounded-lg border border-border bg-card p-4">
          {secretariat ? (
            <Selecteur id="statut" label="Statut de l’étudiant" valeur={e.statut} options={STATUTS_ETUDIANT} vide="—"
              onChange={async (v) => {
                if (!v || v === e.statut) return;
                const libelle = STATUTS_ETUDIANT.find((s) => s.valeur === v).libelle;
                const ok = await confirmer({ titre: `Passer l’étudiant au statut « ${libelle} » ?`,
                  description: v === 'actif' ? undefined : 'Son inscription en cours sera clôturée.', libelleConfirmer: 'Confirmer' });
                if (ok) statut.mutate(v);
              }} />
          ) : <Info label="Statut">{STATUTS_ETUDIANT.find((s) => s.valeur === e.statut)?.libelle}</Info>}
          <div>
            <h3 className="mb-1 text-xs text-muted-foreground">Inscriptions</h3>
            <ul className="space-y-1 text-sm">
              {e.inscriptions.map((i) => (
                <li key={i.id}>
                  <button type="button" className={`w-full rounded px-2 py-1 text-left hover:bg-muted ${String(i.annee) === annee ? 'bg-muted' : ''}`}
                    onClick={() => setAnnee(String(i.annee))}>
                    {i.classe_libelle} <span className="text-muted-foreground">· {i.type === 'premiere' ? 'première inscription' : 'réinscription'} · {i.statut}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <h2 className="text-lg font-semibold">Notes {notes.data?.classe ? `— ${notes.data.classe}` : ''}</h2>
      {notes.isLoading && <p className="text-sm text-muted-foreground">Chargement…</p>}
      {notes.data?.semestres?.length === 0 && <p className="text-sm text-muted-foreground">Aucune inscription.</p>}
      <div className="grid gap-3 xl:grid-cols-2">
        {(notes.data?.semestres ?? []).map((s) => (
          <Semestre key={s.semestre} s={s} secretariat={secretariat}
            onReleve={() => telecharger(`/scolarite/etudiants/${id}/releve.pdf`, { ...params, semestre: s.semestre },
              `releve-${e.matricule}-${s.semestre}.pdf`)} />
        ))}
      </div>
    </div>
  );
}
