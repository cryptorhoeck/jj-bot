import React from 'react';

export function DashboardTab({ colors, darkMode, summary, trades, botRunning, learningData, onNavigate }) {
  // Calculate additional metrics
  const recentTrades = trades.slice(0, 10);
  const todayTrades = trades.filter(t => {
    const tradeDate = new Date(t.timestamp);
    const today = new Date();
    return tradeDate.toDateString() === today.toDateString();
  });

  const todayPnL = todayTrades.reduce((sum, t) => sum + (t.pnl || 0), 0);

  // Get winning/losing streaks
  let currentStreak = 0;
  let streakType = null;
  for (let i = 0; i < trades.length && i < 10; i++) {
    const isWin = trades[i].pnl >= 0;
    if (i === 0) {
      streakType = isWin ? 'win' : 'loss';
      currentStreak = 1;
    } else if ((streakType === 'win' && isWin) || (streakType === 'loss' && !isWin)) {
      currentStreak++;
    } else {
      break;
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Hero Section */}
      <div style={{
        background: `linear-gradient(135deg, ${colors.blue}20 0%, ${colors.green}20 100%)`,
        borderRadius: '0.75rem',
        padding: '2rem',
        border: `2px solid ${colors.border}`
      }}>
        <h1 style={{ fontSize: '2rem', fontWeight: '700', color: colors.text, marginBottom: '0.5rem' }}>
          Welcome to JJ-Bot 🦍
        </h1>
        <p style={{ fontSize: '1rem', color: colors.textMuted }}>
          Adaptive trading bot with real-time strategy learning
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: '1rem',
          marginTop: '1.5rem'
        }}>
          <div style={{
            backgroundColor: colors.card,
            padding: '1rem',
            borderRadius: '0.5rem',
            border: `1px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Bot Status</p>
            <p style={{ fontSize: '1.5rem', fontWeight: '600', color: botRunning ? colors.green : colors.red }}>
              {botRunning ? '🟢 Active' : '🔴 Offline'}
            </p>
          </div>

          {learningData && learningData.current_state && (
            <div style={{
              backgroundColor: colors.card,
              padding: '1rem',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`
            }}>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Active Strategy</p>
              <p style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.blue }}>
                {learningData.current_state.recommended_strategy || 'rsi_strategy'}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Key Metrics */}
      <div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📊 Performance Overview
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {/* Total Trades */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Total Trades</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.text }}>
              {summary.total_trades}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              {todayTrades.length} today
            </p>
          </div>

          {/* Total P&L */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${summary.total_pnl >= 0 ? colors.green : colors.red}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Total P&L</p>
            <p style={{
              fontSize: '2rem',
              fontWeight: '700',
              color: summary.total_pnl >= 0 ? colors.green : colors.red
            }}>
              ${summary.total_pnl?.toFixed(2)}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              ${todayPnL.toFixed(2)} today
            </p>
          </div>

          {/* Win Rate */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Win Rate</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.text }}>
              {summary.win_rate?.toFixed(1)}%
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              {currentStreak > 1 && `${currentStreak}x ${streakType} streak`}
            </p>
          </div>

          {/* Avg P&L */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Avg P&L</p>
            <p style={{
              fontSize: '2rem',
              fontWeight: '700',
              color: summary.avg_pnl >= 0 ? colors.green : colors.red
            }}>
              ${summary.avg_pnl?.toFixed(2)}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              per trade
            </p>
          </div>
        </div>
      </div>

      {/* Strategy Performance & Learning Insights */}
      {learningData && learningData.top_strategies && learningData.top_strategies.length > 0 && (
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            🧠 Strategy Intelligence
          </h2>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            {learningData.top_strategies.slice(0, 3).map((strat, idx) => (
              <div
                key={strat.name}
                style={{
                  backgroundColor: colors.card,
                  padding: '1.5rem',
                  borderRadius: '0.75rem',
                  border: strat.name === learningData.current_state?.recommended_strategy
                    ? `3px solid ${colors.blue}`
                    : `2px solid ${colors.border}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                    {strat.name}
                  </p>
                  <span style={{ fontSize: '1.5rem' }}>
                    {idx === 0 && '🥇'}
                    {idx === 1 && '🥈'}
                    {idx === 2 && '🥉'}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Win Rate</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
                      {(strat.win_rate * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>P&L</span>
                    <span style={{
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      color: strat.total_pnl >= 0 ? colors.green : colors.red
                    }}>
                      ${strat.total_pnl.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Trades</span>
                    <span style={{ fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
                      {strat.trade_count}
                    </span>
                  </div>
                </div>

                {strat.name === learningData.current_state?.recommended_strategy && (
                  <div style={{
                    marginTop: '0.75rem',
                    padding: '0.5rem',
                    backgroundColor: `${colors.blue}20`,
                    borderRadius: '0.375rem',
                    textAlign: 'center'
                  }}>
                    <span style={{ fontSize: '0.75rem', color: colors.blue, fontWeight: '600' }}>
                      ⭐ ACTIVE
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Learning Insights */}
          {learningData.insights && learningData.insights.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              {learningData.insights.slice(0, 3).map((insight, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '1rem',
                    backgroundColor: insight.type === 'suggestion'
                      ? `${colors.blue}15`
                      : `${colors.yellow}15`,
                    borderRadius: '0.5rem',
                    marginBottom: '0.5rem',
                    border: `1px solid ${insight.type === 'suggestion' ? colors.blue : colors.yellow}33`
                  }}
                >
                  <p style={{ fontSize: '0.875rem', color: colors.text, margin: 0 }}>
                    {insight.type === 'suggestion' ? '💡' : 'ℹ️'} {insight.message}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Recent Activity */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: colors.text }}>
            🕐 Recent Activity
          </h2>
          {onNavigate && (
            <button
              onClick={() => onNavigate('data')}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: colors.blue,
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500'
              }}
            >
              View All Trades →
            </button>
          )}
        </div>

        <div style={{
          backgroundColor: colors.card,
          borderRadius: '0.75rem',
          padding: '1.5rem',
          border: `2px solid ${colors.border}`
        }}>
          {recentTrades.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {recentTrades.map((trade, idx) => (
                <div
                  key={idx}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem',
                    backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                    borderRadius: '0.5rem',
                    border: `1px solid ${colors.border}`
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>
                      {new Date(trade.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                  <div style={{ flex: 1 }}>
                    <p style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                      {trade.symbol}
                    </p>
                  </div>
                  <div style={{ flex: 1 }}>
                    <span style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      backgroundColor: trade.signal === 'BUY' ? `${colors.green}20` : `${colors.red}20`,
                      color: trade.signal === 'BUY' ? colors.green : colors.red
                    }}>
                      {trade.signal}
                    </span>
                  </div>
                  <div style={{ flex: 1, textAlign: 'right' }}>
                    <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>
                      ${parseFloat(trade.last_price).toFixed(2)}
                    </p>
                  </div>
                  <div style={{ flex: 1, textAlign: 'right' }}>
                    <p style={{
                      fontSize: '1rem',
                      fontWeight: '700',
                      color: trade.pnl >= 0 ? colors.green : colors.red
                    }}>
                      ${trade.pnl?.toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem' }}>
              <p style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>📭</p>
              <p style={{ color: colors.textMuted, fontSize: '1rem', marginBottom: '1rem' }}>
                No trades yet
              </p>
              {onNavigate && (
                <button
                  onClick={() => onNavigate('trading')}
                  style={{
                    padding: '0.75rem 1.5rem',
                    backgroundColor: colors.blue,
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    fontWeight: '600'
                  }}
                >
                  Start Trading Bot →
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          ⚡ Quick Actions
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {onNavigate && (
            <>
              <button
                onClick={() => onNavigate('trading')}
                style={{
                  padding: '1.5rem',
                  backgroundColor: colors.card,
                  border: `2px solid ${colors.border}`,
                  borderRadius: '0.75rem',
                  cursor: 'pointer',
                  textAlign: 'center',
                  color: colors.text,
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = colors.blue}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = colors.border}
              >
                <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</p>
                <p style={{ fontSize: '1rem', fontWeight: '600' }}>Bot Control</p>
              </button>

              <button
                onClick={() => onNavigate('charts')}
                style={{
                  padding: '1.5rem',
                  backgroundColor: colors.card,
                  border: `2px solid ${colors.border}`,
                  borderRadius: '0.75rem',
                  cursor: 'pointer',
                  textAlign: 'center',
                  color: colors.text
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = colors.blue}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = colors.border}
              >
                <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📈</p>
                <p style={{ fontSize: '1rem', fontWeight: '600' }}>Charts</p>
              </button>

              <button
                onClick={() => onNavigate('data')}
                style={{
                  padding: '1.5rem',
                  backgroundColor: colors.card,
                  border: `2px solid ${colors.border}`,
                  borderRadius: '0.75rem',
                  cursor: 'pointer',
                  textAlign: 'center',
                  color: colors.text
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = colors.blue}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = colors.border}
              >
                <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📊</p>
                <p style={{ fontSize: '1rem', fontWeight: '600' }}>Analytics</p>
              </button>

              <button
                onClick={() => onNavigate('data')}
                style={{
                  padding: '1.5rem',
                  backgroundColor: colors.card,
                  border: `2px solid ${colors.border}`,
                  borderRadius: '0.75rem',
                  cursor: 'pointer',
                  textAlign: 'center',
                  color: colors.text
                }}
                onMouseEnter={(e) => e.currentTarget.style.borderColor = colors.blue}
                onMouseLeave={(e) => e.currentTarget.style.borderColor = colors.border}
              >
                <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>💾</p>
                <p style={{ fontSize: '1rem', fontWeight: '600' }}>Export Data</p>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
