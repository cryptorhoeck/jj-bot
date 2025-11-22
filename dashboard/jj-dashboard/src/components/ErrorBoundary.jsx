import React from 'react';
import { ErrorState } from './StateComponents';

/**
 * Error Boundary component for graceful error handling
 * Catches JavaScript errors in child components and displays fallback UI
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({ errorInfo });

    // You could also send this to an error reporting service
    // logErrorToService(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    // Optionally reload the page or reset app state
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const { darkMode = false } = this.props;

      return (
        <div style={{ padding: '2rem' }}>
          <ErrorState
            icon="💥"
            title="Something went wrong"
            description="An unexpected error occurred in this section. This might be a temporary issue."
            error={this.props.showError ? this.state.error : null}
            onRetry={this.handleReset}
            darkMode={darkMode}
          />

          {/* Developer info - only in development */}
          {process.env.NODE_ENV === 'development' && this.state.errorInfo && (
            <details
              style={{
                marginTop: '1.5rem',
                padding: '1rem',
                backgroundColor: darkMode ? '#1e293b' : '#f1f5f9',
                borderRadius: '0.5rem',
                fontSize: '0.75rem',
              }}
            >
              <summary style={{ cursor: 'pointer', color: darkMode ? '#94a3b8' : '#64748b' }}>
                Technical Details (Developer Mode)
              </summary>
              <pre style={{
                marginTop: '1rem',
                overflow: 'auto',
                color: darkMode ? '#e2e8f0' : '#1e293b',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {this.state.error?.toString()}
                {'\n\nComponent Stack:\n'}
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

// Functional wrapper with hooks support
export function withErrorBoundary(Component, options = {}) {
  return function WithErrorBoundary(props) {
    return (
      <ErrorBoundary {...options}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}

export default ErrorBoundary;
