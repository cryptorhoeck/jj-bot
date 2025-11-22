import './index.css'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App.jsx'
import ErrorBoundary from './components/ErrorBoundary'

// StrictMode disabled to prevent WebSocket reconnection noise in dev mode
createRoot(document.getElementById('root')).render(
  // <StrictMode>
    <ErrorBoundary darkMode={true} showError={process.env.NODE_ENV === 'development'}>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1e293b',
            color: '#e2e8f0',
            borderRadius: '0.5rem',
            padding: '0.75rem 1rem',
            fontSize: '0.875rem',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.3)',
          },
          success: {
            iconTheme: { primary: '#10b981', secondary: '#1e293b' },
            style: { borderLeft: '4px solid #10b981' },
          },
          error: {
            iconTheme: { primary: '#ef4444', secondary: '#1e293b' },
            style: { borderLeft: '4px solid #ef4444' },
            duration: 5000,
          },
          loading: {
            iconTheme: { primary: '#3b82f6', secondary: '#1e293b' },
          },
        }}
      />
      <App />
    </ErrorBoundary>
  // </StrictMode>,
)
