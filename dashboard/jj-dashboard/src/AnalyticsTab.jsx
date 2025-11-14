import React, { useState, useEffect } from 'react';

export function AnalyticsTab({ colors, darkMode, API_BASE }) {
  const [equityCurve, setEquityCurve] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [distribution, setDistribution] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [loading, setLoading] = useState(false);
  const [simulationParams, setSimulationParams] = useState({
    initial_capital: 10000,
    avg_return_pct: 1.5,
    std_return_pct: 2.5,
    num_trades: 100,
    win_rate: 60
  });

  // Fetch simulated equity curve
  const fetchSimulation = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams(simulationParams);
      const response = await fetch(`${API_BASE}/api/analytics/equity-curve/simulate?${params}`);

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setEquityCurve(result.equity_curve);
          setMetrics(result.metrics);
        }
      }
    } catch (error) {
      console.error('Error fetching simulation:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSimulation();
  }, []);

  // Render equity curve chart
  const renderEquityCurve = () => {
    if (!equityCurve || equityCurve.length === 0) {
      return (
        <div style={{ textAlign: 'center', padding: '3rem', color: colors.textMuted }}>
          No data available
        </div>
      );
    }

    const width = 1000;
    const height = 300;
    const padding = 60;
    const chartWidth = width - (padding * 2);
    const chartHeight = height - (padding * 2);

    const equityValues = equityCurve.map(p => p.equity);
    const maxEquity = Math.max(...equityValues);
    const minEquity = Math.min(...equityValues);
    const range = maxEquity - minEquity || 1;

    return (
      <div style={{ backgroundColor: darkMode ? '#0f172a' : '#ffffff', borderRadius: '0.5rem', padding: '1rem' }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
          📈 Equity Curve
        </h3>

        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((percent, i) => (
            <g key={i}>
              <line
                x1={padding}
                y1={padding + (chartHeight * percent)}
                x2={width - padding}
                y2={padding + (chartHeight * percent)}
                stroke={darkMode ? '#1e293b' : '#e2e8f0'}
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={width - padding + 5}
                y={padding + (chartHeight * percent) + 4}
                textAnchor="start"
                fill={colors.textMuted}
                fontSize="11"
              >
                ${(minEquity + (range * (1 - percent))).toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </text>
            </g>
          ))}

          {/* Equity line */}
          <polyline
            points={equityCurve.map((point, index) => {
              const x = padding + (index / (equityCurve.length - 1)) * chartWidth;
              const y = padding + chartHeight - ((point.equity - minEquity) / range) * chartHeight;
              return `${x},${y}`;
            }).join(' ')}
            fill="none"
            stroke="#10b981"
            strokeWidth="2.5"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {/* Fill area */}
          <polygon
            points={
              `${padding},${height - padding} ` +
              equityCurve.map((point, index) => {
                const x = padding + (index / (equityCurve.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((point.equity - minEquity) / range) * chartHeight;
                return `${x},${y}`;
              }).join(' ') +
              ` ${width - padding},${height - padding}`
            }
            fill="url(#equityGradient)"
            opacity="0.2"
          />

          {/* Gradient */}
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* X-axis labels (trade numbers) */}
          {[0, 0.25, 0.5, 0.75, 1].map((percent, i) => {
            const tradeNum = Math.round(percent * (equityCurve.length - 1));
            return (
              <text
                key={`x${i}`}
                x={padding + (percent * chartWidth)}
                y={height - padding + 20}
                textAnchor="middle"
                fill={colors.textMuted}
                fontSize="10"
              >
                {tradeNum}
              </text>
            );
          })}

          {/* X-axis label */}
          <text
            x={width / 2}
            y={height - 5}
            textAnchor="middle"
            fill={colors.textMuted}
            fontSize="11"
            fontWeight="600"
          >
            Trade Number
          </text>
        </svg>
      </div>
    );
  };

  // Render performance metrics
  const renderMetrics = () => {
    if (!metrics || !metrics.success) {
      return null;
    }

    const m = metrics;

    const metricCards = [
      {
        label: 'Total Return',
        value: `${m.overview.total_return_pct.toFixed(2)}%`,
        color: m.overview.total_return_pct >= 0 ? '#10b981' : '#ef4444',
        icon: '💰'
      },
      {
        label: 'Win Rate',
        value: `${m.win_loss.win_rate.toFixed(1)}%`,
        color: m.win_loss.win_rate >= 50 ? '#10b981' : '#f59e0b',
        icon: '🎯'
      },
      {
        label: 'Profit Factor',
        value: m.win_loss.profit_factor.toFixed(2),
        color: m.win_loss.profit_factor >= 1.5 ? '#10b981' : m.win_loss.profit_factor >= 1 ? '#f59e0b' : '#ef4444',
        icon: '📊'
      },
      {
        label: 'Sharpe Ratio',
        value: m.risk_metrics.sharpe_ratio.toFixed(2),
        color: m.risk_metrics.sharpe_ratio >= 1 ? '#10b981' : '#6b7280',
        icon: '📉'
      },
      {
        label: 'Max Drawdown',
        value: `${m.risk_metrics.max_drawdown_pct.toFixed(2)}%`,
        color: m.risk_metrics.max_drawdown_pct < 10 ? '#10b981' : m.risk_metrics.max_drawdown_pct < 20 ? '#f59e0b' : '#ef4444',
        icon: '⚠️'
      },
      {
        label: 'Total Trades',
        value: m.overview.total_trades,
        color: colors.text,
        icon: '🔄'
      }
    ];

    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem'
      }}>
        {metricCards.map((card, index) => (
          <div
            key={index}
            style={{
              backgroundColor: darkMode ? '#0f172a' : '#ffffff',
              border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
              borderRadius: '0.5rem',
              padding: '1rem'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span style={{ fontSize: '1.25rem' }}>{card.icon}</span>
              <span style={{ fontSize: '0.75rem', fontWeight: '600', color: colors.textMuted }}>
                {card.label}
              </span>
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: card.color }}>
              {card.value}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Render win/loss details
  const renderWinLossDetails = () => {
    if (!metrics || !metrics.success) return null;

    const m = metrics.win_loss;
    const total = m.num_wins + m.num_losses;

    return (
      <div style={{
        backgroundColor: darkMode ? '#0f172a' : '#ffffff',
        borderRadius: '0.5rem',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
          📊 Win/Loss Analysis
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
          {/* Wins vs Losses */}
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: '#10b981' }}>Wins: {m.num_wins}</span>
                <span style={{ fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
                  {((m.num_wins / total) * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: darkMode ? '#1e293b' : '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${(m.num_wins / total) * 100}%`,
                  backgroundColor: '#10b981'
                }} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.875rem', color: '#ef4444' }}>Losses: {m.num_losses}</span>
                <span style={{ fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
                  {((m.num_losses / total) * 100).toFixed(1)}%
                </span>
              </div>
              <div style={{ height: '8px', backgroundColor: darkMode ? '#1e293b' : '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${(m.num_losses / total) * 100}%`,
                  backgroundColor: '#ef4444'
                }} />
              </div>
            </div>
          </div>

          {/* Statistics */}
          <div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Avg Win:</span>
                <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#10b981' }}>
                  ${m.avg_win.toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Avg Loss:</span>
                <span style={{ fontSize: '0.875rem', fontWeight: '600', color: '#ef4444' }}>
                  ${m.avg_loss.toFixed(2)}
                </span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Expectancy:</span>
                <span style={{ fontSize: '0.875rem', fontWeight: '600', color: m.expectancy >= 0 ? '#10b981' : '#ef4444' }}>
                  ${m.expectancy.toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: '1.5rem' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '1.5rem'
      }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
            Performance Analytics
          </h2>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: colors.textMuted }}>
            Portfolio performance metrics and equity curve visualization
          </p>
        </div>

        <button
          onClick={fetchSimulation}
          disabled={loading}
          style={{
            padding: '0.625rem 1.25rem',
            backgroundColor: '#3b82f6',
            color: '#ffffff',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '0.875rem',
            fontWeight: '600',
            opacity: loading ? 0.6 : 1
          }}
        >
          {loading ? '⏳ Loading...' : '🔄 Refresh Simulation'}
        </button>
      </div>

      {/* Performance Metrics Cards */}
      {renderMetrics()}

      {/* Win/Loss Analysis */}
      {renderWinLossDetails()}

      {/* Equity Curve */}
      {renderEquityCurve()}

      {/* Simulation Parameters */}
      <div style={{
        marginTop: '1.5rem',
        padding: '1rem',
        backgroundColor: darkMode ? '#0f172a' : '#f8fafc',
        borderRadius: '0.5rem',
        border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`
      }}>
        <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
          Simulation Parameters
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', fontSize: '0.75rem', color: colors.textMuted }}>
          <div>Initial Capital: ${simulationParams.initial_capital.toLocaleString()}</div>
          <div>Avg Return: {simulationParams.avg_return_pct}%</div>
          <div>Std Dev: {simulationParams.std_return_pct}%</div>
          <div>Number of Trades: {simulationParams.num_trades}</div>
          <div>Win Rate: {simulationParams.win_rate}%</div>
        </div>
      </div>
    </div>
  );
}
