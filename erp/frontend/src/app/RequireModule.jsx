import useAuthStore, { aDroit } from '@/store/authStore';
import Interdit from './pages/Interdit';

/** Affiche `children` si l'utilisateur a le droit ; sinon la page 403, sans redirection. */
export default function RequireModule({ module, niveau, children }) {
  const autorise = useAuthStore((state) => aDroit(state, module, niveau));
  return autorise ? children : <Interdit />;
}
