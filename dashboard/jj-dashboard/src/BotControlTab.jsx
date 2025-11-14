import React, { useState, useEffect } from 'react';

export function BotControlTab({ colors, darkMode, API_BASE, onNavigate, learningData }) {
  const [botRunning, setBotRunning] = useState(false);
  const [botSymbols, setBotSymbols] = useState(['BTC', 'ETH', 'SOL']);
  const [newSymbol, setNewSymbol] = useState('');
  const [botConfig, setBotConfig] = useState({
    tradeAmount: 100,
    maxPositions: 3,
    riskPerTrade: 2,
    useMLPredictions: true,
    useTechnicalIndicators: true
  });
  const [recentTrades, setRecentTrades] = useState([]);
  const [uptime, setUptime] = useState(0);
  const [startTime, setStartTime] = useState(null);

  // Update uptime counter
  useEffect(() => {
    if (!botRunning || !startTime) return;

    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setUptime(elapsed);
    }, 1000);

    return () => clearInterval(interval);
  }, [botRunning, startTime]);

  // Format uptime display
  const formatUptime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h}h ${m}m ${s}s`;
  };

  // Start bot
  const handleStartBot = async () => {
    // Validate configuration
    if (botSymbols.length === 0) {
      alert('Please add at least one symbol to trade');
      return;
    }

    if (botConfig.tradeAmount <= 0) {
      alert('Trade amount must be greater than 0');
      return;
    }

    // Start bot
    setBotRunning(true);
    setStartTime(Date.now());
    console.log('🤖 Bot started with symbols:', botSymbols);
  };

  // Stop bot
  const handleStopBot = () => {
    setBotRunning(false);
    setStartTime(null);
    setUptime(0);
    console.log('🛑 Bot stopped');
  };

  // Add symbol to bot
  const handleAddSymbol = () => {
    if (!newSymbol) return;

    const symbol = newSymbol.toUpperCase().trim();

    if (botSymbols.includes(symbol)) {
      alert('Symbol already added');
      return;
    }

    setBotSymbols([...botSymbols, symbol]);
    setNewSymbol('');

    // TODO: Auto-train ML model for new symbol
    console.log(`✅ Added ${symbol} to bot trading list`);
  };

  // Remove symbol from bot
  const handleRemoveSymbol = (symbol) => {
    setBotSymbols(botSymbols.filter(s => s !== symbol));
  };

  // Navigate to Charts tab with selected symbol
  const viewCharts = (symbol) => {
    if (onNavigate) {
      onNavigate('charts', symbol);
    }
  };

  // Update config
  const updateConfig = (key, value) => {
    setBotConfig({ ...botConfig, [key]: value });
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
            🤖 Trading Bot
          </h2>
          <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem', color: colors.textMuted }}>
            Automated trading with machine learning
          </p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Bot Control */}
        <div style={{
          backgroundColor: darkMode ? '#0f172a' : '#ffffff',
          border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          borderRadius: '0.5rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
            🎛️ Bot Control
          </h3>

          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
              <div style={{
                width: '12px',
                height: '12px',
                borderRadius: '50%',
                backgroundColor: botRunning ? '#10b981' : '#6b7280'
              }} />
              <span style={{ fontSize: '1rem', fontWeight: '600', color: colors.text }}>
                Status: {botRunning ? 'RUNNING' : 'STOPPED'}
              </span>
            </div>

            {botRunning && (
              <div style={{ fontSize: '0.875rem', color: colors.textMuted, marginLeft: '1.5rem' }}>
                Uptime: {formatUptime(uptime)}
              </div>
            )}
          </div>

          {botRunning ? (
            <button
              onClick={handleStopBot}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#ef4444',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '600',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#dc2626'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#ef4444'}
            >
              🛑 Stop Bot
            </button>
          ) : (
            <button
              onClick={handleStartBot}
              style={{
                width: '100%',
                padding: '0.75rem',
                backgroundColor: '#10b981',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontSize: '1rem',
                fontWeight: '600',
                transition: 'background-color 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#059669'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#10b981'}
            >
              ▶️ Start Bot
            </button>
          )}
        </div>

        {/* Active Symbols */}
        <div style={{
          backgroundColor: darkMode ? '#0f172a' : '#ffffff',
          border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          borderRadius: '0.5rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
            📊 Active Trading Symbols
          </h3>

          <div style={{ marginBottom: '1rem', maxHeight: '120px', overflowY: 'auto' }}>
            {botSymbols.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '1rem', color: colors.textMuted, fontSize: '0.875rem' }}>
                No symbols added yet
              </div>
            ) : (
              botSymbols.map((symbol) => (
                <div
                  key={symbol}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.5rem',
                    marginBottom: '0.5rem',
                    backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                    borderRadius: '0.25rem'
                  }}
                >
                  <span style={{ fontWeight: '600', color: colors.text }}>{symbol}</span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => viewCharts(symbol)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: '#3b82f6',
                        color: '#ffffff',
                        border: 'none',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      📈 Charts
                    </button>
                    <button
                      onClick={() => handleRemoveSymbol(symbol)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        backgroundColor: darkMode ? '#334155' : '#e2e8f0',
                        color: colors.text,
                        border: 'none',
                        borderRadius: '0.25rem',
                        cursor: 'pointer',
                        fontSize: '0.75rem',
                        fontWeight: '500'
                      }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
              placeholder="Enter symbol (e.g., ADA)"
              style={{
                flex: 1,
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                borderRadius: '0.25rem',
                color: colors.text,
                fontSize: '0.875rem',
                outline: 'none'
              }}
            />
            <button
              onClick={handleAddSymbol}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#3b82f6',
                color: '#ffffff',
                border: 'none',
                borderRadius: '0.25rem',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '600'
              }}
            >
              Add
            </button>
          </div>
        </div>
      </div>

      {/* Learning Dashboard (from previous Learning tab) */}
      <div style={{
        backgroundColor: darkMode ? '#0f172a' : '#ffffff',
        border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
        borderRadius: '0.5rem',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
          🧠 Learning & Strategy
        </h3>

        {learningData ? (
          <>
            {/* Current State */}
            <div style={{ marginBottom: '1.5rem', padding: '1rem', backgroundColor: darkMode ? '#1e293b' : '#f8fafc', borderRadius: '0.5rem' }}>
              <h4 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>Current State</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Recommended Strategy</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#3b82f6' }}>
                    {learningData.current_state?.recommended_strategy || 'None'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Market Regime</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#fbbf24' }}>
                    {learningData.current_state?.market_regime || 'Unknown'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Confidence</div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 'bold', color: '#10b981' }}>
                    {((learningData.current_state?.regime_confidence || 0) * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            </div>

            {/* Learning Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
              <div style={{ textAlign: 'center', padding: '0.75rem', backgroundColor: darkMode ? '#1e293b' : '#f8fafc', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
                  {learningData.learning_stats?.total_evaluations || 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Total Evaluations</div>
              </div>
              <div style={{ textAlign: 'center', padding: '0.75rem', backgroundColor: darkMode ? '#1e293b' : '#f8fafc', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
                  {learningData.learning_stats?.strategy_switches || 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Strategy Switches</div>
              </div>
              <div style={{ textAlign: 'center', padding: '0.75rem', backgroundColor: darkMode ? '#1e293b' : '#f8fafc', borderRadius: '0.5rem' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
                  {learningData.learning_stats?.regime_changes || 0}
                </div>
                <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>Regime Changes (24h)</div>
              </div>
            </div>
          </>
        ) : (
          <p style={{ color: colors.textMuted, textAlign: 'center', padding: '1rem' }}>Loading learning data...</p>
        )}
      </div>

      {/* Bot Configuration */}
      <div style={{
        backgroundColor: darkMode ? '#0f172a' : '#ffffff',
        border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
        borderRadius: '0.5rem',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
          ⚙️ Bot Configuration
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: colors.text, marginBottom: '0.25rem' }}>
              Trade Amount ($)
            </label>
            <input
              type="number"
              value={botConfig.tradeAmount}
              onChange={(e) => updateConfig('tradeAmount', parseFloat(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                borderRadius: '0.25rem',
                color: colors.text,
                fontSize: '0.875rem'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: colors.text, marginBottom: '0.25rem' }}>
              Max Positions
            </label>
            <input
              type="number"
              value={botConfig.maxPositions}
              onChange={(e) => updateConfig('maxPositions', parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                borderRadius: '0.25rem',
                color: colors.text,
                fontSize: '0.875rem'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '500', color: colors.text, marginBottom: '0.25rem' }}>
              Risk Per Trade (%)
            </label>
            <input
              type="number"
              value={botConfig.riskPerTrade}
              onChange={(e) => updateConfig('riskPerTrade', parseFloat(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                borderRadius: '0.25rem',
                color: colors.text,
                fontSize: '0.875rem'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', fontWeight: '500', color: colors.text, marginTop: '1.75rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={botConfig.useMLPredictions}
                onChange={(e) => updateConfig('useMLPredictions', e.target.checked)}
                style={{ width: '16px', height: '16px' }}
              />
              Use ML Predictions
            </label>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div style={{
        backgroundColor: darkMode ? '#0f172a' : '#ffffff',
        border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
        borderRadius: '0.5rem',
        padding: '1.5rem'
      }}>
        <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
          🔗 Quick Actions
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.75rem' }}>
          <button
            onClick={() => onNavigate && onNavigate('charts')}
            style={{
              padding: '0.75rem',
              backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
              border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: colors.text,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#e2e8f0'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#1e293b' : '#f8fafc'}
          >
            📈 View Charts
          </button>

          <button
            onClick={() => onNavigate && onNavigate('backtest')}
            style={{
              padding: '0.75rem',
              backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
              border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: colors.text,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#e2e8f0'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#1e293b' : '#f8fafc'}
          >
            🧪 Run Backtest
          </button>

          <button
            onClick={() => onNavigate && onNavigate('analytics')}
            style={{
              padding: '0.75rem',
              backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
              border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: colors.text,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#e2e8f0'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#1e293b' : '#f8fafc'}
          >
            📊 Analytics
          </button>

          <button
            onClick={async () => {
              if (botSymbols.length === 0) {
                alert('Add symbols first');
                return;
              }
              alert(`Training ML models for: ${botSymbols.join(', ')}`);
              // TODO: Trigger ML training API
            }}
            style={{
              padding: '0.75rem',
              backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
              border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              color: colors.text,
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#e2e8f0'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#1e293b' : '#f8fafc'}
          >
            🤖 Train ML Model
          </button>
        </div>
      </div>
    </div>
  );
}
