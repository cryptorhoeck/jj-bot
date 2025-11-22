import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

export function TradingTab({ colors, darkMode, API_BASE, learningData }) {
  // Bot state
  const [botRunning, setBotRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  // Configuration state
  const [botConfig, setBotConfig] = useState({
    initial_capital: 10000,
    max_open_positions: 5,
    position_size_pct: 0.10,
    stop_loss_pct: 0.02,
    take_profit_pct: 0.05,
    use_stop_loss: true,
    use_take_profit: true
  });

  // Symbols state
  const [botSymbols, setBotSymbols] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [availableSymbols] = useState([
    'BTC', 'ETH', 'SOL', 'BNB', 'ADA', 'DOT', 'LINK', 'MATIC', 'UNI', 'AVAX',
    'XRP', 'DOGE', 'TRX', 'ATOM', 'LTC', 'BCH', 'XLM', 'ETC', 'WBTC', 'SHIB'
  ]);

  // Positions state
  const [positions, setPositions] = useState([]);

  // Backtest state
  const [backtestExpanded, setBacktestExpanded] = useState(false);
  const [backtestResults, setBacktestResults] = useState(null);
  const [backtestRunning, setBacktestRunning] = useState(false);
  const [backtestConfig, setBacktestConfig] = useState({
    strategy: 'rsi_strategy',
    start_date: '',
    end_date: '',
    symbols: ['BTC', 'ETH']
  });

  // Load bot status
  const checkBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/status`);
      const data = await response.json();
      setBotRunning(data.running);
    } catch (error) {
      console.error('Failed to check bot status:', error);
    }
  }, [API_BASE]);

  // Load bot config
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

  // Load symbols
  const loadSymbols = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/enabled`);
      const data = await response.json();
      if (data.success && Array.isArray(data.symbols)) {
        setBotSymbols(data.symbols);
      } else {
        setBotSymbols([]);
      }
    } catch (error) {
      console.error('Failed to load symbols:', error);
      setBotSymbols([]);
    }
  }, [API_BASE]);

  // Load positions (placeholder - positions feature not implemented yet)
  const loadPositions = useCallback(async () => {
    try {
      // For now, just set empty array since positions endpoint doesn't exist yet
      // TODO: Implement /api/positions endpoint
      setPositions([]);
    } catch (error) {
      console.error('Failed to load positions:', error);
      setPositions([]);
    }
  }, [API_BASE]);

  useEffect(() => {
    checkBotStatus();
    loadBotConfig();
    loadSymbols();
    loadPositions();

    const interval = setInterval(() => {
      checkBotStatus();
      loadPositions();
    }, 5000);

    return () => clearInterval(interval);
  }, [checkBotStatus, loadBotConfig, loadSymbols, loadPositions]);

  // Save config (debounced)
  const saveBotConfig = async (config) => {
    try {
      const payload = {
        initial_capital: config.initial_capital,
        trading_mechanics: {
          max_open_positions: config.max_open_positions,
          position_size_pct: config.position_size_pct
        },
        risk_management: {
          stop_loss_pct: config.stop_loss_pct,
          take_profit_pct: config.take_profit_pct,
          use_stop_loss: config.use_stop_loss,
          use_take_profit: config.use_take_profit
        }
      };

      await fetch(`${API_BASE}/api/simulator/config/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error('Failed to save config:', error);
    }
  };

  const updateConfig = (key, value) => {
    const newConfig = { ...botConfig, [key]: value };
    setBotConfig(newConfig);
    if (updateConfig.timeout) clearTimeout(updateConfig.timeout);
    updateConfig.timeout = setTimeout(() => {
      saveBotConfig(newConfig);
    }, 1000);
  };

  // Bot controls
  const startBot = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, {
        method: 'POST'
      });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setBotRunning(true);
        toast.success('Trading bot started successfully!');
      }
    } catch (error) {
      toast.error('Error starting bot: ' + error);
    }
    setLoading(false);
  };

  const stopBot = async () => {
    setLoading(true);
    try {
      await fetch(`${API_BASE}/api/simulator/stop`, { method: 'POST' });
      setBotRunning(false);
      toast.success('Trading bot stopped');
    } catch (error) {
      toast.error('Error stopping bot: ' + error);
    }
    setLoading(false);
  };

  // Symbol management
  const handleAddSymbol = async () => {
    const symbol = newSymbol.toUpperCase().trim();
    if (!symbol) return;

    try {
      const response = await fetch(`${API_BASE}/api/symbols/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, enabled: true })
      });

      if (response.status === 404) {
        await fetch(`${API_BASE}/api/symbols/add`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol, coingecko_id: symbol.toLowerCase() })
        });
      }

      setBotSymbols([...botSymbols, symbol]);
      setNewSymbol('');
      toast.success(`${symbol} added to trading list`);
    } catch (error) {
      toast.error('Failed to add symbol');
    }
  };

  const removeSymbol = async (symbol) => {
    try {
      await fetch(`${API_BASE}/api/symbols/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, enabled: false })
      });
      setBotSymbols(botSymbols.filter(s => s !== symbol));
    } catch (error) {
      console.error('Failed to remove symbol:', error);
    }
  };

  // Backtest
  const runBacktest = async () => {
    setBacktestRunning(true);
    try {
      const response = await fetch(`${API_BASE}/api/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(backtestConfig)
      });
      const data = await response.json();
      setBacktestResults(data);
      toast.success('Backtest completed successfully!');
    } catch (error) {
      toast.error('Backtest failed: ' + error);
    }
    setBacktestRunning(false);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Bot Status & Control */}
      <div style={{
        border: `2px solid ${botRunning ? colors.green : colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: colors.text }}>
              🤖 Trading Bot
            </h2>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginTop: '0.25rem' }}>
              Status: {botRunning ? '🟢 Running' : '🔴 Stopped'}
            </p>
          </div>
          <button
            onClick={botRunning ? stopBot : startBot}
            disabled={loading}
            style={{
              padding: '0.75rem 2rem',
              backgroundColor: botRunning ? colors.red : colors.green,
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.6 : 1
            }}
          >
            {loading ? '⏳ Loading...' : (botRunning ? '⏹️ Stop Bot' : '▶️ Start Bot')}
          </button>
        </div>

        {/* Current Strategy (from learning system) */}
        {learningData && learningData.current_state && (
          <div style={{
            backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
            padding: '1rem',
            borderRadius: '0.5rem',
            marginTop: '1rem'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Active Strategy</p>
                <p style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.blue }}>
                  {learningData.current_state.recommended_strategy || 'rsi_strategy'}
                </p>
              </div>
              {learningData.current_state.confidence && (
                <div>
                  <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Confidence</p>
                  <p style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.green }}>
                    {(learningData.current_state.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Configuration */}
      <div style={{
        border: `2px solid ${colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card
      }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          ⚙️ Configuration
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          {/* Initial Capital */}
          <div>
            <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
              Initial Capital ($)
            </label>
            <input
              type="number"
              value={botConfig.initial_capital}
              onChange={(e) => updateConfig('initial_capital', parseFloat(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem'
              }}
            />
          </div>

          {/* Max Positions */}
          <div>
            <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
              Max Open Positions
            </label>
            <input
              type="number"
              value={botConfig.max_open_positions}
              onChange={(e) => updateConfig('max_open_positions', parseInt(e.target.value))}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem'
              }}
            />
          </div>

          {/* Position Size */}
          <div>
            <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
              Position Size (% of capital)
            </label>
            <input
              type="number"
              step="0.01"
              value={(botConfig.position_size_pct * 100).toFixed(0)}
              onChange={(e) => updateConfig('position_size_pct', parseFloat(e.target.value) / 100)}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem'
              }}
            />
          </div>

          {/* Stop Loss */}
          <div>
            <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
              Stop Loss (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.stop_loss_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('stop_loss_pct', parseFloat(e.target.value) / 100)}
              disabled={!botConfig.use_stop_loss}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                opacity: botConfig.use_stop_loss ? 1 : 0.5
              }}
            />
          </div>

          {/* Take Profit */}
          <div>
            <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
              Take Profit (%)
            </label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.take_profit_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('take_profit_pct', parseFloat(e.target.value) / 100)}
              disabled={!botConfig.use_take_profit}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                opacity: botConfig.use_take_profit ? 1 : 0.5
              }}
            />
          </div>
        </div>

        {/* Checkboxes */}
        <div style={{ display: 'flex', gap: '2rem', marginTop: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={botConfig.use_stop_loss}
              onChange={(e) => updateConfig('use_stop_loss', e.target.checked)}
            />
            <span style={{ color: colors.text }}>Use Stop Loss</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={botConfig.use_take_profit}
              onChange={(e) => updateConfig('use_take_profit', e.target.checked)}
            />
            <span style={{ color: colors.text }}>Use Take Profit</span>
          </label>
        </div>
      </div>

      {/* Symbols */}
      <div style={{
        border: `2px solid ${colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card
      }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📊 Trading Symbols ({botSymbols.length})
        </h3>

        {/* Add symbol */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <input
            type="text"
            placeholder="Add symbol (e.g., BTC)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
            style={{
              flex: 1,
              padding: '0.5rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.375rem'
            }}
          />
          <button
            onClick={handleAddSymbol}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: colors.blue,
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            + Add
          </button>
        </div>

        {/* Symbol list */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
          {botSymbols.map(symbol => (
            <div
              key={symbol}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 0.75rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                borderRadius: '0.375rem',
                border: `1px solid ${colors.border}`
              }}
            >
              <span style={{ color: colors.text, fontWeight: '500' }}>{symbol}</span>
              <button
                onClick={() => removeSymbol(symbol)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: colors.red,
                  cursor: 'pointer',
                  padding: '0',
                  fontSize: '1rem'
                }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Learning System Performance */}
      {learningData && learningData.top_strategies && learningData.top_strategies.length > 0 && (
        <div style={{
          border: `2px solid ${colors.border}`,
          borderRadius: '0.75rem',
          padding: '1.5rem',
          backgroundColor: colors.card
        }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            🧠 Strategy Performance (Last 24h)
          </h3>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            {learningData.top_strategies.slice(0, 6).map((strat, idx) => (
              <div
                key={strat.name}
                style={{
                  padding: '1rem',
                  backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                  borderRadius: '0.5rem',
                  border: strat.name === learningData.current_state?.recommended_strategy
                    ? `2px solid ${colors.blue}`
                    : `1px solid ${colors.border}`
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <p style={{ fontSize: '0.875rem', fontWeight: '600', color: colors.text }}>
                    {idx === 0 && '🥇 '}
                    {idx === 1 && '🥈 '}
                    {idx === 2 && '🥉 '}
                    {strat.name}
                  </p>
                </div>
                <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                  <p style={{ color: colors.textMuted }}>
                    Win Rate: <span style={{ color: colors.text, fontWeight: '600' }}>
                      {(strat.win_rate * 100).toFixed(0)}%
                    </span>
                  </p>
                  <p style={{ color: colors.textMuted }}>
                    P&L: <span style={{ color: strat.total_pnl >= 0 ? colors.green : colors.red, fontWeight: '600' }}>
                      ${strat.total_pnl.toFixed(2)}
                    </span>
                  </p>
                  <p style={{ color: colors.textMuted }}>
                    Trades: <span style={{ color: colors.text }}>{strat.trade_count}</span>
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Learning insights */}
          {learningData.insights && learningData.insights.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              {learningData.insights.map((insight, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: insight.type === 'suggestion' ? `${colors.blue}20` : `${colors.yellow}20`,
                    borderRadius: '0.375rem',
                    marginBottom: '0.5rem'
                  }}
                >
                  <p style={{ fontSize: '0.875rem', color: colors.text }}>
                    {insight.type === 'suggestion' ? '💡' : 'ℹ️'} {insight.message}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Current Positions */}
      <div style={{
        border: `2px solid ${colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card
      }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📈 Open Positions ({positions.length})
        </h3>

        {positions.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${colors.border}` }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Symbol</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Side</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Entry</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Current</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>P&L</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: colors.textMuted }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, idx) => (
                  <tr key={idx} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: '0.5rem', color: colors.text, fontWeight: '600' }}>{pos.symbol}</td>
                    <td style={{ padding: '0.5rem', color: pos.side === 'LONG' ? colors.green : colors.red }}>
                      {pos.side}
                    </td>
                    <td style={{ padding: '0.5rem', color: colors.text }}>${pos.entry_price?.toFixed(2)}</td>
                    <td style={{ padding: '0.5rem', color: colors.text }}>${pos.current_price?.toFixed(2)}</td>
                    <td style={{
                      padding: '0.5rem',
                      color: pos.unrealized_pnl >= 0 ? colors.green : colors.red,
                      fontWeight: '600'
                    }}>
                      ${pos.unrealized_pnl?.toFixed(2)}
                    </td>
                    <td style={{ padding: '0.5rem', color: colors.textMuted, fontSize: '0.875rem' }}>
                      {pos.status || 'OPEN'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: colors.textMuted, textAlign: 'center', padding: '2rem' }}>
            No open positions. Start the bot to begin trading.
          </p>
        )}
      </div>

      {/* Backtest (Collapsible) */}
      <div style={{
        border: `2px solid ${colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card
      }}>
        <div
          onClick={() => setBacktestExpanded(!backtestExpanded)}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: 'pointer'
          }}
        >
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.text }}>
            📊 Backtest (Optional)
          </h3>
          <span style={{ fontSize: '1.5rem', color: colors.text }}>
            {backtestExpanded ? '▼' : '▶'}
          </span>
        </div>

        {backtestExpanded && (
          <div style={{ marginTop: '1rem' }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '1rem' }}>
              Test strategies on historical data before going live
            </p>

            {/* Backtest config */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1rem' }}>
              <div>
                <label style={{ fontSize: '0.875rem', color: colors.textMuted, display: 'block', marginBottom: '0.5rem' }}>
                  Strategy
                </label>
                <select
                  value={backtestConfig.strategy}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, strategy: e.target.value })}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                    color: colors.text,
                    border: `1px solid ${colors.border}`,
                    borderRadius: '0.375rem'
                  }}
                >
                  <option value="rsi_strategy">RSI Strategy</option>
                  <option value="momentum">Momentum</option>
                  <option value="trend_following">Trend Following</option>
                  <option value="mean_reversion">Mean Reversion</option>
                </select>
              </div>
            </div>

            <button
              onClick={runBacktest}
              disabled={backtestRunning}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: colors.blue,
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: backtestRunning ? 'not-allowed' : 'pointer',
                opacity: backtestRunning ? 0.6 : 1
              }}
            >
              {backtestRunning ? '⏳ Running...' : '▶️ Run Backtest'}
            </button>

            {backtestResults && (
              <div style={{
                marginTop: '1rem',
                padding: '1rem',
                backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
                borderRadius: '0.5rem'
              }}>
                <p style={{ color: colors.text, fontWeight: '600', marginBottom: '0.5rem' }}>Results:</p>
                <p style={{ color: colors.textMuted }}>Win Rate: {backtestResults.win_rate?.toFixed(1)}%</p>
                <p style={{ color: backtestResults.total_pnl >= 0 ? colors.green : colors.red }}>
                  Total P&L: ${backtestResults.total_pnl?.toFixed(2)}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
