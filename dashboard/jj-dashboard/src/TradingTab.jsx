import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

export function TradingTab({ darkMode, API_BASE, learningData }) {
  const [botRunning, setBotRunning] = useState(false);
  const [loading, setLoading] = useState(false);

  const [botConfig, setBotConfig] = useState({
    initial_capital: 10000,
    max_open_positions: 5,
    position_size_pct: 0.10,
    stop_loss_pct: 0.02,
    take_profit_pct: 0.05,
    use_stop_loss: true,
    use_take_profit: true
  });

  const [botSymbols, setBotSymbols] = useState([]);
  const [newSymbol, setNewSymbol] = useState('');
  const [positions, setPositions] = useState([]);
  const [backtestExpanded, setBacktestExpanded] = useState(false);
  const [backtestResults, setBacktestResults] = useState(null);
  const [backtestRunning, setBacktestRunning] = useState(false);
  const [backtestConfig, setBacktestConfig] = useState({
    strategy: 'rsi_strategy',
    symbols: ['BTC', 'ETH']
  });

  const checkBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/status`);
      const data = await response.json();
      setBotRunning(data.running);
    } catch (error) {
      console.error('Failed to check bot status:', error);
    }
  }, [API_BASE]);

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

  const loadSymbols = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/symbols/enabled`);
      const data = await response.json();
      if (data.success && Array.isArray(data.symbols)) {
        setBotSymbols(data.symbols);
      }
    } catch (error) {
      console.error('Failed to load symbols:', error);
    }
  }, [API_BASE]);

  useEffect(() => {
    checkBotStatus();
    loadBotConfig();
    loadSymbols();

    const interval = setInterval(() => {
      checkBotStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [checkBotStatus, loadBotConfig, loadSymbols]);

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

  const startBot = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/simulator/start`, { method: 'POST' });
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
      toast.success(`${symbol} removed`);
    } catch (error) {
      console.error('Failed to remove symbol:', error);
    }
  };

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
      toast.success('Backtest completed!');
    } catch (error) {
      toast.error('Backtest failed: ' + error);
    }
    setBacktestRunning(false);
  };

  return (
    <div className="space-y-6">
      {/* Bot Status & Control */}
      <div className={`card p-6 ${botRunning ? 'card-success' : ''}`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${botRunning ? 'bg-success/10' : 'bg-[var(--bg-tertiary)]'}`}>
              <svg className={`w-7 h-7 ${botRunning ? 'text-success' : 'text-muted'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold">Trading Bot</h2>
              <div className="flex items-center gap-2 mt-1">
                <span className={`badge ${botRunning ? 'badge-live' : 'badge-warning'}`}>
                  {botRunning ? 'Running' : 'Stopped'}
                </span>
                {learningData?.current_state?.recommended_strategy && (
                  <span className="badge badge-info">
                    {learningData.current_state.recommended_strategy}
                  </span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={botRunning ? stopBot : startBot}
            disabled={loading}
            className={`btn btn-lg ${botRunning ? 'btn-danger' : 'btn-success'}`}
          >
            {loading ? (
              <div className="spinner w-5 h-5" />
            ) : botRunning ? (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                </svg>
                Stop Bot
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Start Bot
              </>
            )}
          </button>
        </div>

        {/* Strategy Info */}
        {learningData?.current_state && (
          <div className="mt-4 p-4 rounded-xl bg-[var(--bg-tertiary)]">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted uppercase tracking-wide">Active Strategy</p>
                <p className="text-lg font-semibold text-info">
                  {learningData.current_state.recommended_strategy || 'RSI Strategy'}
                </p>
              </div>
              {learningData.current_state.confidence && (
                <div className="text-right">
                  <p className="text-xs text-muted uppercase tracking-wide">Confidence</p>
                  <p className="text-lg font-semibold text-success">
                    {(learningData.current_state.confidence * 100).toFixed(0)}%
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Configuration */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          Configuration
        </h3>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div>
            <label className="input-label">Initial Capital ($)</label>
            <input
              type="number"
              value={botConfig.initial_capital}
              onChange={(e) => updateConfig('initial_capital', parseFloat(e.target.value))}
              className="input"
            />
          </div>

          <div>
            <label className="input-label">Max Open Positions</label>
            <input
              type="number"
              value={botConfig.max_open_positions}
              onChange={(e) => updateConfig('max_open_positions', parseInt(e.target.value))}
              className="input"
            />
          </div>

          <div>
            <label className="input-label">Position Size (%)</label>
            <input
              type="number"
              step="1"
              value={(botConfig.position_size_pct * 100).toFixed(0)}
              onChange={(e) => updateConfig('position_size_pct', parseFloat(e.target.value) / 100)}
              className="input"
            />
          </div>

          <div>
            <label className="input-label">Stop Loss (%)</label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.stop_loss_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('stop_loss_pct', parseFloat(e.target.value) / 100)}
              disabled={!botConfig.use_stop_loss}
              className={`input ${!botConfig.use_stop_loss ? 'opacity-50' : ''}`}
            />
          </div>

          <div>
            <label className="input-label">Take Profit (%)</label>
            <input
              type="number"
              step="0.1"
              value={(botConfig.take_profit_pct * 100).toFixed(1)}
              onChange={(e) => updateConfig('take_profit_pct', parseFloat(e.target.value) / 100)}
              disabled={!botConfig.use_take_profit}
              className={`input ${!botConfig.use_take_profit ? 'opacity-50' : ''}`}
            />
          </div>
        </div>

        {/* Checkboxes */}
        <div className="flex flex-wrap gap-6 mt-4 pt-4 border-t border-[var(--border-color)]">
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={botConfig.use_stop_loss}
              onChange={(e) => updateConfig('use_stop_loss', e.target.checked)}
              className="w-5 h-5 rounded border-2 border-[var(--border-color)] text-info focus:ring-info"
            />
            <span className="text-sm font-medium group-hover:text-info transition-colors">Use Stop Loss</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={botConfig.use_take_profit}
              onChange={(e) => updateConfig('use_take_profit', e.target.checked)}
              className="w-5 h-5 rounded border-2 border-[var(--border-color)] text-info focus:ring-info"
            />
            <span className="text-sm font-medium group-hover:text-info transition-colors">Use Take Profit</span>
          </label>
        </div>
      </div>

      {/* Trading Symbols */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <svg className="w-5 h-5 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          Trading Symbols
          <span className="badge badge-info ml-2">{botSymbols.length} active</span>
        </h3>

        {/* Add Symbol */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="Add symbol (e.g., BTC)"
            value={newSymbol}
            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
            onKeyPress={(e) => e.key === 'Enter' && handleAddSymbol()}
            className="input flex-1"
          />
          <button onClick={handleAddSymbol} className="btn btn-primary">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Add
          </button>
        </div>

        {/* Symbol Tags */}
        <div className="flex flex-wrap gap-2">
          {botSymbols.map(symbol => (
            <div
              key={symbol}
              className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-color)] group hover:border-danger transition-colors"
            >
              <span className="font-semibold">{symbol}</span>
              <button
                onClick={() => removeSymbol(symbol)}
                className="text-muted hover:text-danger transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          {botSymbols.length === 0 && (
            <p className="text-muted text-sm">No symbols added yet. Add symbols to start trading.</p>
          )}
        </div>
      </div>

      {/* Strategy Performance */}
      {learningData?.top_strategies?.length > 0 && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Strategy Performance (24h)
          </h3>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {learningData.top_strategies.slice(0, 6).map((strat, idx) => (
              <div
                key={strat.name}
                className={`p-4 rounded-xl bg-[var(--bg-tertiary)] border ${
                  strat.name === learningData.current_state?.recommended_strategy
                    ? 'border-info'
                    : 'border-[var(--border-color)]'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <p className="font-semibold flex items-center gap-2">
                    {idx === 0 && <span className="text-yellow-500">1st</span>}
                    {idx === 1 && <span className="text-gray-400">2nd</span>}
                    {idx === 2 && <span className="text-amber-600">3rd</span>}
                    {strat.name}
                  </p>
                  {strat.name === learningData.current_state?.recommended_strategy && (
                    <span className="badge badge-info text-xs">Active</span>
                  )}
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted">Win Rate</span>
                    <span className="font-semibold">{(strat.win_rate * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">P&L</span>
                    <span className={`font-semibold ${strat.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      ${strat.total_pnl.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Trades</span>
                    <span>{strat.trade_count}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Learning Insights */}
          {learningData.insights?.length > 0 && (
            <div className="mt-4 space-y-2">
              {learningData.insights.map((insight, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg ${insight.type === 'suggestion' ? 'bg-info/10' : 'bg-warning/10'}`}
                >
                  <p className="text-sm flex items-center gap-2">
                    {insight.type === 'suggestion' ? (
                      <svg className="w-4 h-4 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    ) : (
                      <svg className="w-4 h-4 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    )}
                    {insight.message}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Backtest Section */}
      <div className="card">
        <button
          onClick={() => setBacktestExpanded(!backtestExpanded)}
          className="w-full p-6 flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Backtest
            <span className="badge badge-info text-xs ml-2">Optional</span>
          </h3>
          <svg className={`w-5 h-5 transition-transform ${backtestExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {backtestExpanded && (
          <div className="px-6 pb-6 border-t border-[var(--border-color)]">
            <p className="text-sm text-muted mt-4 mb-4">
              Test strategies on historical data before going live
            </p>

            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="input-label">Strategy</label>
                <select
                  value={backtestConfig.strategy}
                  onChange={(e) => setBacktestConfig({ ...backtestConfig, strategy: e.target.value })}
                  className="input"
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
              className="btn btn-primary"
            >
              {backtestRunning ? (
                <>
                  <div className="spinner w-4 h-4" />
                  Running...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  </svg>
                  Run Backtest
                </>
              )}
            </button>

            {backtestResults && (
              <div className="mt-4 p-4 rounded-xl bg-[var(--bg-tertiary)]">
                <p className="font-semibold mb-2">Results</p>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted">Win Rate</p>
                    <p className="font-semibold">{backtestResults.win_rate?.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-muted">Total P&L</p>
                    <p className={`font-semibold ${backtestResults.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      ${backtestResults.total_pnl?.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
