import React from 'react';

/**
 * Empty and Error state components for professional UX
 */

// Empty state component
export function EmptyState({
  icon = '📭',
  title = 'No data available',
  description = 'There is nothing to display yet.',
  action = null,
  darkMode = false,
}) {
  const colors = {
    bg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '#334155' : '#e2e8f0',
    text: darkMode ? '#e2e8f0' : '#1e293b',
    textMuted: darkMode ? '#94a3b8' : '#64748b',
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 2rem',
        backgroundColor: colors.bg,
        borderRadius: '0.75rem',
        border: `2px dashed ${colors.border}`,
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>{icon}</div>
      <h3 style={{
        fontSize: '1.125rem',
        fontWeight: '600',
        color: colors.text,
        marginBottom: '0.5rem',
      }}>
        {title}
      </h3>
      <p style={{
        fontSize: '0.875rem',
        color: colors.textMuted,
        maxWidth: '300px',
        lineHeight: 1.5,
        marginBottom: action ? '1.5rem' : 0,
      }}>
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          style={{
            padding: '0.625rem 1.25rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#3b82f6'}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}

// Error state component
export function ErrorState({
  icon = '⚠️',
  title = 'Something went wrong',
  description = 'An unexpected error occurred. Please try again.',
  error = null,
  onRetry = null,
  darkMode = false,
}) {
  const colors = {
    bg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '#7f1d1d' : '#fecaca',
    bgAccent: darkMode ? '#450a0a' : '#fef2f2',
    text: darkMode ? '#e2e8f0' : '#1e293b',
    textMuted: darkMode ? '#94a3b8' : '#64748b',
    error: '#ef4444',
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem 2rem',
        backgroundColor: colors.bgAccent,
        borderRadius: '0.75rem',
        border: `2px solid ${colors.border}`,
        textAlign: 'center',
      }}
    >
      <div style={{
        fontSize: '3rem',
        marginBottom: '1rem',
        width: '4rem',
        height: '4rem',
        borderRadius: '50%',
        backgroundColor: `${colors.error}20`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        {icon}
      </div>
      <h3 style={{
        fontSize: '1.125rem',
        fontWeight: '600',
        color: colors.error,
        marginBottom: '0.5rem',
      }}>
        {title}
      </h3>
      <p style={{
        fontSize: '0.875rem',
        color: colors.textMuted,
        maxWidth: '400px',
        lineHeight: 1.5,
        marginBottom: error ? '1rem' : (onRetry ? '1.5rem' : 0),
      }}>
        {description}
      </p>
      {error && (
        <code style={{
          display: 'block',
          padding: '0.75rem 1rem',
          backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
          borderRadius: '0.375rem',
          fontSize: '0.75rem',
          color: colors.textMuted,
          fontFamily: 'monospace',
          maxWidth: '100%',
          overflow: 'auto',
          marginBottom: onRetry ? '1.5rem' : 0,
        }}>
          {error.toString()}
        </code>
      )}
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            padding: '0.625rem 1.25rem',
            backgroundColor: colors.error,
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: '600',
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#dc2626'}
          onMouseLeave={(e) => e.currentTarget.style.backgroundColor = colors.error}
        >
          Try Again
        </button>
      )}
    </div>
  );
}

// Connection lost state
export function ConnectionLost({ darkMode = false, onReconnect = null }) {
  return (
    <ErrorState
      icon="🔌"
      title="Connection Lost"
      description="Unable to connect to the server. Please check your connection and try again."
      onRetry={onReconnect}
      darkMode={darkMode}
    />
  );
}

// No trades state
export function NoTrades({ darkMode = false, onStartBot = null }) {
  return (
    <EmptyState
      icon="📊"
      title="No trades yet"
      description="Start the trading bot to begin executing trades and see your performance data here."
      action={onStartBot ? { label: 'Start Trading Bot', onClick: onStartBot } : null}
      darkMode={darkMode}
    />
  );
}

// No positions state
export function NoPositions({ darkMode = false }) {
  return (
    <EmptyState
      icon="💼"
      title="No open positions"
      description="You don't have any active positions. The bot will open positions when trading signals are detected."
      darkMode={darkMode}
    />
  );
}

// Loading data state with spinner
export function LoadingData({ message = 'Loading data...', darkMode = false }) {
  const colors = {
    text: darkMode ? '#94a3b8' : '#64748b',
    spinner: '#3b82f6',
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '3rem',
        gap: '1rem',
      }}
    >
      <div
        style={{
          width: '2.5rem',
          height: '2.5rem',
          border: `3px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
          borderTopColor: colors.spinner,
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }}
      />
      <p style={{ color: colors.text, fontSize: '0.875rem' }}>{message}</p>
    </div>
  );
}

// Inline loading indicator
export function LoadingSpinner({ size = 'md', color = '#3b82f6' }) {
  const sizes = {
    sm: '1rem',
    md: '1.5rem',
    lg: '2rem',
    xl: '3rem',
  };

  return (
    <div
      style={{
        width: sizes[size],
        height: sizes[size],
        border: `2px solid transparent`,
        borderTopColor: color,
        borderRadius: '50%',
        animation: 'spin 0.8s linear infinite',
        display: 'inline-block',
      }}
    />
  );
}

// Status badge component
export function StatusBadge({ status, darkMode = false }) {
  const statusConfig = {
    success: { bg: '#10b98120', color: '#10b981', label: 'Success' },
    error: { bg: '#ef444420', color: '#ef4444', label: 'Error' },
    warning: { bg: '#f59e0b20', color: '#f59e0b', label: 'Warning' },
    info: { bg: '#3b82f620', color: '#3b82f6', label: 'Info' },
    running: { bg: '#10b98120', color: '#10b981', label: 'Running' },
    stopped: { bg: '#ef444420', color: '#ef4444', label: 'Stopped' },
    pending: { bg: '#f59e0b20', color: '#f59e0b', label: 'Pending' },
  };

  const config = statusConfig[status] || statusConfig.info;

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: '0.25rem 0.625rem',
        backgroundColor: config.bg,
        color: config.color,
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: '600',
      }}
    >
      <span
        style={{
          width: '0.375rem',
          height: '0.375rem',
          borderRadius: '50%',
          backgroundColor: config.color,
        }}
      />
      {config.label}
    </span>
  );
}

// CSS for animations
export const stateStyles = `
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
`;

export default {
  EmptyState,
  ErrorState,
  ConnectionLost,
  NoTrades,
  NoPositions,
  LoadingData,
  LoadingSpinner,
  StatusBadge,
};
