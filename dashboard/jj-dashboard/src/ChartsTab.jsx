import React, { useState, useEffect } from 'react';

export function ChartsTab({ colors, darkMode, API_BASE }) {
  const [timeRange, setTimeRange] = useState(24);
  const [equityCurve, setEquityCurve] = useState(null);
  const [pnlDist, setPnlDist] = useState(null);
  const [strategyPerf, setStrategyPerf] = useState(null);
  const [symbolPerf, setSymbolPerf] = useState(null);
  const [streaks, setStreaks] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch all analytics data
  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);

    try {
      const [equity, pnl, strategy, symbol, streakData] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/enhanced/equity-curve?hours=${timeRange}`).then(r => r.json()),
        fetch(`${API_BASE}/api/analytics/enhanced/pnl-distribution?hours=${timeRange}`).then(r => r.json()),
        fetch(`${API_BASE}/api/analytics/enhanced/strategy-performance?hours=${timeRange}`).then(r => r.json()),
        fetch(`${API_BASE}/api/analytics/enhanced/symbol-performance?hours=${timeRange}`).then(r => r.json()),
        fetch(`${API_BASE}/api/analytics/enhanced/streaks?hours=${timeRange}`).then(r => r.json())
      ]);

      setEquityCurve(equity.data);
      setPnlDist(pnl.data);
      setStrategyPerf(strategy.data);
      setSymbolPerf(symbol.data);
      setStreaks(streakData.data);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAnalytics();
    const interval = setInterval(fetchAnalytics, 30000); // Refresh every 30 seconds
    return () => clearInterval(interval);
  }, [timeRange]);

  // Render equity curve chart
  const renderEquityCurve = () => {
    if (!equityCurve || !equityCurve.capital || equityCurve.capital.length === 0) {
      return <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
        No trade data available for the selected time range
      </div>;
    }

    const capitals = equityCurve.capital;
    const maxCapital = Math.max(...capitals);
    const minCapital = Math.min(...capitals);
    const range = maxCapital - minCapital || 1;
    const initialCapital = equityCurve.initial_capital;

    return (
      <div style={{ height: '250px', position: 'relative' }}>
        <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((percent) => (
            <line
              key={percent}
              x1="0%"
              y1={`${percent}%`}
              x2="100%"
              y2={`${percent}%`}
              stroke={colors.border}
              strokeWidth="1"
              strokeDasharray="4"
            />
          ))}

          {/* Initial capital line */}
          {range > 0 && (
            <line
              x1="0%"
              y1={`${100 - ((initialCapital - minCapital) / range) * 100}%`}
              x2="100%"
              y2={`${100 - ((initialCapital - minCapital) / range) * 100}%`}
              stroke="#6b7280"
              strokeWidth="1"
              strokeDasharray="8"
            />
          )}

          {/* Equity curve */}
          <polyline
            points={capitals.map((value, index) => {
              const x = (index / (capitals.length - 1)) * 100;
              const y = 100 - ((value - minCapital) / range) * 90;
              return `${x}%,${y + 5}%`;
            }).join(' ')}
            fill="none"
            stroke={equityCurve.total_return >= 0 ? '#10b981' : '#ef4444'}
            strokeWidth="3"
            strokeLinejoin="round"
          />

          {/* Data points */}
          {capitals.map((value, index) => {
            const x = (index / (capitals.length - 1)) * 100;
            const y = 100 - ((value - minCapital) / range) * 90 + 5;
            return (
              <circle
                key={index}
                cx={`${x}%`}
                cy={`${y}%`}
                r="3"
                fill={equityCurve.total_return >= 0 ? '#10b981' : '#ef4444'}
              />
            );
          })}
        </svg>

        {/* Legend */}
        <div style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          backgroundColor: colors.card,
          border: `1px solid ${colors.border}`,
          borderRadius: '0.375rem',
          padding: '0.5rem',
          fontSize: '0.75rem'
        }}>
          <div style={{ color: colors.text, marginBottom: '0.25rem' }}>
            Return: <span style={{ fontWeight: '700', color: equityCurve.total_return >= 0 ? '#10b981' : '#ef4444' }}>
              {equityCurve.total_return >= 0 ? '+' : ''}{equityCurve.total_return}%
            </span>
          </div>
          <div style={{ color: colors.textMuted }}>
            {equityCurve.trade_count} trades
          </div>
        </div>
      </div>
    );
  };

  // Render P&L distribution histogram
  const renderPnlDistribution = () => {
    if (!pnlDist || !pnlDist.counts || pnlDist.counts.length === 0) {
      return <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
        No P&L data available
      </div>;
    }

    const maxCount = Math.max(...pnlDist.counts);

    return (
      <div>
        <div style={{ height: '200px', display: 'flex', alignItems: 'flex-end', gap: '2px', padding: '0.5rem' }}>
          {pnlDist.counts.map((count, index) => {
            const binValue = pnlDist.bins[index];
            const height = maxCount > 0 ? (count / maxCount) * 100 : 0;
            const isPositive = binValue >= 0;

            return (
              <div
                key={index}
                style={{
                  flex: 1,
                  height: `${height}%`,
                  backgroundColor: isPositive ? 'rgba(16, 185, 129, 0.6)' : 'rgba(239, 68, 68, 0.6)',
                  borderRadius: '2px 2px 0 0',
                  position: 'relative',
                  cursor: 'pointer'
                }}
                title={`${binValue.toFixed(0)}: ${count} trades`}
              />
            );
          })}
        </div>

        {/* Statistics */}
        {pnlDist.statistics && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
            gap: '0.75rem',
            marginTop: '1rem'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Win Rate</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#10b981' }}>
                {pnlDist.statistics.win_rate}%
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Profit Factor</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.text }}>
                {pnlDist.statistics.profit_factor.toFixed(2)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Avg Win</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#10b981' }}>
                ${pnlDist.statistics.avg_win.toFixed(2)}
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Avg Loss</div>
              <div style={{ fontSize: '1.25rem', fontWeight: '700', color: '#ef4444' }}>
                ${pnlDist.statistics.avg_loss.toFixed(2)}
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render strategy performance comparison
  const renderStrategyPerformance = () => {
    if (!strategyPerf || !strategyPerf.strategies || strategyPerf.strategies.length === 0) {
      return <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
        No strategy data available
      </div>;
    }

    return (
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '0.875rem', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `2px solid ${colors.border}` }}>
              <th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Strategy</th>
              <th style={{ textAlign: 'center', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Trades</th>
              <th style={{ textAlign: 'center', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Win Rate</th>
              <th style={{ textAlign: 'right', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Total P&L</th>
              <th style={{ textAlign: 'right', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Avg P&L</th>
            </tr>
          </thead>
          <tbody>
            {strategyPerf.strategies.map((strategy, index) => (
              <tr key={index} style={{ borderBottom: `1px solid ${colors.border}` }}>
                <td style={{ padding: '0.75rem', color: colors.text, fontWeight: '600' }}>{strategy.strategy}</td>
                <td style={{ padding: '0.75rem', textAlign: 'center', color: colors.text }}>{strategy.trade_count}</td>
                <td style={{ padding: '0.75rem', textAlign: 'center', color: strategy.win_rate >= 50 ? '#10b981' : '#ef4444' }}>
                  {strategy.win_rate.toFixed(1)}%
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', color: strategy.total_pnl >= 0 ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                  ${strategy.total_pnl.toFixed(2)}
                </td>
                <td style={{ padding: '0.75rem', textAlign: 'right', color: strategy.avg_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                  ${strategy.avg_pnl.toFixed(2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Render symbol performance
  const renderSymbolPerformance = () => {
    if (!symbolPerf || !symbolPerf.symbols || symbolPerf.symbols.length === 0) {
      return <div style={{ padding: '2rem', textAlign: 'center', color: colors.textMuted }}>
        No symbol data available
      </div>;
    }

    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '1rem'
      }}>
        {symbolPerf.symbols.map((symbol, index) => (
          <div
            key={index}
            style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `2px solid ${symbol.total_pnl >= 0 ? '#10b981' : '#ef4444'}`,
              textAlign: 'center'
            }}
          >
            <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text, marginBottom: '0.5rem' }}>
              {symbol.symbol}
            </div>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
              {symbol.trade_count} trades • {symbol.win_rate.toFixed(0)}% win
            </div>
            <div style={{
              fontSize: '1.25rem',
              fontWeight: '700',
              color: symbol.total_pnl >= 0 ? '#10b981' : '#ef4444'
            }}>
              ${symbol.total_pnl.toFixed(2)}
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div style={{ backgroundColor: colors.card, borderRadius: '0.5rem', padding: '1.5rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text, margin: 0 }}>
          📊 Performance Analytics
        </h2>

        {/* Time range selector */}
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Time Range:</span>
          {[1, 6, 24, 72, 168].map((hours) => (
            <button
              key={hours}
              onClick={() => setTimeRange(hours)}
              style={{
                padding: '0.375rem 0.75rem',
                backgroundColor: timeRange === hours ? colors.blue : colors.card,
                color: timeRange === hours ? 'white' : colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '0.75rem',
                fontWeight: '600'
              }}
            >
              {hours === 1 ? '1h' : hours === 6 ? '6h' : hours === 24 ? '24h' : hours === 72 ? '3d' : '7d'}
            </button>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{
          padding: '1rem',
          marginBottom: '1.5rem',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          border: '1px solid #ef4444',
          borderRadius: '0.5rem',
          color: colors.text
        }}>
          ⚠️ Error loading analytics: {error}
        </div>
      )}

      {/* Loading State */}
      {loading && !equityCurve && (
        <div style={{ padding: '3rem', textAlign: 'center', color: colors.textMuted }}>
          ⏳ Loading analytics...
        </div>
      )}

      {/* Streak Stats */}
      {streaks && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '1rem',
          marginBottom: '2rem'
        }}>
          <div style={{
            padding: '1rem',
            backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
            borderRadius: '0.5rem',
            border: `1px solid ${colors.border}`,
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.5rem' }}>
              Current Streak
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: '700',
              color: streaks.current_streak > 0 ? '#10b981' : streaks.current_streak < 0 ? '#ef4444' : colors.text
            }}>
              {streaks.current_streak > 0 ? '+' : ''}{streaks.current_streak}
            </div>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
              {streaks.current_streak_type}
            </div>
          </div>

          <div style={{
            padding: '1rem',
            backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
            borderRadius: '0.5rem',
            border: `1px solid ${colors.border}`,
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.5rem' }}>
              Longest Win Streak
            </div>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: '#10b981' }}>
              {streaks.longest_win_streak}
            </div>
          </div>

          <div style={{
            padding: '1rem',
            backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
            borderRadius: '0.5rem',
            border: `1px solid ${colors.border}`,
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.5rem' }}>
              Longest Loss Streak
            </div>
            <div style={{ fontSize: '2rem', fontWeight: '700', color: '#ef4444' }}>
              {streaks.longest_loss_streak}
            </div>
          </div>
        </div>
      )}

      {/* Equity Curve */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
        borderRadius: '0.5rem',
        border: `1px solid ${colors.border}`
      }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📈 Equity Curve
        </h3>
        {renderEquityCurve()}
      </div>

      {/* P&L Distribution */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
        borderRadius: '0.5rem',
        border: `1px solid ${colors.border}`
      }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📊 P&L Distribution
        </h3>
        {renderPnlDistribution()}
      </div>

      {/* Strategy Performance */}
      <div style={{
        marginBottom: '2rem',
        padding: '1.5rem',
        backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
        borderRadius: '0.5rem',
        border: `1px solid ${colors.border}`
      }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          🎯 Strategy Performance
        </h3>
        {renderStrategyPerformance()}
      </div>

      {/* Symbol Performance */}
      <div style={{
        padding: '1.5rem',
        backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
        borderRadius: '0.5rem',
        border: `1px solid ${colors.border}`
      }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          💰 Performance by Symbol
        </h3>
        {renderSymbolPerformance()}
      </div>
    </div>
  );
}
