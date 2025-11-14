import React, { useState, useEffect, useCallback } from 'react';

export function BotControlTab({ colors, darkMode, API_BASE, onNavigate, learningData }) {
  const [botRunning, setBotRunning] = useState(false);
  const [botSymbols, setBotSymbols] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [botConfig, setBotConfig] = useState({
    initial_capital: 10000,
    max_open_positions: 5,
    position_size_pct: 0.10,
    stop_loss_pct: 0.02,
    take_profit_pct: 0.05,
    use_stop_loss: true,
    use_take_profit: true
  });
  const [recentTrades, setRecentTrades] = useState([]);
  const [positions, setPositions] = useState([]);
  const [uptime, setUptime] = useState(0);
  const [startTime, setStartTime] = useState(null);
  const [botPid, setBotPid] = useState(null);
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(false);

  // Load bot configuration from backend
  const loadBotConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/config/`);
      const data = await response.json();

      if (data.success && data.config) {
        const cfg = data.config;
        setBotConfig({
          initial_capital: cfg.initial_capital || 10000,
          max_open_positions: cfg.trading_mechanics?.max_open_positions || 5,
          position_size_pct: cfg.trading_mechanics?.position_size_pct || 0.10,
          stop_loss_pct: cfg.risk_management?.stop_loss_pct || 0.02,
          take_profit_pct: cfg.risk_management?.take_profit_pct || 0.05,
          use_stop_loss: cfg.risk_management?.use_stop_loss !== false,
          use_take_profit: cfg.risk_management?.use_take_profit !== false
        });
      }
    } catch (error) {
      console.error('Failed to load bot config:', error);
    }
  }, [API_BASE]);

  // Save bot configuration to backend
  const saveBotConfig = useCallback(async (config) => {
    setConfigLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/config/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          initial_capital: config.initial_capital,
          trade_frequency_ticks: 5,
          price_generation: {
            tick_interval_seconds: 60,
            volatility_multiplier: 1.0,
            trend_strength: 1.0,
            regime_duration_multiplier: 1.0,
            inter_symbol_correlation: 0.3,
            spread_bps: 10.0
          },
          trading_mechanics: {
            commission_rate: 0.001,
            slippage_rate: 0.0005,
            position_size_pct: config.position_size_pct,
            max_open_positions: config.max_open_positions
          },
          risk_management: {
            use_stop_loss: config.use_stop_loss,
            stop_loss_pct: config.stop_loss_pct,
            use_take_profit: config.use_take_profit,
            take_profit_pct: config.take_profit_pct,
            use_trailing_stop: false,
            trailing_stop_pct: 0.03,
            max_loss_per_trade_pct: 0.02,
            max_daily_loss_pct: 0.10
          }
        })
      });

      const data = await response.json();
      if (data.success) {
        console.log('✅ Bot config saved');
      }
    } catch (error) {
      console.error('Failed to save bot config:', error);
    } finally {
      setConfigLoading(false);
    }
  }, [API_BASE]);

  // Load enabled symbols from backend
  const loadBotSymbols = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/enabled`);
      const data = await response.json();

      if (data.success && data.symbols) {
        setBotSymbols(Object.keys(data.symbols));
      }
    } catch (error) {
      console.error('Failed to load symbols:', error);
      // Fallback to default symbols
      setBotSymbols(['BTC', 'ETH', 'SOL']);
    }
  }, [API_BASE]);

  // Fetch bot status from backend
  const fetchBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/status`);
      const data = await response.json();

      if (data.running) {
        setBotRunning(true);
        setBotPid(data.pid);
        if (!startTime) {
          setStartTime(Date.now() - (uptime * 1000)); // Approximate start time
        }
      } else {
        setBotRunning(false);
        setBotPid(null);
        setStartTime(null);
        setUptime(0);
      }
    } catch (error) {
      console.error('Failed to fetch bot status:', error);
    }
  }, [API_BASE, startTime, uptime]);

  // Fetch real trades from database
  const fetchTrades = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/trades?limit=10`);
      const data = await response.json();
      setRecentTrades(data.trades || []);
    } catch (error) {
      console.error('Failed to fetch trades:', error);
    }
  }, [API_BASE]);

  // Fetch positions from bot
  const fetchPositions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/services/realistic_simulator/positions`);
      const data = await response.json();
      if (data.positions) {
        setPositions(data.positions);
      }
    } catch (error) {
      console.error('Failed to fetch positions:', error);
    }
  }, [API_BASE]);

  // Load initial data on mount
  useEffect(() => {
    loadBotConfig();
    loadBotSymbols();
  }, [loadBotConfig, loadBotSymbols]);

  // Check bot status on mount and poll every 2 seconds
  useEffect(() => {
    fetchBotStatus();
    fetchTrades();
    fetchPositions();

    const interval = setInterval(() => {
      fetchBotStatus();
      if (botRunning) {
        fetchTrades();
        fetchPositions();
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [fetchBotStatus, fetchTrades, fetchPositions, botRunning]);

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

  // Start bot - Call real backend API
  const handleStartBot = async () => {
    if (loading) return;

    // Validate configuration
    if (botSymbols.length === 0) {
      alert('Please add at least one symbol to trade');
      return;
    }

    if (botConfig.tradeAmount <= 0) {
      alert('Trade amount must be greater than 0');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, {
        method: 'POST'
      });
      const data = await response.json();

      if (data.status === 'started' || data.status === 'already_running') {
        console.log('🤖 Bot started:', data.message);
        setStartTime(Date.now());
        await fetchBotStatus();
      } else {
        alert(`Failed to start bot: ${data.message}`);
      }
    } catch (error) {
      console.error('Error starting bot:', error);
      alert('Failed to start bot');
    } finally {
      setLoading(false);
    }
  };

  // Stop bot - Call real backend API
  const handleStopBot = async () => {
    if (loading) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/stop`, {
        method: 'POST'
      });
      const data = await response.json();

      console.log('🛑 Bot stopped:', data.message);
      await fetchBotStatus();
    } catch (error) {
      console.error('Error stopping bot:', error);
      alert('Failed to stop bot');
    } finally {
      setLoading(false);
    }
  };

  // Add symbol to bot
  const handleAddSymbol = async () => {
    if (!newSymbol) return;

    const symbol = newSymbol.toUpperCase().trim();

    if (botSymbols.includes(symbol)) {
      alert('Symbol already added');
      return;
    }

    try {
      // Enable symbol in backend
      const response = await fetch(`${API_BASE}/api/symbols/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, enabled: true })
      });

      const data = await response.json();

      if (data.success || response.status === 404) {
        // If symbol doesn't exist, try to add it (user might be adding custom symbol)
        if (response.status === 404) {
          const addResponse = await fetch(`${API_BASE}/api/symbols/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, coingecko_id: symbol.toLowerCase() })
          });

          if (!addResponse.ok) {
            alert('Failed to add symbol. Please check the symbol name.');
            return;
          }
        }

        // Update local state
        setBotSymbols([...botSymbols, symbol]);
        setNewSymbol('');
        console.log(`✅ Added ${symbol} to bot trading list`);
      } else {
        alert('Failed to enable symbol');
      }
    } catch (error) {
      console.error('Error adding symbol:', error);
      alert('Failed to add symbol');
    }
  };

  // Remove symbol from bot
  const handleRemoveSymbol = async (symbol) => {
    try {
      // Disable symbol in backend
      const response = await fetch(`${API_BASE}/api/symbols/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, enabled: false })
      });

      if (response.ok) {
        // Update local state
        setBotSymbols(botSymbols.filter(s => s !== symbol));
        console.log(`✅ Removed ${symbol} from bot trading list`);
      } else {
        alert('Failed to disable symbol');
      }
    } catch (error) {
      console.error('Error removing symbol:', error);
      alert('Failed to remove symbol');
    }
  };

  // Navigate to Charts tab with selected symbol
  const viewCharts = (symbol) => {
    if (onNavigate) {
      onNavigate('charts', symbol);
    }
  };

  // Update config and save to backend
  const updateConfig = (key, value) => {
    const newConfig = { ...botConfig, [key]: value };
    setBotConfig(newConfig);
    // Debounce save to avoid too many API calls
    if (updateConfig.timeout) clearTimeout(updateConfig.timeout);
    updateConfig.timeout = setTimeout(() => {
      saveBotConfig(newConfig);
    }, 1000);
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

      {/* Live Positions & Recent Trades */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        {/* Live Positions */}
        <div style={{
          backgroundColor: darkMode ? '#0f172a' : '#ffffff',
          border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          borderRadius: '0.5rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
            💼 Live Positions
          </h3>

          {positions.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: colors.textMuted, fontSize: '0.875rem' }}>
              No open positions
            </div>
          ) : (
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {positions.map((pos, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                    borderRadius: '0.25rem',
                    borderLeft: `3px solid ${pos.side === 'LONG' ? '#10b981' : '#ef4444'}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: '600', color: colors.text }}>{pos.symbol}</span>
                    <span style={{ fontSize: '0.75rem', color: pos.side === 'LONG' ? '#10b981' : '#ef4444', fontWeight: '600' }}>
                      {pos.side}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                    Size: {pos.size} | Entry: ${pos.entry_price?.toFixed(2)}
                  </div>
                  {pos.unrealized_pnl !== undefined && (
                    <div style={{ fontSize: '0.75rem', fontWeight: '600', color: pos.unrealized_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                      P&L: ${pos.unrealized_pnl.toFixed(2)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Trades */}
        <div style={{
          backgroundColor: darkMode ? '#0f172a' : '#ffffff',
          border: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          borderRadius: '0.5rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem', fontWeight: '700', color: colors.text }}>
            📜 Recent Trades
          </h3>

          {recentTrades.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem', color: colors.textMuted, fontSize: '0.875rem' }}>
              No trades yet
            </div>
          ) : (
            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
              {recentTrades.map((trade, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    marginBottom: '0.5rem',
                    backgroundColor: darkMode ? '#1e293b' : '#f8fafc',
                    borderRadius: '0.25rem',
                    borderLeft: `3px solid ${trade.pnl >= 0 ? '#10b981' : '#ef4444'}`
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: '600', color: colors.text }}>{trade.symbol}</span>
                    <span style={{ fontSize: '0.75rem', fontWeight: '600', color: trade.pnl >= 0 ? '#10b981' : '#ef4444' }}>
                      ${trade.pnl?.toFixed(2)}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                    {trade.signal} @ ${trade.last_price?.toFixed(2)}
                  </div>
                  <div style={{ fontSize: '0.7rem', color: colors.textMuted }}>
                    {new Date(trade.timestamp).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          )}
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
              Initial Capital ($)
            </label>
            <input
              type="number"
              value={botConfig.initial_capital}
              onChange={(e) => updateConfig('initial_capital', parseFloat(e.target.value))}
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
              value={botConfig.max_open_positions}
              onChange={(e) => updateConfig('max_open_positions', parseInt(e.target.value))}
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
              Position Size (%)
            </label>
            <input
              type="number"
              step="0.01"
              value={(botConfig.position_size_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('position_size_pct', parseFloat(e.target.value) / 100)}
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
              Stop Loss (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.stop_loss_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('stop_loss_pct', parseFloat(e.target.value) / 100)}
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
              Take Profit (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.take_profit_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('take_profit_pct', parseFloat(e.target.value) / 100)}
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

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '1.75rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', fontWeight: '500', color: colors.text, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={botConfig.use_stop_loss}
                onChange={(e) => updateConfig('use_stop_loss', e.target.checked)}
                style={{ width: '16px', height: '16px' }}
              />
              Use Stop Loss
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem', fontWeight: '500', color: colors.text, cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={botConfig.use_take_profit}
                onChange={(e) => updateConfig('use_take_profit', e.target.checked)}
                style={{ width: '16px', height: '16px' }}
              />
              Use Take Profit
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
