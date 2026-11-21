/**
 * Launchpad (écran des modules), sur le modèle de SAP Fiori : une tuile sobre par module, qui porte un
 * chiffre vivant calculé par le serveur dans le périmètre de la personne (GET /api/core/lanceur/), puis
 * une ligne d'accès rapides selon les droits.
 */
import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { Inbox, UserCircle } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';
import { lireLanceur } from '@/api/lanceur';
import { dateLongue } from '@/lib/dates';
import useAuthStore, { aRole } from '@/store/authStore';
import AccesRapides from './lanceur/AccesRapides';
import TuileModule from './lanceur/TuileModule';
import MenuUtilisateur from './MenuUtilisateur';
import { CANVAS_MON_ESPACE, COULEUR_MON_ESPACE, espacePersonnelSeul, menuVisible, modulesVisibles } from './modules';

function Groupe({ titre, children }) {
  return (
    <section className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{titre}</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-[repeat(auto-fill,11rem)] sm:gap-4">{children}</div>
    </section>
  );
}

export default function Lanceur() {
  const user = useAuthStore((state) => state.user);
  const espacePersonnel = useAuthStore((state) => aRole(state, 'etudiant') || aRole(state, 'enseignant'));
  const modules = modulesVisibles(user);
  const resumes = useQuery({ queryKey: ['lanceur'], queryFn: lireLanceur, enabled: modules.length > 0 });

  // Rien d'autre à choisir que son espace personnel : on y va directement.
  if (espacePersonnelSeul(user)) return <Navigate to="/moi" replace />;

  const vide = modules.length === 0 && !espacePersonnel;
  const parModule = Object.fromEntries((resumes.data ?? []).map((r) => [r.module, r]));
  // undefined pendant le chargement (pas encore de chiffre), null si le serveur n'en donne pas.
  const valeurDe = (r) => {
    if (resumes.isError) return null;
    if (!r) return resumes.isPending ? undefined : null;
    return r.valeur;
  };
  const niveaux = (code) => user?.modules?.find((m) => m.code === code)?.niveaux ?? [];
  const rapides = modules.flatMap((m) => menuVisible(m, niveaux(m.code))
    .filter((item) => item.rapide)
    .map((item) => ({ libelle: item.libelle, to: `${m.chemin}/${item.chemin}` })));

  return (
    <div className="min-h-dvh bg-canvas" style={{ '--canvas': CANVAS_MON_ESPACE }}>
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between gap-3 border-b border-border bg-card px-4 md:px-8">
        <div className="flex min-w-0 items-center gap-2.5">
          <img src={logoUccb} alt="" className="size-8 shrink-0" />
          <h1 className="truncate text-[15px] font-semibold tracking-tight text-foreground">UCCB · ERP</h1>
        </div>
        <div className="flex items-center gap-4">
          <p className="hidden text-sm text-muted-foreground sm:block">{dateLongue(new Date())}</p>
          <MenuUtilisateur />
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-4 py-6 md:px-8 md:py-8">
        {vide ? (
          <div className="carte flex flex-col items-center gap-3 py-16 text-center">
            <Inbox className="size-10 text-muted-foreground" />
            <p className="max-w-sm text-sm text-muted-foreground">
              Aucun module ne vous est attribué. Contactez l’administrateur.
            </p>
          </div>
        ) : (
          <>
            {espacePersonnel && (
              <Groupe titre="Mon espace">
                <TuileModule to="/moi" titre="Mon espace" sousTitre="Planning, notes, documents"
                  icone={UserCircle} couleur={COULEUR_MON_ESPACE} />
              </Groupe>
            )}
            {modules.length > 0 && (
              <Groupe titre="Modules">
                {modules.map((m) => {
                  const r = parModule[m.code];
                  return (
                    <TuileModule key={m.code} to={m.chemin} titre={m.libelle} icone={m.icone} couleur={m.couleur}
                      chargement={resumes.isPending} sousTitre={r?.libelle} unite={r?.unite} detail={r?.detail} ton={r?.ton}
                      valeur={valeurDe(r)} />
                  );
                })}
              </Groupe>
            )}
            <AccesRapides liens={rapides} />
          </>
        )}
      </main>
    </div>
  );
}
