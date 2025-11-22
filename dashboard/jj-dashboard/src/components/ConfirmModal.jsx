import React from 'react';

/**
 * Confirmation modal to replace native confirm() dialogs
 */
export function ConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  title = 'Confirm Action',
  message = 'Are you sure you want to proceed?',
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  confirmVariant = 'danger', // 'danger', 'warning', 'primary'
  darkMode = false,
}) {
  if (!isOpen) return null;

  const colors = {
    overlay: 'rgba(0, 0, 0, 0.5)',
    bg: darkMode ? '#1e293b' : '#ffffff',
    border: darkMode ? '#334155' : '#e2e8f0',
    text: darkMode ? '#e2e8f0' : '#1e293b',
    textMuted: darkMode ? '#94a3b8' : '#64748b',
  };

  const buttonColors = {
    danger: { bg: '#ef4444', hover: '#dc2626' },
    warning: { bg: '#f59e0b', hover: '#d97706' },
    primary: { bg: '#3b82f6', hover: '#2563eb' },
  };

  const confirmColor = buttonColors[confirmVariant] || buttonColors.primary;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: colors.overlay,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000,
        animation: 'fadeIn 0.15s ease-out',
      }}
      onClick={onClose}
    >
      <div
        style={{
          backgroundColor: colors.bg,
          borderRadius: '0.75rem',
          padding: '1.5rem',
          maxWidth: '400px',
          width: '90%',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          animation: 'slideUp 0.2s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Icon */}
        <div style={{
          width: '3rem',
          height: '3rem',
          borderRadius: '50%',
          backgroundColor: `${confirmColor.bg}20`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '1rem',
        }}>
          {confirmVariant === 'danger' ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={confirmColor.bg} strokeWidth="2">
              <path d="M12 9v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : confirmVariant === 'warning' ? (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={confirmColor.bg} strokeWidth="2">
              <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          ) : (
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke={confirmColor.bg} strokeWidth="2">
              <path d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          )}
        </div>

        {/* Title */}
        <h3 style={{
          fontSize: '1.125rem',
          fontWeight: '600',
          color: colors.text,
          marginBottom: '0.5rem',
        }}>
          {title}
        </h3>

        {/* Message */}
        <p style={{
          fontSize: '0.875rem',
          color: colors.textMuted,
          lineHeight: 1.5,
          marginBottom: '1.5rem',
        }}>
          {message}
        </p>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.625rem 1.25rem',
              backgroundColor: 'transparent',
              color: colors.textMuted,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              fontWeight: '500',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#f1f5f9';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
            }}
          >
            {cancelText}
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            style={{
              padding: '0.625rem 1.25rem',
              backgroundColor: confirmColor.bg,
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = confirmColor.hover}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = confirmColor.bg}
          >
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

// Custom hook for confirm dialogs
export function useConfirmModal() {
  const [modalState, setModalState] = React.useState({
    isOpen: false,
    config: {},
    resolve: null,
  });

  const confirm = React.useCallback((config) => {
    return new Promise((resolve) => {
      setModalState({
        isOpen: true,
        config,
        resolve,
      });
    });
  }, []);

  const handleClose = React.useCallback(() => {
    if (modalState.resolve) {
      modalState.resolve(false);
    }
    setModalState({ isOpen: false, config: {}, resolve: null });
  }, [modalState.resolve]);

  const handleConfirm = React.useCallback(() => {
    if (modalState.resolve) {
      modalState.resolve(true);
    }
    setModalState({ isOpen: false, config: {}, resolve: null });
  }, [modalState.resolve]);

  const ConfirmModalComponent = React.useCallback(
    (props) => (
      <ConfirmModal
        isOpen={modalState.isOpen}
        onClose={handleClose}
        onConfirm={handleConfirm}
        {...modalState.config}
        {...props}
      />
    ),
    [modalState.isOpen, modalState.config, handleClose, handleConfirm]
  );

  return { confirm, ConfirmModal: ConfirmModalComponent };
}

// CSS for animations
export const modalStyles = `
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
`;

export default ConfirmModal;
