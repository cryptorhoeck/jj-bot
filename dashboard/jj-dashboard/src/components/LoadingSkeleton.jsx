import React from 'react';

/**
 * Reusable loading skeleton components for professional loading states
 */

// Base skeleton component with animation
export function Skeleton({ className = '', width, height, borderRadius = '0.25rem', style = {} }) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width: width || '100%',
        height: height || '1rem',
        borderRadius,
        background: 'linear-gradient(90deg, var(--skeleton-base) 25%, var(--skeleton-shine) 50%, var(--skeleton-base) 75%)',
        backgroundSize: '200% 100%',
        animation: 'skeleton-loading 1.5s ease-in-out infinite',
        ...style,
      }}
    />
  );
}

// Card skeleton for dashboard cards
export function CardSkeleton({ darkMode = false }) {
  const colors = {
    base: darkMode ? '#334155' : '#e2e8f0',
    shine: darkMode ? '#475569' : '#f1f5f9',
  };

  return (
    <div
      style={{
        '--skeleton-base': colors.base,
        '--skeleton-shine': colors.shine,
        padding: '1.5rem',
        borderRadius: '0.75rem',
        backgroundColor: darkMode ? '#1e293b' : '#ffffff',
        border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
      }}
    >
      <Skeleton height="0.75rem" width="40%" style={{ marginBottom: '0.75rem' }} />
      <Skeleton height="2rem" width="60%" style={{ marginBottom: '0.5rem' }} />
      <Skeleton height="0.625rem" width="30%" />
    </div>
  );
}

// Table skeleton for trade tables
export function TableSkeleton({ rows = 5, cols = 5, darkMode = false }) {
  const colors = {
    base: darkMode ? '#334155' : '#e2e8f0',
    shine: darkMode ? '#475569' : '#f1f5f9',
  };

  return (
    <div
      style={{
        '--skeleton-base': colors.base,
        '--skeleton-shine': colors.shine,
        backgroundColor: darkMode ? '#1e293b' : '#ffffff',
        borderRadius: '0.75rem',
        padding: '1rem',
        border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', padding: '0.5rem 0' }}>
        {Array(cols).fill(0).map((_, i) => (
          <Skeleton key={i} height="0.75rem" style={{ flex: i === 0 ? 2 : 1 }} />
        ))}
      </div>

      {/* Rows */}
      {Array(rows).fill(0).map((_, rowIdx) => (
        <div
          key={rowIdx}
          style={{
            display: 'flex',
            gap: '1rem',
            padding: '0.75rem 0',
            borderTop: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
          }}
        >
          {Array(cols).fill(0).map((_, colIdx) => (
            <Skeleton
              key={colIdx}
              height="0.875rem"
              style={{ flex: colIdx === 0 ? 2 : 1 }}
            />
          ))}
        </div>
      ))}
    </div>
  );
}

// Chart skeleton for price charts
export function ChartSkeleton({ darkMode = false, height = '300px' }) {
  const colors = {
    base: darkMode ? '#334155' : '#e2e8f0',
    shine: darkMode ? '#475569' : '#f1f5f9',
  };

  return (
    <div
      style={{
        '--skeleton-base': colors.base,
        '--skeleton-shine': colors.shine,
        height,
        backgroundColor: darkMode ? '#1e293b' : '#ffffff',
        borderRadius: '0.75rem',
        padding: '1.5rem',
        border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
        <Skeleton height="1.25rem" width="30%" />
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Skeleton height="1.25rem" width="3rem" />
          <Skeleton height="1.25rem" width="3rem" />
          <Skeleton height="1.25rem" width="3rem" />
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', alignItems: 'flex-end', gap: '2px' }}>
        {Array(30).fill(0).map((_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: `${20 + Math.random() * 60}%`,
              backgroundColor: colors.base,
              borderRadius: '2px 2px 0 0',
              animation: 'skeleton-loading 1.5s ease-in-out infinite',
              animationDelay: `${i * 0.05}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// Stats grid skeleton for dashboard overview
export function StatsGridSkeleton({ count = 6, darkMode = false }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '1rem',
    }}>
      {Array(count).fill(0).map((_, i) => (
        <CardSkeleton key={i} darkMode={darkMode} />
      ))}
    </div>
  );
}

// Position list skeleton
export function PositionSkeleton({ count = 3, darkMode = false }) {
  const colors = {
    base: darkMode ? '#334155' : '#e2e8f0',
    shine: darkMode ? '#475569' : '#f1f5f9',
  };

  return (
    <div style={{ '--skeleton-base': colors.base, '--skeleton-shine': colors.shine }}>
      {Array(count).fill(0).map((_, i) => (
        <div
          key={i}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1rem',
            borderBottom: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
          }}
        >
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
            <Skeleton width="3rem" height="3rem" borderRadius="50%" />
            <div style={{ flex: 1 }}>
              <Skeleton width="60%" height="1rem" style={{ marginBottom: '0.5rem' }} />
              <Skeleton width="40%" height="0.75rem" />
            </div>
          </div>
          <Skeleton width="5rem" height="1.25rem" />
        </div>
      ))}
    </div>
  );
}

// Full page loading skeleton
export function PageSkeleton({ darkMode = false }) {
  return (
    <div style={{ padding: '2rem', display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Skeleton
            width="200px"
            height="2rem"
            style={{
              marginBottom: '0.5rem',
              '--skeleton-base': darkMode ? '#334155' : '#e2e8f0',
              '--skeleton-shine': darkMode ? '#475569' : '#f1f5f9',
            }}
          />
          <Skeleton
            width="300px"
            height="1rem"
            style={{
              '--skeleton-base': darkMode ? '#334155' : '#e2e8f0',
              '--skeleton-shine': darkMode ? '#475569' : '#f1f5f9',
            }}
          />
        </div>
        <Skeleton
          width="120px"
          height="2.5rem"
          borderRadius="0.5rem"
          style={{
            '--skeleton-base': darkMode ? '#334155' : '#e2e8f0',
            '--skeleton-shine': darkMode ? '#475569' : '#f1f5f9',
          }}
        />
      </div>

      {/* Stats Grid */}
      <StatsGridSkeleton count={6} darkMode={darkMode} />

      {/* Chart */}
      <ChartSkeleton darkMode={darkMode} />

      {/* Table */}
      <TableSkeleton rows={5} cols={5} darkMode={darkMode} />
    </div>
  );
}

// CSS keyframes for animation (add to index.css or inject via style tag)
export const skeletonStyles = `
@keyframes skeleton-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
`;

export default {
  Skeleton,
  CardSkeleton,
  TableSkeleton,
  ChartSkeleton,
  StatsGridSkeleton,
  PositionSkeleton,
  PageSkeleton,
};
