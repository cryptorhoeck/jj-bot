import React, { useState, useMemo } from 'react';

export function DataTab({ colors, darkMode, API_BASE, trades, summary }) {
  const [viewMode, setViewMode] = useState('trades'); // 'trades' or 'analytics'

  // Calculate real analytics from trades
  const analytics = useMemo(() => {
    if (!trades || trades.length === 0) {
      return null;
    }

    // Performance by symbol
    const bySymbol = {};
    trades.forEach(trade => {
      if (!bySymbol[trade.symbol]) {
        bySymbol[trade.symbol] = {
          trades: 0,
          wins: 0,
          losses: 0,
          totalPnL: 0
        };
      }
      bySymbol[trade.symbol].trades++;
      bySymbol[trade.symbol].totalPnL += trade.pnl || 0;
      if (trade.pnl >= 0) {
        bySymbol[trade.symbol].wins++;
      } else {
        bySymbol[trade.symbol].losses++;
      }
    });

    const symbolStats = Object.entries(bySymbol).map(([symbol, stats]) => ({
      symbol,
      ...stats,
      winRate: (stats.wins / stats.trades) * 100,
      avgPnL: stats.totalPnL / stats.trades
    })).sort((a, b) => b.totalPnL - a.totalPnL);

    // Performance by strategy
    const byStrategy = {};
    trades.forEach(trade => {
      const strategy = trade.strategy || 'unknown';
      if (!byStrategy[strategy]) {
        byStrategy[strategy] = {
          trades: 0,
          wins: 0,
          losses: 0,
          totalPnL: 0
        };
      }
      byStrategy[strategy].trades++;
      byStrategy[strategy].totalPnL += trade.pnl || 0;
      if (trade.pnl >= 0) {
        byStrategy[strategy].wins++;
      } else {
        byStrategy[strategy].losses++;
      }
    });

    const strategyStats = Object.entries(byStrategy).map(([strategy, stats]) => ({
      strategy,
      ...stats,
      winRate: (stats.wins / stats.trades) * 100,
      avgPnL: stats.totalPnL / stats.trades
    })).sort((a, b) => b.totalPnL - a.totalPnL);

    // Performance by hour
    const byHour = {};
    for (let i = 0; i < 24; i++) {
      byHour[i] = { trades: 0, totalPnL: 0, wins: 0 };
    }
    trades.forEach(trade => {
      const hour = new Date(trade.timestamp).getHours();
      byHour[hour].trades++;
      byHour[hour].totalPnL += trade.pnl || 0;
      if (trade.pnl >= 0) byHour[hour].wins++;
    });

    const hourStats = Object.entries(byHour)
      .filter(([_, stats]) => stats.trades > 0)
      .map(([hour, stats]) => ({
        hour: parseInt(hour),
        ...stats,
        winRate: (stats.wins / stats.trades) * 100,
        avgPnL: stats.totalPnL / stats.trades
      }))
      .sort((a, b) => b.totalPnL - a.totalPnL);

    // Best/worst trades
    const sortedByPnL = [...trades].sort((a, b) => b.pnl - a.pnl);
    const bestTrades = sortedByPnL.slice(0, 5);
    const worstTrades = sortedByPnL.slice(-5).reverse();

    return {
      symbolStats,
      strategyStats,
      hourStats,
      bestTrades,
      worstTrades
    };
  }, [trades]);

  // Data management functions
  const exportCSV = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/export`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trades_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      alert('Error exporting data: ' + error);
    }
  };

  const clearDatabase = async () => {
    if (confirm('Are you sure you want to clear all trade data? This will backup first.')) {
      try {
        await fetch(`${API_BASE}/api/data/clear`, { method: 'POST' });
        alert('Database cleared and backed up!');
        window.location.reload();
      } catch (error) {
        alert('Error clearing database: ' + error);
      }
    }
  };

  const archiveData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/archive`, { method: 'POST' });
      const data = await response.json();
      alert(data.message);
    } catch (error) {
      alert('Error archiving data: ' + error);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header with view toggle */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: '700', color: colors.text }}>
          📊 Data & Analytics
        </h1>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={() => setViewMode('trades')}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: viewMode === 'trades' ? colors.blue : colors.card,
              color: viewMode === 'trades' ? 'white' : colors.text,
              border: `2px solid ${viewMode === 'trades' ? colors.blue : colors.border}`,
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            📋 Trades
          </button>
          <button
            onClick={() => setViewMode('analytics')}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: viewMode === 'analytics' ? colors.blue : colors.card,
              color: viewMode === 'analytics' ? 'white' : colors.text,
              border: `2px solid ${viewMode === 'analytics' ? colors.blue : colors.border}`,
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontWeight: '600'
            }}
          >
            📈 Analytics
          </button>
        </div>
      </div>

      {/* Trades View */}
      {viewMode === 'trades' && (
        <>
          {/* Data Management */}
          <div style={{
            backgroundColor: colors.card,
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: `2px solid ${colors.border}`
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              💾 Data Management
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <button
                onClick={exportCSV}
                style={{
                  padding: '1rem',
                  backgroundColor: colors.blue,
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '1rem'
                }}
              >
                📥 Export CSV
              </button>
              <button
                onClick={archiveData}
                style={{
                  padding: '1rem',
                  backgroundColor: colors.yellow,
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '1rem'
                }}
              >
                📦 Archive
              </button>
              <button
                onClick={clearDatabase}
                style={{
                  padding: '1rem',
                  backgroundColor: colors.red,
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  fontWeight: '600',
                  fontSize: '1rem'
                }}
              >
                🗑️ Clear Database
              </button>
            </div>

            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb', borderRadius: '0.5rem' }}>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>
                Total Trades: <strong style={{ color: colors.text }}>{summary.total_trades}</strong> |
                Total P&L: <strong style={{ color: summary.total_pnl >= 0 ? colors.green : colors.red }}>${summary.total_pnl?.toFixed(2)}</strong> |
                Win Rate: <strong style={{ color: colors.text }}>{summary.win_rate?.toFixed(1)}%</strong>
              </p>
            </div>
          </div>

          {/* Trade History Table */}
          <div style={{
            backgroundColor: colors.card,
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: `2px solid ${colors.border}`
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              📋 Trade History ({trades.length})
            </h3>

            {trades.length > 0 ? (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: `2px solid ${colors.border}` }}>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Time</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Symbol</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Signal</th>
                      <th style={{ textAlign: 'right', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Price</th>
                      <th style={{ textAlign: 'right', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>P&L</th>
                      <th style={{ textAlign: 'left', padding: '0.75rem', color: colors.textMuted, fontWeight: '600' }}>Strategy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade, idx) => (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: `1px solid ${colors.border}`,
                          backgroundColor: idx % 2 === 0 ? 'transparent' : (darkMode ? '#1a1a1a' : '#f9fafb')
                        }}
                      >
                        <td style={{ padding: '0.75rem', color: colors.text, fontSize: '0.875rem' }}>
                          {new Date(trade.timestamp).toLocaleString()}
                        </td>
                        <td style={{ padding: '0.75rem', color: colors.text, fontWeight: '600' }}>
                          {trade.symbol}
                        </td>
                        <td style={{ padding: '0.75rem' }}>
                          <span style={{
                            padding: '0.25rem 0.75rem',
                            borderRadius: '0.25rem',
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            backgroundColor: trade.signal === 'BUY' ? `${colors.green}20` : `${colors.red}20`,
                            color: trade.signal === 'BUY' ? colors.green : colors.red
                          }}>
                            {trade.signal}
                          </span>
                        </td>
                        <td style={{ padding: '0.75rem', color: colors.text, textAlign: 'right', fontSize: '0.875rem' }}>
                          ${parseFloat(trade.last_price).toFixed(2)}
                        </td>
                        <td style={{
                          padding: '0.75rem',
                          textAlign: 'right',
                          color: trade.pnl >= 0 ? colors.green : colors.red,
                          fontWeight: '700'
                        }}>
                          ${trade.pnl?.toFixed(2)}
                        </td>
                        <td style={{ padding: '0.75rem', color: colors.textMuted, fontSize: '0.875rem' }}>
                          {trade.strategy || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p style={{ color: colors.textMuted, textAlign: 'center', padding: '3rem' }}>
                No trades yet. Start the bot to generate trades.
              </p>
            )}
          </div>
        </>
      )}

      {/* Analytics View */}
      {viewMode === 'analytics' && analytics && (
        <>
          {/* Performance by Symbol */}
          <div style={{
            backgroundColor: colors.card,
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: `2px solid ${colors.border}`
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              📊 Performance by Symbol
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              {analytics.symbolStats.map(stat => (
                <div
                  key={stat.symbol}
                  style={{
                    padding: '1rem',
                    backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                    borderRadius: '0.5rem',
                    border: `1px solid ${colors.border}`
                  }}
                >
                  <p style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.text, marginBottom: '0.5rem' }}>
                    {stat.symbol}
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.875rem' }}>
                    <p style={{ color: colors.textMuted }}>
                      Trades: <strong style={{ color: colors.text }}>{stat.trades}</strong>
                    </p>
                    <p style={{ color: colors.textMuted }}>
                      Win Rate: <strong style={{ color: colors.text }}>{stat.winRate.toFixed(1)}%</strong>
                    </p>
                    <p style={{ color: colors.textMuted }}>
                      Total P&L: <strong style={{ color: stat.totalPnL >= 0 ? colors.green : colors.red }}>
                        ${stat.totalPnL.toFixed(2)}
                      </strong>
                    </p>
                    <p style={{ color: colors.textMuted }}>
                      Avg P&L: <strong style={{ color: stat.avgPnL >= 0 ? colors.green : colors.red }}>
                        ${stat.avgPnL.toFixed(2)}
                      </strong>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Performance by Strategy */}
          <div style={{
            backgroundColor: colors.card,
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: `2px solid ${colors.border}`
          }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
              🧠 Performance by Strategy
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              {analytics.strategyStats.map((stat, idx) => (
                <div
                  key={stat.strategy}
                  style={{
                    padding: '1rem',
                    backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                    borderRadius: '0.5rem',
                    border: `1px solid ${colors.border}`
                  }}
                >
                  <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text, marginBottom: '0.5rem' }}>
                    {idx < 3 && ['🥇', '🥈', '🥉'][idx]} {stat.strategy}
                  </p>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', fontSize: '0.875rem' }}>
                    <p style={{ color: colors.textMuted }}>
                      Trades: <strong style={{ color: colors.text }}>{stat.trades}</strong>
                    </p>
                    <p style={{ color: colors.textMuted }}>
                      Win Rate: <strong style={{ color: colors.text }}>{stat.winRate.toFixed(1)}%</strong>
                    </p>
                    <p style={{ color: colors.textMuted }}>
                      Total P&L: <strong style={{ color: stat.totalPnL >= 0 ? colors.green : colors.red }}>
                        ${stat.totalPnL.toFixed(2)}
                      </strong>
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Best/Worst Trades */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            {/* Best Trades */}
            <div style={{
              backgroundColor: colors.card,
              borderRadius: '0.75rem',
              padding: '1.5rem',
              border: `2px solid ${colors.green}`
            }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
                🎯 Best Trades
              </h3>

              {analytics.bestTrades.map((trade, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: `${colors.green}10`,
                    borderRadius: '0.5rem',
                    marginBottom: '0.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                      {trade.symbol} {trade.signal}
                    </p>
                    <p style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                      {new Date(trade.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <p style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.green }}>
                    +${trade.pnl.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>

            {/* Worst Trades */}
            <div style={{
              backgroundColor: colors.card,
              borderRadius: '0.75rem',
              padding: '1.5rem',
              border: `2px solid ${colors.red}`
            }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
                ⚠️ Worst Trades
              </h3>

              {analytics.worstTrades.map((trade, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: `${colors.red}10`,
                    borderRadius: '0.5rem',
                    marginBottom: '0.5rem',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                      {trade.symbol} {trade.signal}
                    </p>
                    <p style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                      {new Date(trade.timestamp).toLocaleString()}
                    </p>
                  </div>
                  <p style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.red }}>
                    ${trade.pnl.toFixed(2)}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Performance by Time */}
          {analytics.hourStats.length > 0 && (
            <div style={{
              backgroundColor: colors.card,
              borderRadius: '0.75rem',
              padding: '1.5rem',
              border: `2px solid ${colors.border}`
            }}>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
                🕐 Best Trading Hours
              </h3>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem' }}>
                {analytics.hourStats.slice(0, 12).map(stat => (
                  <div
                    key={stat.hour}
                    style={{
                      padding: '0.75rem',
                      backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                      borderRadius: '0.375rem',
                      border: `1px solid ${colors.border}`,
                      textAlign: 'center'
                    }}
                  >
                    <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                      {stat.hour}:00
                    </p>
                    <p style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                      {stat.trades} trades
                    </p>
                    <p style={{
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      color: stat.totalPnL >= 0 ? colors.green : colors.red
                    }}>
                      ${stat.totalPnL.toFixed(0)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {viewMode === 'analytics' && !analytics && (
        <div style={{
          backgroundColor: colors.card,
          borderRadius: '0.75rem',
          padding: '3rem',
          border: `2px solid ${colors.border}`,
          textAlign: 'center'
        }}>
          <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📊</p>
          <p style={{ color: colors.textMuted, fontSize: '1rem' }}>
            No trades yet. Analytics will appear once you have trading data.
          </p>
        </div>
      )}
    </div>
  );
}
