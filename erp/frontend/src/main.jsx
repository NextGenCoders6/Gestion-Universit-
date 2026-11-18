import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { RouterProvider } from 'react-router-dom';
import { router } from '@/app/router';
import ErrorBoundary from '@/components/ErrorBoundary';
import { queryClient } from '@/lib/queryClient';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </ErrorBoundary>,
);
