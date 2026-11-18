// Arbre de routage provisoire (complété par le lanceur et les modules).
import { createBrowserRouter } from 'react-router-dom';
import LoginPage from '@/features/auth/LoginPage';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '*', element: <LoginPage /> },
]);
