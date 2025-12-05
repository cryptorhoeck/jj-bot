import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

// Available symbols for selection
const AVAILABLE_SYMBOLS = [
  'BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA', 'DOGE', 'TRX', 'AVAX', 'LINK',
  'DOT', 'POL', 'SHIB', 'LTC', 'BCH', 'UNI', 'XLM', 'ATOM', 'ETC', 'FIL',
  'HBAR', 'APT', 'ARB', 'OP', 'NEAR', 'INJ', 'RUNE', 'AAVE', 'GRT', 'FTM',
  'SAND', 'MANA', 'AXS', 'GALA', 'ENJ', 'CHZ', 'CRV', 'SNX', 'COMP', 'MKR',
  'SUSHI', 'YFI', '1INCH', 'BAL', 'LDO', 'RPL', 'SSV', 'GMX', 'DYDX', 'WOO'
];

export function TradingTab({ darkMode, API_BASE, learningData, sharedBotStatus, onBotStatusChange }) {
  // Use shared state from App.jsx when available, otherwise manage locally
  const [botRunning, setBotRunning] = useState(sharedBotStatus?.running || false);
  const [loading, setLoading] = useState(false);
  const [activeSection, setActiveSection] = useState('control'); // control, config, symbols, strategies

  // Sync with shared state when it changes
  useEffect(() => {
    if (sharedBotStatus) {
      setBotRunning(sharedBotStatus.running || false);
      if (sharedBotStatus.training) {
        setTrainingProgress(sharedBotStatus.training);
      }
      setTradingIQ({
        iq: sharedBotStatus.trading_iq || 0,
        level: sharedBotStatus.expertise_level || 'Untrained'
      });
    }
  }, [sharedBotStatus]);

  // Pro config state
  const [proConfig, setProConfig] = useState({
    mode: 'paper',
    initial_capital: 10000,
    max_position_pct: 0.05,
    max_positions: 10,
    stop_loss_pct: 0.02,
    take_profit_pct: 0.04,
    max_daily_loss_pct: 0.05,
    max_drawdown_pct: 0.10,
    min_signal_confidence: 0.45,
    use_rl_agent: true,
    use_edge_strategies: true,
    use_alternative_data: true,
    symbols: []
  });

  const [botStats, setBotStats] = useState({
    equity: 10000,
    positions: 0,
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0
  });

  const [selectedSymbols, setSelectedSymbols] = useState([]);
  const [symbolSearch, setSymbolSearch] = useState('');
  const [positions, setPositions] = useState([]);
  const [trainingProgress, setTrainingProgress] = useState(sharedBotStatus?.training || null);

  // Persistent Trading IQ and training history state
  const [tradingIQ, setTradingIQ] = useState({
    iq: sharedBotStatus?.trading_iq || 0,
    level: sharedBotStatus?.expertise_level || 'Untrained'
  });
  const [trainingHistory, setTrainingHistory] = useState({
    training_sessions: 0,
    total_training_episodes: 0,
    total_training_trades: 0,
    last_training_date: null,
    avg_win_rate: 0,
    avg_profit_factor: 0,
    avg_reward: 0
  });

  // Load bot status
  const checkBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/status`);
      const data = await response.json();
      setBotRunning(data.running || false);

      // Update training progress
      if (data.training) {
        setTrainingProgress(data.training);
      }

      // Update persistent Trading IQ
      setTradingIQ({
        iq: data.trading_iq || 0,
        level: data.expertise_level || 'Untrained'
      });

      // Update training history
      if (data.training_history) {
        setTrainingHistory(data.training_history);
      }

      if (data.running) {
        setBotStats({
          equity: data.equity || 10000,
          positions: data.positions || 0,
          total_trades: data.total_trades || 0,
          total_pnl: data.total_pnl || 0,
          win_rate: data.win_rate || 0
        });
      }
    } catch (error) {
      console.error('Failed to check bot status:', error);
    }
  }, [API_BASE]);

  // Load pro config
  const loadProConfig = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/config`);
      const data = await response.json();
      if (data.config) {
        setProConfig(prev => ({ ...prev, ...data.config }));
        if (data.config.symbols) {
          setSelectedSymbols(data.config.symbols.map(s => s.replace('/USDT', '')));
        }
      }
    } catch (error) {
      console.error('Failed to load pro config:', error);
    }
  }, [API_BASE]);

  // Load open positions
  const loadPositions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/positions/open`);
      const data = await response.json();
      if (data.open_positions) {
        setPositions(data.open_positions);
      }
    } catch (error) {
      console.error('Failed to load positions:', error);
    }
  }, [API_BASE]);

  useEffect(() => {
    checkBotStatus();
    loadProConfig();
    loadPositions();
    const interval = setInterval(() => {
      checkBotStatus();
      if (botRunning) loadPositions();
    }, 5000);
    return () => clearInterval(interval);
  }, [checkBotStatus, loadProConfig, loadPositions, botRunning]);

  // Save config to API
  const saveConfig = async (updates) => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const data = await response.json();
      if (data.status === 'updated') {
        toast.success('Configuration saved');
        setProConfig(prev => ({ ...prev, ...updates }));
      }
    } catch (error) {
      toast.error('Failed to save config');
    }
  };

  // Update config field with immediate save for sliders, debounce for text inputs
  const updateConfig = (field, value, immediate = false) => {
    const newConfig = { ...proConfig, [field]: value };
    setProConfig(newConfig);

    if (updateConfig.timeout) clearTimeout(updateConfig.timeout);

    if (immediate) {
      // Save immediately for sliders and toggles
      saveConfig({ [field]: value });
    } else {
      // Debounce for text inputs
      updateConfig.timeout = setTimeout(() => {
        saveConfig({ [field]: value });
      }, 500);
    }
  };

  // Toggle symbol selection
  const toggleSymbol = (symbol) => {
    const newSymbols = selectedSymbols.includes(symbol)
      ? selectedSymbols.filter(s => s !== symbol)
      : [...selectedSymbols, symbol];
    setSelectedSymbols(newSymbols);

    // Save to config as SYMBOL/USDT format
    const symbolsWithPair = newSymbols.map(s => `${s}/USDT`);
    saveConfig({ symbols: symbolsWithPair });
  };

  // Start bot in paper trading mode
  const startBot = async () => {
    setLoading(true);
    try {
      // Explicitly request paper mode to ensure we're trading, not training
      const response = await fetch(`${API_BASE}/api/pro/start?mode=paper`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setBotRunning(true);
        toast.success('Paper trading started!');
        onBotStatusChange?.(); // Notify App.jsx to refresh status
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to start bot');
      }
    } catch (error) {
      toast.error('Error starting bot');
    }
    setLoading(false);
  };

  // Stop bot
  const stopBot = async () => {
    const isTraining = trainingProgress?.is_training;

    setLoading(true);
    if (isTraining) {
      toast.loading('Stopping training and saving progress...');
    }

    try {
      const response = await fetch(`${API_BASE}/api/pro/stop`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'stopped' || data.status === 'not_running') {
        setBotRunning(false);
        setTrainingProgress(null);
        if (isTraining) {
          toast.success('Training stopped. Progress saved!');
        } else {
          toast.success('Bot stopped');
        }
        onBotStatusChange?.(); // Notify App.jsx to refresh status
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to stop');
      }
    } catch (error) {
      toast.error(isTraining ? 'Error stopping training' : 'Error stopping bot');
    }
    setLoading(false);
  };

  // Train RL model
  const trainModel = async () => {
    if (botRunning) {
      toast.error('Stop the bot before starting training');
      return;
    }

    const episodes = parseInt(prompt('How many training episodes? (Default: 100, Recommended: 500-1000)', '500'));
    if (!episodes || episodes < 1) {
      toast.error('Invalid number of episodes');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/pro/train?episodes=${episodes}`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'started') {
        setBotRunning(true);
        toast.success(`RL training started for ${episodes} episodes. This may take a while...`);
        onBotStatusChange?.(); // Notify App.jsx to refresh status
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to start training');
      }
    } catch (error) {
      toast.error('Error starting training');
    }
    setLoading(false);
  };

  // Filter symbols by search
  const filteredSymbols = AVAILABLE_SYMBOLS.filter(s =>
    s.toLowerCase().includes(symbolSearch.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Navigation Tabs */}
      <div className="flex gap-2 border-b border-[var(--border-color)] pb-2">
        {['control', 'config', 'symbols', 'strategies'].map(section => (
          <button
            key={section}
            onClick={() => setActiveSection(section)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeSection === section
                ? 'bg-info text-white'
                : 'text-muted hover:bg-[var(--bg-tertiary)]'
            }`}
          >
            {section === 'control' && '🤖 Control'}
            {section === 'config' && '⚙️ Settings'}
            {section === 'symbols' && '📊 Symbols'}
            {section === 'strategies' && '🧠 Strategies'}
          </button>
        ))}
      </div>

      {/* CONTROL SECTION */}
      {activeSection === 'control' && (
        <>
          {/* Bot Status & Control */}
          <div className={`card p-6 ${botRunning ? 'card-success' : ''}`}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${botRunning ? 'bg-success/10' : 'bg-[var(--bg-tertiary)]'}`}>
                  <span className="text-3xl">{botRunning ? '🟢' : '⚪'}</span>
                </div>
                <div>
                  <h2 className="text-xl font-bold">JJ-Bot Pro</h2>
                  <div className="flex items-center gap-2 mt-1">
                    {trainingProgress?.is_training ? (
                      <>
                        <span className="badge badge-info">
                          🧠 Training AI
                        </span>
                        <span className="text-sm text-muted">{trainingProgress.progress_pct?.toFixed(0)}% complete</span>
                      </>
                    ) : (
                      <>
                        <span className={`badge ${botRunning ? 'badge-live' : 'badge-warning'}`}>
                          {botRunning ? '▶ Trading' : '⏹ Stopped'}
                        </span>
                        {proConfig.mode === 'live' && (
                          <span className="badge badge-danger">⚠️ LIVE MONEY</span>
                        )}
                        <span className="text-sm text-muted">{selectedSymbols.length} symbols</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                {trainingProgress?.is_training ? (
                  <button
                    onClick={stopBot}
                    disabled={loading}
                    className="btn btn-lg btn-danger"
                  >
                    {loading ? <div className="spinner w-5 h-5" /> : '⏹️ Stop Training'}
                  </button>
                ) : (
                  <>
                    <button
                      onClick={botRunning ? stopBot : startBot}
                      disabled={loading}
                      className={`btn btn-lg ${botRunning ? 'btn-danger' : 'btn-success'}`}
                    >
                      {loading ? <div className="spinner w-5 h-5" /> : botRunning ? '⏹️ Stop' : '▶️ Start Trading'}
                    </button>

                    {!botRunning && (
                      <button
                        onClick={trainModel}
                        disabled={loading}
                        className="btn btn-lg btn-info"
                        title="Train the AI model to improve trading decisions"
                      >
                        🧠 Train AI
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Live Stats */}
            {botRunning && (
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-6 pt-4 border-t border-[var(--border-color)]">
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Equity</p>
                  <p className="text-lg font-bold">${botStats.equity?.toLocaleString(undefined, {maximumFractionDigits: 2})}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Positions</p>
                  <p className="text-lg font-bold">{botStats.positions}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Trades</p>
                  <p className="text-lg font-bold">{botStats.total_trades}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">P&L</p>
                  <p className={`text-lg font-bold ${botStats.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                    ${botStats.total_pnl?.toFixed(2)}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Win Rate</p>
                  <p className="text-lg font-bold">{botStats.win_rate?.toFixed(1)}%</p>
                </div>
              </div>
            )}
          </div>

          {/* Info Card - Modes Explained */}
          {!botRunning && !trainingProgress?.is_training && (
            <div className="card p-6 bg-[var(--bg-secondary)]">
              <div className="flex items-start gap-3">
                <div className="text-2xl">💡</div>
                <div className="flex-1">
                  <h3 className="font-semibold mb-2">How It Works</h3>
                  <div className="space-y-2 text-sm text-muted">
                    <p>
                      <strong className="text-[var(--text-color)]">▶️ Start Trading:</strong> Bot trades with real market data. No real money (paper trading). Click "Stop" to pause.
                    </p>
                    <p>
                      <strong className="text-[var(--text-color)]">🧠 Train AI:</strong> Trains the AI model quickly. Trading pauses during training. Click "Stop Training" anytime to cancel.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Training Progress */}
          {trainingProgress && trainingProgress.is_training && (
            <div className="card p-6 card-info">
              {/* Trading IQ Header */}
              <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--border-color)]">
                <div className="flex items-center gap-3">
                  <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
                    <span className="text-3xl font-bold text-white">{trainingProgress.trading_iq || 0}</span>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg">Trading IQ</h3>
                    <p className="text-sm">
                      <span className="font-semibold text-info">{trainingProgress.expertise_level || 'Untrained'}</span>
                      {' '}<span className="text-muted">Level</span>
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-xs text-muted">Episode</p>
                  <p className="text-lg font-bold">{trainingProgress.current_episode}/{trainingProgress.total_episodes}</p>
                </div>
              </div>

              {/* Progress Bar */}
              <div className="mb-4">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>Training Progress</span>
                  <span>{trainingProgress.progress_pct?.toFixed(1)}%</span>
                </div>
                <div className="w-full h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-300"
                    style={{ width: `${trainingProgress.progress_pct}%` }}
                  />
                </div>
              </div>

              {/* Performance Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-[var(--border-color)]">
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Avg Win Rate</p>
                  <p className="text-sm font-bold">{trainingProgress.avg_win_rate?.toFixed(1)}%</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Profit Factor</p>
                  <p className="text-sm font-bold">{trainingProgress.avg_profit_factor?.toFixed(2)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Avg Reward</p>
                  <p className="text-sm font-bold">{trainingProgress.avg_reward?.toFixed(1)}</p>
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted uppercase">Last Episode</p>
                  <p className={`text-sm font-bold ${trainingProgress.last_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                    ${trainingProgress.last_pnl?.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Open Positions */}
          {positions.length > 0 && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">📈 Open Positions ({positions.length})</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-muted text-left border-b border-[var(--border-color)]">
                      <th className="pb-2">Symbol</th>
                      <th className="pb-2">Side</th>
                      <th className="pb-2">Entry</th>
                      <th className="pb-2">Current</th>
                      <th className="pb-2">P&L</th>
                      <th className="pb-2">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {positions.map((pos, idx) => (
                      <tr key={idx} className="border-b border-[var(--border-color)]">
                        <td className="py-2 font-semibold">{pos.symbol}</td>
                        <td className={pos.side === 'long' ? 'text-success' : 'text-danger'}>
                          {pos.side?.toUpperCase()}
                        </td>
                        <td>${pos.entry_price?.toFixed(2)}</td>
                        <td>${pos.current_price?.toFixed(2)}</td>
                        <td className={pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}>
                          ${pos.unrealized_pnl?.toFixed(2)}
                        </td>
                        <td className="text-muted">{pos.signal_source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Trading IQ - Main Dashboard Card */}
          <div className={`card p-6 ${trainingProgress?.is_training ? 'card-info' : ''}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">🧠 Trading IQ</h3>
              <span className={`badge ${trainingProgress?.is_training ? 'badge-info' : tradingIQ.iq > 0 ? 'badge-success' : 'badge-warning'}`}>
                {trainingProgress?.is_training ? '⚡ Training' : tradingIQ.iq > 0 ? 'Trained' : 'Untrained'}
              </span>
            </div>
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
                <span className="text-3xl font-bold text-white">
                  {trainingProgress?.is_training ? trainingProgress.trading_iq || tradingIQ.iq : tradingIQ.iq}
                </span>
              </div>
              <div className="flex-1">
                <p className="text-xl font-semibold">
                  <span className="text-info">
                    {trainingProgress?.is_training ? trainingProgress.expertise_level || tradingIQ.level : tradingIQ.level}
                  </span>
                </p>
                {trainingProgress?.is_training ? (
                  <p className="text-sm text-muted mt-1">
                    Episode {trainingProgress.current_episode} of {trainingProgress.total_episodes}
                    <span className="ml-2 text-info font-medium">
                      ({trainingProgress.total_episodes - trainingProgress.current_episode} remaining)
                    </span>
                  </p>
                ) : (
                  <p className="text-sm text-muted mt-1">
                    {tradingIQ.iq === 0
                      ? 'Train the AI to improve trading decisions'
                      : tradingIQ.iq < 50
                        ? 'Continue training to improve performance'
                        : tradingIQ.iq < 80
                          ? 'Good progress! More training will help'
                          : 'Excellent! AI is well-trained'}
                  </p>
                )}
              </div>
            </div>

            {/* Live Training Progress Bar */}
            {trainingProgress?.is_training && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>Training Progress</span>
                  <span className="font-semibold">{trainingProgress.progress_pct?.toFixed(1)}%</span>
                </div>
                <div className="w-full h-3 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500 ease-out"
                    style={{ width: `${trainingProgress.progress_pct || 0}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted mt-1">
                  <span>Win Rate: {trainingProgress.avg_win_rate?.toFixed(1) || 0}%</span>
                  <span>Avg Reward: {trainingProgress.avg_reward?.toFixed(1) || 0}</span>
                </div>
              </div>
            )}

            {/* Training History Stats */}
            {(trainingHistory.training_sessions > 0 || tradingIQ.iq > 0) && (
              <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
                <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Sessions</p>
                    <p className="text-sm font-bold">{(trainingHistory.training_sessions || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Episodes</p>
                    <p className="text-sm font-bold">{(trainingHistory.total_training_episodes || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Trades</p>
                    <p className="text-sm font-bold">{(trainingHistory.total_training_trades || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Avg Win Rate</p>
                    <p className="text-sm font-bold">{trainingHistory.avg_win_rate?.toFixed(1) || 0}%</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Profit Factor</p>
                    <p className="text-sm font-bold">{trainingHistory.avg_profit_factor?.toFixed(2) || 0}</p>
                  </div>
                </div>
                {trainingHistory.last_training_date && (
                  <p className="text-xs text-muted text-center mt-3">
                    Last trained: {new Date(trainingHistory.last_training_date).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {/* SETTINGS SECTION */}
      {activeSection === 'config' && (
        <div className="space-y-6">
          {/* Trading Mode */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">🎯 Trading Mode</h3>
            <div className="flex gap-4">
              {['paper', 'live'].map(mode => (
                <button
                  key={mode}
                  onClick={() => updateConfig('mode', mode, true)}
                  className={`px-6 py-3 rounded-lg font-medium transition-all ${
                    proConfig.mode === mode
                      ? mode === 'live' ? 'bg-danger text-white' : 'bg-success text-white'
                      : 'bg-[var(--bg-tertiary)] text-muted hover:bg-[var(--bg-secondary)]'
                  }`}
                >
                  {mode === 'paper' ? '📝 Paper Trading' : '💰 Live Trading'}
                </button>
              ))}
            </div>
            {proConfig.mode === 'live' && (
              <p className="mt-2 text-danger text-sm">⚠️ Live trading uses real funds. Use with caution!</p>
            )}
          </div>

          {/* Capital & Position Sizing */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">💰 Capital & Position Sizing</h3>
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className="input-label">Initial Capital ($)</label>
                <input
                  type="number"
                  value={proConfig.initial_capital}
                  onChange={(e) => updateConfig('initial_capital', parseFloat(e.target.value))}
                  className="input"
                />
              </div>
              <div>
                <label className="input-label">Position Size (%)</label>
                <input
                  type="number"
                  step="1"
                  value={(proConfig.max_position_pct * 100).toFixed(0)}
                  onChange={(e) => updateConfig('max_position_pct', parseFloat(e.target.value) / 100)}
                  className="input"
                />
                <p className="text-xs text-muted mt-1">${(proConfig.initial_capital * proConfig.max_position_pct).toFixed(0)} per trade</p>
              </div>
              <div>
                <label className="input-label">Max Concurrent Positions</label>
                <input
                  type="number"
                  value={proConfig.max_positions}
                  onChange={(e) => updateConfig('max_positions', parseInt(e.target.value))}
                  className="input"
                />
              </div>
            </div>
          </div>

          {/* Risk Management */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">🛡️ Risk Management</h3>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="input-label">Stop Loss (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(proConfig.stop_loss_pct * 100).toFixed(1)}
                  onChange={(e) => updateConfig('stop_loss_pct', parseFloat(e.target.value) / 100)}
                  className="input"
                />
              </div>
              <div>
                <label className="input-label">Take Profit (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(proConfig.take_profit_pct * 100).toFixed(1)}
                  onChange={(e) => updateConfig('take_profit_pct', parseFloat(e.target.value) / 100)}
                  className="input"
                />
              </div>
              <div>
                <label className="input-label">Max Daily Loss (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(proConfig.max_daily_loss_pct * 100).toFixed(1)}
                  onChange={(e) => updateConfig('max_daily_loss_pct', parseFloat(e.target.value) / 100)}
                  className="input"
                />
              </div>
              <div>
                <label className="input-label">Max Drawdown (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={(proConfig.max_drawdown_pct * 100).toFixed(1)}
                  onChange={(e) => updateConfig('max_drawdown_pct', parseFloat(e.target.value) / 100)}
                  className="input"
                />
              </div>
            </div>
          </div>

          {/* Signal Confidence */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">🎚️ Signal Confidence Threshold</h3>
            <div className="flex items-center gap-4">
              <input
                type="range"
                min="0.1"
                max="0.9"
                step="0.05"
                value={proConfig.min_signal_confidence}
                onChange={(e) => updateConfig('min_signal_confidence', parseFloat(e.target.value), true)}
                className="flex-1 h-2 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-xl font-bold w-16 text-center">
                {(proConfig.min_signal_confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-sm text-muted mt-2">
              Lower = more trades (riskier) | Higher = fewer trades (safer)
            </p>
          </div>

          {/* Trading IQ - Always visible */}
          <div className={`card p-6 ${trainingProgress?.is_training ? 'card-info' : ''}`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">🧠 Trading IQ</h3>
              <span className={`badge ${trainingProgress?.is_training ? 'badge-info' : tradingIQ.iq > 0 ? 'badge-success' : 'badge-warning'}`}>
                {trainingProgress?.is_training ? '⚡ Training' : tradingIQ.iq > 0 ? 'Trained' : 'Untrained'}
              </span>
            </div>
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg">
                <span className="text-3xl font-bold text-white">
                  {trainingProgress?.is_training ? trainingProgress.trading_iq || tradingIQ.iq : tradingIQ.iq}
                </span>
              </div>
              <div className="flex-1">
                <p className="text-xl font-semibold">
                  <span className="text-info">
                    {trainingProgress?.is_training ? trainingProgress.expertise_level || tradingIQ.level : tradingIQ.level}
                  </span>
                </p>
                {trainingProgress?.is_training ? (
                  <p className="text-sm text-muted mt-1">
                    Episode {trainingProgress.current_episode} of {trainingProgress.total_episodes}
                    <span className="ml-2 text-info font-medium">
                      ({trainingProgress.total_episodes - trainingProgress.current_episode} remaining)
                    </span>
                  </p>
                ) : (
                  <p className="text-sm text-muted mt-1">
                    {tradingIQ.iq === 0
                      ? 'Train the AI to improve trading decisions'
                      : tradingIQ.iq < 50
                        ? 'Continue training to improve performance'
                        : tradingIQ.iq < 80
                          ? 'Good progress! More training will help'
                          : 'Excellent! AI is well-trained'}
                  </p>
                )}
              </div>
            </div>

            {/* Live Training Progress Bar */}
            {trainingProgress?.is_training && (
              <div className="mt-4">
                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>Training Progress</span>
                  <span className="font-semibold">{trainingProgress.progress_pct?.toFixed(1)}%</span>
                </div>
                <div className="w-full h-3 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500 ease-out"
                    style={{ width: `${trainingProgress.progress_pct || 0}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted mt-1">
                  <span>Win Rate: {trainingProgress.avg_win_rate?.toFixed(1) || 0}%</span>
                  <span>Avg Reward: {trainingProgress.avg_reward?.toFixed(1) || 0}</span>
                </div>
              </div>
            )}

            {/* Training History Stats - Always show if we have training data */}
            {(trainingHistory.training_sessions > 0 || tradingIQ.iq > 0) && (
              <div className="mt-4 pt-4 border-t border-[var(--border-color)]">
                <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Sessions</p>
                    <p className="text-sm font-bold">{(trainingHistory.training_sessions || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Episodes</p>
                    <p className="text-sm font-bold">{(trainingHistory.total_training_episodes || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Trades</p>
                    <p className="text-sm font-bold">{(trainingHistory.total_training_trades || 0).toLocaleString()}</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Avg Win Rate</p>
                    <p className="text-sm font-bold">{trainingHistory.avg_win_rate?.toFixed(1) || 0}%</p>
                  </div>
                  <div className="text-center">
                    <p className="text-xs text-muted uppercase">Profit Factor</p>
                    <p className="text-sm font-bold">{trainingHistory.avg_profit_factor?.toFixed(2) || 0}</p>
                  </div>
                </div>
                {trainingHistory.last_training_date && (
                  <p className="text-xs text-muted text-center mt-3">
                    Last trained: {new Date(trainingHistory.last_training_date).toLocaleDateString()}
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* SYMBOLS SECTION */}
      {activeSection === 'symbols' && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">📊 Trading Symbols</h3>
            <span className="badge badge-info">{selectedSymbols.length} selected</span>
          </div>

          {/* Search */}
          <input
            type="text"
            placeholder="Search symbols..."
            value={symbolSearch}
            onChange={(e) => setSymbolSearch(e.target.value)}
            className="input mb-4"
          />

          {/* Quick Actions */}
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => {
                setSelectedSymbols(AVAILABLE_SYMBOLS.slice(0, 10));
                saveConfig({ symbols: AVAILABLE_SYMBOLS.slice(0, 10).map(s => `${s}/USDT`) });
              }}
              className="btn btn-sm"
            >
              Top 10
            </button>
            <button
              onClick={() => {
                setSelectedSymbols(AVAILABLE_SYMBOLS.slice(0, 25));
                saveConfig({ symbols: AVAILABLE_SYMBOLS.slice(0, 25).map(s => `${s}/USDT`) });
              }}
              className="btn btn-sm"
            >
              Top 25
            </button>
            <button
              onClick={() => {
                setSelectedSymbols(AVAILABLE_SYMBOLS);
                saveConfig({ symbols: AVAILABLE_SYMBOLS.map(s => `${s}/USDT`) });
              }}
              className="btn btn-sm"
            >
              All 50
            </button>
            <button
              onClick={() => {
                setSelectedSymbols([]);
                saveConfig({ symbols: [] });
              }}
              className="btn btn-sm btn-danger"
            >
              Clear All
            </button>
          </div>

          {/* Symbol Grid */}
          <div className="grid grid-cols-5 md:grid-cols-8 lg:grid-cols-10 gap-2">
            {filteredSymbols.map(symbol => (
              <button
                key={symbol}
                onClick={() => toggleSymbol(symbol)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  selectedSymbols.includes(symbol)
                    ? 'bg-info text-white'
                    : 'bg-[var(--bg-tertiary)] text-muted hover:bg-[var(--bg-secondary)]'
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* STRATEGIES SECTION */}
      {activeSection === 'strategies' && (
        <div className="space-y-6">
          {/* Strategy Toggles */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">🧠 Strategy Components</h3>
            <div className="space-y-4">
              {/* RL Agent */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <div>
                  <p className="font-semibold">🤖 RL Agent (PPO)</p>
                  <p className="text-sm text-muted">Neural network that learns from trading experience</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proConfig.use_rl_agent}
                    onChange={(e) => updateConfig('use_rl_agent', e.target.checked, true)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-info"></div>
                </label>
              </div>

              {/* Edge Strategies */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <div>
                  <p className="font-semibold">📈 Edge Strategies</p>
                  <p className="text-sm text-muted">Funding rate, sentiment, order flow, liquidations</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proConfig.use_edge_strategies}
                    onChange={(e) => updateConfig('use_edge_strategies', e.target.checked, true)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-info"></div>
                </label>
              </div>

              {/* Alternative Data */}
              <div className="flex items-center justify-between p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <div>
                  <p className="font-semibold">📊 Alternative Data</p>
                  <p className="text-sm text-muted">Social sentiment, on-chain metrics, whale activity</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proConfig.use_alternative_data}
                    onChange={(e) => updateConfig('use_alternative_data', e.target.checked, true)}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-info"></div>
                </label>
              </div>
            </div>
          </div>

          {/* Available Strategies Info */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">📋 Edge Strategies (4)</h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="font-semibold text-info">💰 Funding Rate Arbitrage</p>
                <p className="text-sm text-muted">Trade when funding rates are extremely positive/negative</p>
              </div>
              <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="font-semibold text-warning">😨 Sentiment Extreme</p>
                <p className="text-sm text-muted">Counter-trade when fear/greed reaches extremes</p>
              </div>
              <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="font-semibold text-success">📊 Order Flow Imbalance</p>
                <p className="text-sm text-muted">Detect heavy buy/sell pressure imbalances</p>
              </div>
              <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="font-semibold text-danger">💥 Liquidation Cascade</p>
                <p className="text-sm text-muted">Trade liquidation-driven price movements</p>
              </div>
            </div>
          </div>

          {/* Strategy Performance */}
          {learningData?.top_strategies?.length > 0 && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">🏆 Strategy Performance (24h)</h3>
              <div className="grid md:grid-cols-3 gap-4">
                {learningData.top_strategies.slice(0, 6).map((strat, idx) => (
                  <div key={strat.name} className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold">{strat.name}</span>
                      {idx === 0 && <span className="text-yellow-500">🥇</span>}
                      {idx === 1 && <span className="text-gray-400">🥈</span>}
                      {idx === 2 && <span className="text-amber-600">🥉</span>}
                    </div>
                    <div className="text-sm space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted">Win Rate</span>
                        <span>{(strat.win_rate * 100).toFixed(0)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted">P&L</span>
                        <span className={strat.total_pnl >= 0 ? 'text-success' : 'text-danger'}>
                          ${strat.total_pnl?.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
