import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { router } from '@/app/router';
import ErrorBoundary from '@/components/ErrorBoundary';
import { estDelaiDepasse } from '@/api/client';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      // Un nouvel essai, sauf après un délai dépassé : un serveur muet
      // pendant 30 s ne répondra pas mieux.
      retry: (echecs, erreur) => echecs < 1 && !estDelaiDepasse(erreur),
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </ErrorBoundary>,
);
