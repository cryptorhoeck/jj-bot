import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

// Input component that only saves on blur or Enter (not on every keystroke)
function DelayedNumberInput({ value, onChange, className, step, min, max, multiplier = 1, decimals = 0 }) {
  const [localValue, setLocalValue] = useState(
    multiplier !== 1 ? (value * multiplier).toFixed(decimals) : value
  );

  useEffect(() => {
    const displayValue = multiplier !== 1 ? (value * multiplier).toFixed(decimals) : value;
    setLocalValue(displayValue);
  }, [value, multiplier, decimals]);

  const commitValue = () => {
    const parsed = parseFloat(localValue);
    if (!isNaN(parsed)) {
      const finalValue = multiplier !== 1 ? parsed / multiplier : parsed;
      onChange(finalValue);
    }
  };

  return (
    <input
      type="number"
      step={step}
      min={min}
      max={max}
      value={localValue}
      onChange={(e) => setLocalValue(e.target.value)}
      onBlur={commitValue}
      onKeyDown={(e) => {
        if (e.key === 'Enter') {
          e.target.blur();
        }
      }}
      className={className}
    />
  );
}

// Collapsible Section Component
function Section({ title, icon, children, defaultOpen = true, badge = null }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="card overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{icon}</span>
          <span className="font-semibold">{title}</span>
          {badge && <span className="badge badge-info ml-2">{badge}</span>}
        </div>
        <span className={`transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
      </button>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
}

// Toggle Switch Component
function ToggleSwitch({ checked, onChange, label, description }) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-tertiary)]">
      <div>
        <p className="font-medium">{label}</p>
        {description && <p className="text-sm text-muted">{description}</p>}
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-info"></div>
      </label>
    </div>
  );
}

export function TradingTab({
  darkMode,
  API_BASE,
  learningData,
  sharedBotStatus,
  onBotStatusChange,
  selectedSymbols = [],
  setSelectedSymbols,
  availableSymbols = []
}) {
  const [botRunning, setBotRunning] = useState(sharedBotStatus?.running || false);
  const [loading, setLoading] = useState(false);

  // Default config
  const DEFAULT_CONFIG = {
    mode: 'paper',
    initial_capital: 0,
    max_position_pct: 0.02,
    max_positions: 5,
    stop_loss_pct: 0.02,
    take_profit_pct: 0.04,
    max_daily_loss_pct: 0.05,
    max_drawdown_pct: 0.10,
    circuit_breaker_losses: 3,
    circuit_breaker_cooldown_minutes: 30,
    min_signal_confidence: 0.60,
    use_rl_agent: true,
    use_edge_strategies: true,
    use_alternative_data: true,
    symbols: [],
    // Auto-disable settings
    auto_disable_symbols: false,
    min_win_rate_threshold: 0.35,
    min_trades_for_evaluation: 5,
    disabled_symbols: []
  };

  const [proConfig, setProConfig] = useState({...DEFAULT_CONFIG});
  const [botStats, setBotStats] = useState({
    equity: 0,
    positions: 0,
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0
  });
  const [symbolSearch, setSymbolSearch] = useState('');
  const [positions, setPositions] = useState([]);
  const [symbolPerformance, setSymbolPerformance] = useState([]);
  const [evaluationResult, setEvaluationResult] = useState(null);
  const [evaluating, setEvaluating] = useState(false);

  // Sync with shared state
  useEffect(() => {
    if (sharedBotStatus) {
      setBotRunning(sharedBotStatus.running || false);
    }
  }, [sharedBotStatus]);

  // Load bot status
  const checkBotStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/status`);
      const data = await response.json();
      setBotRunning(data.running || false);

      if (data.running) {
        setBotStats({
          equity: data.equity || 0,
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
        if (data.config.symbols && selectedSymbols.length === 0) {
          setSelectedSymbols(data.config.symbols.map(s => s.replace('/USD', '')));
        }
      }
    } catch (error) {
      console.error('Failed to load pro config:', error);
    }
  }, [API_BASE, selectedSymbols.length, setSelectedSymbols]);

  // Load open positions
  const loadPositions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/positions`);
      const data = await response.json();
      if (data.positions) {
        setPositions(data.positions);
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
  const saveConfig = async (updates, silent = false) => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const data = await response.json();
      if (data.status === 'updated') {
        if (!silent) toast.success('Configuration saved');
        setProConfig(prev => ({ ...prev, ...updates }));
      }
    } catch (error) {
      if (!silent) toast.error('Failed to save config');
    }
  };

  // Load symbol performance data
  const loadSymbolPerformance = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/symbol-performance`);
      const data = await response.json();
      if (data.symbols) {
        setSymbolPerformance(data.symbols);
      }
    } catch (error) {
      console.error('Failed to load symbol performance:', error);
    }
  };

  // Evaluate symbols for auto-disable
  const evaluateSymbols = async () => {
    setEvaluating(true);
    setEvaluationResult(null); // Clear previous results
    try {
      const minWinRate = proConfig.min_win_rate_threshold || 0.35;
      const minTrades = proConfig.min_trades_for_evaluation || 5;
      const response = await fetch(
        `${API_BASE}/api/pro/evaluate-symbols?min_win_rate=${minWinRate}&min_trades=${minTrades}`,
        { method: 'POST' }
      );
      const data = await response.json();
      setEvaluationResult(data);
      if (data.poor_performers?.length === 0) {
        toast.success('No poor performers found!');
      }
      return data;
    } catch (error) {
      toast.error('Failed to evaluate symbols');
      return null;
    } finally {
      setEvaluating(false);
    }
  };

  // Apply auto-disable
  const applyAutoDisable = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/pro/apply-auto-disable`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'applied') {
        toast.success(`Disabled ${data.disabled?.length || 0} poor performing symbols`);
        loadProConfig(); // Reload config to get updated symbols
        setEvaluationResult(null);
      } else if (data.status === 'disabled') {
        toast.info('Auto-disable feature is not enabled');
      } else {
        toast.error(data.message || 'Failed to apply');
      }
    } catch (error) {
      toast.error('Failed to apply auto-disable');
    }
  };

  // Toggle individual symbol
  const toggleSymbolEnabled = async (symbol, enabled) => {
    try {
      const response = await fetch(
        `${API_BASE}/api/pro/toggle-symbol?symbol=${encodeURIComponent(symbol)}&enabled=${enabled}`,
        { method: 'POST' }
      );
      const data = await response.json();
      if (data.status === 'updated') {
        toast.success(`${symbol} ${enabled ? 'enabled' : 'disabled'}`);
        loadProConfig();
        loadSymbolPerformance();
      }
    } catch (error) {
      toast.error('Failed to toggle symbol');
    }
  };

  // Sync symbols to server
  useEffect(() => {
    if (selectedSymbols.length === 0) return;
    const symbolsWithPair = selectedSymbols.map(s => s.includes('/') ? s : `${s}/USD`);
    const currentSymbols = proConfig.symbols || [];
    if (JSON.stringify(symbolsWithPair.sort()) !== JSON.stringify(currentSymbols.sort())) {
      const timeoutId = setTimeout(() => {
        saveConfig({ symbols: symbolsWithPair }, true);
      }, 500);
      return () => clearTimeout(timeoutId);
    }
  }, [selectedSymbols]);

  // Update config
  const updateConfig = (field, value, immediate = false) => {
    const newConfig = { ...proConfig, [field]: value };
    setProConfig(newConfig);
    if (updateConfig.timeout) clearTimeout(updateConfig.timeout);
    if (immediate) {
      saveConfig({ [field]: value });
    } else {
      updateConfig.timeout = setTimeout(() => {
        saveConfig({ [field]: value });
      }, 500);
    }
  };

  // Reset to defaults
  const resetToDefaults = async () => {
    if (!window.confirm('Reset all settings to recommended defaults?')) return;
    const defaultSymbols = proConfig.symbols.length > 0 ? proConfig.symbols : [
      'BTC/USD', 'ETH/USD', 'SOL/USD', 'XRP/USD', 'DOGE/USD',
      'ADA/USD', 'AVAX/USD', 'DOT/USD', 'LINK/USD', 'ATOM/USD'
    ];
    const resetConfig = { ...DEFAULT_CONFIG, symbols: defaultSymbols };
    setProConfig(resetConfig);
    setSelectedSymbols(defaultSymbols);
    try {
      await fetch(`${API_BASE}/api/pro/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(resetConfig)
      });
      toast.success('Settings reset to defaults');
    } catch (error) {
      toast.error('Failed to save default settings');
    }
  };

  // Toggle symbol
  const toggleSymbol = (symbol) => {
    const newSymbols = selectedSymbols.includes(symbol)
      ? selectedSymbols.filter(s => s !== symbol)
      : [...selectedSymbols, symbol];
    setSelectedSymbols(newSymbols);
    saveConfig({ symbols: newSymbols.map(s => `${s}/USD`) });
  };

  // Start/Stop bot
  const startBot = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/pro/start?mode=paper`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'started' || data.status === 'already_running') {
        setBotRunning(true);
        toast.success('Paper trading started!');
        onBotStatusChange?.();
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to start bot');
      }
    } catch (error) {
      toast.error('Error starting bot');
    }
    setLoading(false);
  };

  const stopBot = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/pro/stop`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'stopped' || data.status === 'not_running') {
        setBotRunning(false);
        toast.success('Bot stopped');
        onBotStatusChange?.();
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to stop');
      }
    } catch (error) {
      toast.error('Error stopping bot');
    }
    setLoading(false);
  };

  // Emergency stop - immediately halt and close all positions
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);
  const [emergencyLoading, setEmergencyLoading] = useState(false);

  const emergencyStop = async (closePositions = true) => {
    setEmergencyLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/pro/emergency-stop?close_positions=${closePositions}`,
        { method: 'POST' }
      );
      const data = await response.json();

      setBotRunning(false);
      setShowEmergencyConfirm(false);

      if (data.positions_closed > 0) {
        toast.success(`Emergency stop: Closed ${data.positions_closed} positions`);
      } else {
        toast.success('Emergency stop executed');
      }

      if (data.close_errors?.length > 0) {
        toast.error(`Failed to close some positions: ${data.close_errors.join(', ')}`);
      }

      onBotStatusChange?.();
    } catch (error) {
      toast.error('Emergency stop failed - check console');
      console.error('Emergency stop error:', error);
    }
    setEmergencyLoading(false);
  };

  const filteredSymbols = availableSymbols.filter(s =>
    s.toLowerCase().includes(symbolSearch.toLowerCase())
  );

  return (
    <div className="space-y-4">
      {/* ===== HEADER CONTROL BAR ===== */}
      <div className={`card p-4 ${botRunning ? 'border-2 border-success' : ''}`}>
        <div className="flex flex-col lg:flex-row lg:items-center gap-4">
          {/* Bot Status & Control */}
          <div className="flex items-center gap-4">
            <button
              onClick={botRunning ? stopBot : startBot}
              disabled={loading}
              className={`btn btn-lg min-w-[140px] ${botRunning ? 'btn-danger' : 'btn-success'}`}
            >
              {loading ? <div className="spinner w-5 h-5" /> : botRunning ? '⏹ Stop' : '▶ Start'}
            </button>
            {/* Emergency Stop Button - only show when bot is running */}
            {botRunning && (
              <button
                onClick={() => setShowEmergencyConfirm(true)}
                disabled={emergencyLoading}
                className="btn btn-lg bg-red-700 hover:bg-red-800 text-white border-2 border-red-500 min-w-[160px]"
                title="Emergency stop - immediately halt trading and close all positions"
              >
                {emergencyLoading ? <div className="spinner w-5 h-5" /> : '🚨 EMERGENCY'}
              </button>
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className={`w-3 h-3 rounded-full ${botRunning ? 'bg-success animate-pulse' : 'bg-gray-500'}`}></span>
                <span className="font-semibold">{botRunning ? 'Trading Active' : 'Stopped'}</span>
                {proConfig.mode === 'live' && (
                  <span className="badge badge-danger text-xs">LIVE</span>
                )}
              </div>
              <p className="text-sm text-muted">
                {selectedSymbols.length} symbols • {proConfig.use_rl_agent ? 'RL' : ''}{proConfig.use_rl_agent && proConfig.use_edge_strategies ? '+' : ''}{proConfig.use_edge_strategies ? 'Edge' : ''} strategy
              </p>
            </div>
          </div>

          {/* Metrics Bar */}
          <div className="flex-1 grid grid-cols-5 gap-2 lg:gap-4">
            <div className="text-center p-2 rounded-lg bg-[var(--bg-tertiary)]">
              <p className="text-xs text-muted">Equity</p>
              <p className="font-bold">${botStats.equity?.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[var(--bg-tertiary)]">
              <p className="text-xs text-muted">P&L</p>
              <p className={`font-bold ${botStats.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                ${botStats.total_pnl?.toFixed(2)}
              </p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[var(--bg-tertiary)]">
              <p className="text-xs text-muted">Win Rate</p>
              <p className="font-bold">{botStats.win_rate?.toFixed(1)}%</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[var(--bg-tertiary)]">
              <p className="text-xs text-muted">Trades</p>
              <p className="font-bold">{botStats.total_trades}</p>
            </div>
            <div className="text-center p-2 rounded-lg bg-[var(--bg-tertiary)]">
              <p className="text-xs text-muted">Positions</p>
              <p className="font-bold">{positions.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* ===== OPEN POSITIONS ===== */}
      {positions.length > 0 && (
        <Section title="Open Positions" icon="📈" badge={positions.length} defaultOpen={true}>
          <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted text-left border-b border-[var(--border-color)]">
                  <th className="pb-2 pr-4">Symbol</th>
                  <th className="pb-2 pr-4">Side</th>
                  <th className="pb-2 pr-4">Entry</th>
                  <th className="pb-2 pr-4">Current</th>
                  <th className="pb-2 pr-4">P&L</th>
                  <th className="pb-2">Source</th>
                </tr>
              </thead>
              <tbody>
                {positions.map((pos, idx) => (
                  <tr key={idx} className="border-b border-[var(--border-color)]">
                    <td className="py-2 pr-4 font-semibold">{pos.symbol}</td>
                    <td className={`pr-4 ${pos.side === 'long' ? 'text-success' : 'text-danger'}`}>
                      {pos.side?.toUpperCase()}
                    </td>
                    <td className="pr-4">${pos.entry_price?.toFixed(2)}</td>
                    <td className="pr-4">${pos.current_price?.toFixed(2)}</td>
                    <td className={`pr-4 font-medium ${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      ${pos.unrealized_pnl?.toFixed(2)}
                    </td>
                    <td className="text-muted text-xs">{pos.signal_source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {/* ===== MAIN CONTENT: 2-COLUMN LAYOUT ===== */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* LEFT COLUMN: SETTINGS */}
        <div className="space-y-4">
          {/* Trading Mode */}
          <Section title="Trading Mode" icon="🎯" defaultOpen={false}>
            <div className="flex gap-2">
              {['paper', 'live'].map(mode => (
                <button
                  key={mode}
                  onClick={() => updateConfig('mode', mode, true)}
                  className={`flex-1 px-4 py-3 rounded-lg font-medium transition-all ${
                    proConfig.mode === mode
                      ? mode === 'live' ? 'bg-danger text-white' : 'bg-success text-white'
                      : 'bg-[var(--bg-tertiary)] text-muted hover:bg-[var(--bg-secondary)]'
                  }`}
                >
                  {mode === 'paper' ? '📝 Paper' : '💰 Live'}
                </button>
              ))}
            </div>
            {proConfig.mode === 'live' && (
              <p className="mt-2 text-danger text-sm">⚠️ Live trading uses real funds!</p>
            )}
          </Section>

          {/* Capital & Position Sizing */}
          <Section title="Capital & Position Sizing" icon="💰" defaultOpen={false}>
            <div className="space-y-3">
              <div>
                <label className="input-label">Initial Capital ($)</label>
                <DelayedNumberInput
                  value={proConfig.initial_capital}
                  onChange={(val) => updateConfig('initial_capital', val)}
                  className="input"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="input-label">Position Size (%)</label>
                  <DelayedNumberInput
                    step="1"
                    value={proConfig.max_position_pct}
                    multiplier={100}
                    decimals={0}
                    onChange={(val) => updateConfig('max_position_pct', val)}
                    className="input"
                  />
                  <p className="text-xs text-muted mt-1">${(proConfig.initial_capital * proConfig.max_position_pct).toFixed(0)}/trade</p>
                </div>
                <div>
                  <label className="input-label">Max Positions</label>
                  <DelayedNumberInput
                    value={proConfig.max_positions}
                    onChange={(val) => updateConfig('max_positions', Math.round(val))}
                    className="input"
                  />
                </div>
              </div>
            </div>
          </Section>

          {/* Risk Management */}
          <Section title="Risk Management" icon="🛡️" defaultOpen={false}>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="input-label">Stop Loss (%)</label>
                  <DelayedNumberInput
                    step="0.1"
                    value={proConfig.stop_loss_pct}
                    multiplier={100}
                    decimals={1}
                    onChange={(val) => updateConfig('stop_loss_pct', val)}
                    className="input"
                  />
                </div>
                <div>
                  <label className="input-label">Take Profit (%)</label>
                  <DelayedNumberInput
                    step="0.1"
                    value={proConfig.take_profit_pct}
                    multiplier={100}
                    decimals={1}
                    onChange={(val) => updateConfig('take_profit_pct', val)}
                    className="input"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="input-label">Max Daily Loss (%)</label>
                  <DelayedNumberInput
                    step="0.1"
                    value={proConfig.max_daily_loss_pct}
                    multiplier={100}
                    decimals={1}
                    onChange={(val) => updateConfig('max_daily_loss_pct', val)}
                    className="input"
                  />
                </div>
                <div>
                  <label className="input-label">Max Drawdown (%)</label>
                  <DelayedNumberInput
                    step="0.1"
                    value={proConfig.max_drawdown_pct}
                    multiplier={100}
                    decimals={1}
                    onChange={(val) => updateConfig('max_drawdown_pct', val)}
                    className="input"
                  />
                </div>
              </div>

              {/* Circuit Breaker */}
              <div className="pt-3 border-t border-[var(--border-color)]">
                <p className="text-sm font-medium mb-2">⚡ Circuit Breaker</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="input-label text-xs">Losses to Trigger</label>
                    <DelayedNumberInput
                      step="1"
                      min="1"
                      max="10"
                      value={proConfig.circuit_breaker_losses || 3}
                      onChange={(val) => updateConfig('circuit_breaker_losses', Math.max(1, Math.round(val)))}
                      className="input"
                    />
                  </div>
                  <div>
                    <label className="input-label text-xs">Cooldown (min)</label>
                    <DelayedNumberInput
                      step="5"
                      min="5"
                      max="480"
                      value={proConfig.circuit_breaker_cooldown_minutes || 30}
                      onChange={(val) => updateConfig('circuit_breaker_cooldown_minutes', Math.max(5, Math.round(val)))}
                      className="input"
                    />
                  </div>
                </div>
              </div>
            </div>
          </Section>

          {/* Signal Confidence */}
          <Section title="Signal Confidence" icon="🎚️" defaultOpen={false}>
            <div>
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
              <p className="text-xs text-muted mt-2">
                Lower = more trades (riskier) • Higher = fewer trades (safer)
              </p>
            </div>
          </Section>

          {/* Auto-Disable Poor Performers */}
          <Section title="Auto-Disable Poor Performers" icon="🚫" defaultOpen={false}>
            <div className="space-y-4">
              {/* Enable Toggle */}
              <ToggleSwitch
                checked={proConfig.auto_disable_symbols || false}
                onChange={(val) => updateConfig('auto_disable_symbols', val, true)}
                label="Enable Auto-Disable"
                description="Automatically disable symbols with low win rates"
              />

              {/* Settings (only shown when enabled) */}
              {proConfig.auto_disable_symbols && (
                <div className="space-y-3 pt-2 border-t border-[var(--border-color)]">
                  <div>
                    <label className="input-label">Min Win Rate Threshold</label>
                    <div className="flex items-center gap-3">
                      <input
                        type="range"
                        min="0.2"
                        max="0.5"
                        step="0.05"
                        value={proConfig.min_win_rate_threshold || 0.35}
                        onChange={(e) => updateConfig('min_win_rate_threshold', parseFloat(e.target.value), true)}
                        className="flex-1 h-2 bg-[var(--bg-tertiary)] rounded-lg appearance-none cursor-pointer"
                      />
                      <span className="font-bold w-12 text-center">
                        {((proConfig.min_win_rate_threshold || 0.35) * 100).toFixed(0)}%
                      </span>
                    </div>
                    <p className="text-xs text-muted mt-1">Symbols below this win rate will be disabled</p>
                  </div>

                  <div>
                    <label className="input-label">Min Trades for Evaluation</label>
                    <DelayedNumberInput
                      step="1"
                      min="3"
                      max="20"
                      value={proConfig.min_trades_for_evaluation || 5}
                      onChange={(val) => updateConfig('min_trades_for_evaluation', Math.max(3, Math.round(val)))}
                      className="input"
                    />
                    <p className="text-xs text-muted mt-1">Symbols need this many trades before being evaluated</p>
                  </div>

                  {/* Evaluate & Apply Buttons */}
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={evaluateSymbols}
                      disabled={evaluating}
                      className="flex-1 btn btn-sm"
                    >
                      {evaluating ? (
                        <><span className="spinner w-4 h-4 mr-1"></span> Evaluating...</>
                      ) : (
                        '🔍 Evaluate'
                      )}
                    </button>
                    <button
                      onClick={applyAutoDisable}
                      disabled={evaluating || !evaluationResult?.poor_performers?.length}
                      className="flex-1 btn btn-sm btn-danger"
                    >
                      🚫 Apply
                    </button>
                  </div>

                  {/* Evaluation Results */}
                  {evaluationResult && evaluationResult.poor_performers?.length > 0 && (
                    <div className="mt-3 p-3 rounded-lg bg-danger/10 border border-danger/30">
                      <p className="text-sm font-medium text-danger mb-2">
                        {evaluationResult.poor_performers.length} symbols below {evaluationResult.threshold}:
                      </p>
                      <div className="flex flex-wrap gap-1">
                        {evaluationResult.poor_performers.slice(0, 10).map(s => (
                          <span key={s.symbol} className="px-2 py-0.5 bg-danger/20 text-danger text-xs rounded">
                            {s.symbol.replace('/USD', '')} ({s.win_rate}%)
                          </span>
                        ))}
                        {evaluationResult.poor_performers.length > 10 && (
                          <span className="text-xs text-muted">+{evaluationResult.poor_performers.length - 10} more</span>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Currently Disabled */}
                  {proConfig.disabled_symbols?.length > 0 && (
                    <div className="mt-2 p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className="text-xs font-medium mb-2">Disabled ({proConfig.disabled_symbols.length}):</p>
                      <div className="flex flex-wrap gap-1">
                        {proConfig.disabled_symbols.slice(0, 8).map(s => (
                          <button
                            key={s}
                            onClick={() => toggleSymbolEnabled(s, true)}
                            className="px-2 py-0.5 bg-gray-600 text-gray-300 text-xs rounded hover:bg-gray-500"
                            title="Click to re-enable"
                          >
                            {s.replace('/USD', '')} ✕
                          </button>
                        ))}
                        {proConfig.disabled_symbols.length > 8 && (
                          <span className="text-xs text-muted">+{proConfig.disabled_symbols.length - 8} more</span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </Section>

          {/* Reset Button */}
          <button
            onClick={resetToDefaults}
            className="w-full btn bg-warning/20 text-warning hover:bg-warning/30"
          >
            🔄 Reset All to Defaults
          </button>
        </div>

        {/* RIGHT COLUMN: SYMBOLS & STRATEGIES */}
        <div className="space-y-4">
          {/* Symbols */}
          <Section title="Trading Symbols" icon="📊" badge={selectedSymbols.length} defaultOpen={true}>
            {/* Search & Quick Actions */}
            <div className="space-y-3 mb-3">
              <input
                type="text"
                placeholder="Search symbols..."
                value={symbolSearch}
                onChange={(e) => setSymbolSearch(e.target.value)}
                className="input"
              />
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => {
                    setSelectedSymbols(availableSymbols.slice(0, 10));
                    saveConfig({ symbols: availableSymbols.slice(0, 10).map(s => `${s}/USD`) });
                  }}
                  className="btn btn-sm"
                >
                  Top 10
                </button>
                <button
                  onClick={() => {
                    setSelectedSymbols(availableSymbols.slice(0, 25));
                    saveConfig({ symbols: availableSymbols.slice(0, 25).map(s => `${s}/USD`) });
                  }}
                  className="btn btn-sm"
                >
                  Top 25
                </button>
                <button
                  onClick={() => {
                    setSelectedSymbols(availableSymbols);
                    saveConfig({ symbols: availableSymbols.map(s => `${s}/USD`) });
                  }}
                  className="btn btn-sm"
                >
                  All
                </button>
                <button
                  onClick={() => {
                    setSelectedSymbols([]);
                    saveConfig({ symbols: [] });
                  }}
                  className="btn btn-sm btn-danger"
                >
                  Clear
                </button>
              </div>
            </div>

            {/* Symbol Grid */}
            <div className="grid grid-cols-5 gap-1.5 max-h-[200px] overflow-y-auto">
              {filteredSymbols.map(symbol => (
                <button
                  key={symbol}
                  onClick={() => toggleSymbol(symbol)}
                  className={`px-2 py-1.5 rounded text-xs font-medium transition-all ${
                    selectedSymbols.includes(symbol)
                      ? 'bg-info text-white'
                      : 'bg-[var(--bg-tertiary)] text-muted hover:bg-[var(--bg-secondary)]'
                  }`}
                >
                  {symbol}
                </button>
              ))}
            </div>
          </Section>

          {/* Strategies */}
          <Section title="Strategy Components" icon="🧠" defaultOpen={true}>
            <div className="space-y-2">
              <ToggleSwitch
                checked={proConfig.use_rl_agent}
                onChange={(val) => updateConfig('use_rl_agent', val, true)}
                label="🤖 RL Agent (PPO)"
                description="Neural network trained on market data"
              />
              <ToggleSwitch
                checked={proConfig.use_edge_strategies}
                onChange={(val) => updateConfig('use_edge_strategies', val, true)}
                label="📈 Edge Strategies"
                description="Funding, sentiment, order flow, liquidations"
              />
              <ToggleSwitch
                checked={proConfig.use_alternative_data}
                onChange={(val) => updateConfig('use_alternative_data', val, true)}
                label="📊 Alternative Data"
                description="Social sentiment, on-chain, whale activity"
              />
            </div>
          </Section>

          {/* Edge Strategies Info */}
          <Section title="Available Edge Strategies" icon="📋" defaultOpen={false}>
            <div className="grid grid-cols-2 gap-2">
              <div className="p-2 rounded bg-[var(--bg-tertiary)]">
                <p className="text-xs font-medium text-info">💰 Funding Rate</p>
                <p className="text-xs text-muted">Trade extreme rates</p>
              </div>
              <div className="p-2 rounded bg-[var(--bg-tertiary)]">
                <p className="text-xs font-medium text-warning">😨 Sentiment</p>
                <p className="text-xs text-muted">Fear/greed extremes</p>
              </div>
              <div className="p-2 rounded bg-[var(--bg-tertiary)]">
                <p className="text-xs font-medium text-success">📊 Order Flow</p>
                <p className="text-xs text-muted">Buy/sell imbalance</p>
              </div>
              <div className="p-2 rounded bg-[var(--bg-tertiary)]">
                <p className="text-xs font-medium text-danger">💥 Liquidations</p>
                <p className="text-xs text-muted">Cascade movements</p>
              </div>
            </div>
          </Section>

          {/* Strategy Performance */}
          {learningData?.top_strategies?.length > 0 && (
            <Section title="Strategy Performance (24h)" icon="🏆" defaultOpen={false}>
              <div className="space-y-2">
                {learningData.top_strategies.slice(0, 4).map((strat, idx) => (
                  <div key={strat.name} className="flex items-center justify-between p-2 rounded bg-[var(--bg-tertiary)]">
                    <div className="flex items-center gap-2">
                      {idx === 0 && <span>🥇</span>}
                      {idx === 1 && <span>🥈</span>}
                      {idx === 2 && <span>🥉</span>}
                      <span className="text-sm font-medium">{strat.name}</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm">
                      <span>{(strat.win_rate * 100).toFixed(0)}% win</span>
                      <span className={strat.total_pnl >= 0 ? 'text-success' : 'text-danger'}>
                        ${strat.total_pnl?.toFixed(0)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}
        </div>
      </div>

      {/* Info Card - Only when stopped */}
      {!botRunning && (
        <div className="card p-4 bg-[var(--bg-secondary)]">
          <div className="flex items-start gap-3">
            <span className="text-xl">💡</span>
            <div className="text-sm text-muted">
              <strong className="text-[var(--text-color)]">Ready to trade:</strong> Configure your settings above, select symbols, then click Start to begin paper trading. Go to the <strong>Training</strong> tab to train the AI model first.
            </div>
          </div>
        </div>
      )}

      {/* Emergency Stop Confirmation Modal */}
      {showEmergencyConfirm && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
          <div className="card p-6 max-w-md mx-4 border-2 border-red-500">
            <div className="text-center mb-6">
              <span className="text-5xl">🚨</span>
              <h2 className="text-xl font-bold mt-3 text-red-500">EMERGENCY STOP</h2>
              <p className="text-muted mt-2">
                This will immediately halt all trading activity and close all open positions.
              </p>
            </div>

            <div className="space-y-3">
              <button
                onClick={() => emergencyStop(true)}
                disabled={emergencyLoading}
                className="w-full btn bg-red-700 hover:bg-red-800 text-white py-3"
              >
                {emergencyLoading ? 'Stopping...' : 'STOP & CLOSE ALL POSITIONS'}
              </button>

              <button
                onClick={() => emergencyStop(false)}
                disabled={emergencyLoading}
                className="w-full btn bg-orange-600 hover:bg-orange-700 text-white py-3"
              >
                {emergencyLoading ? 'Stopping...' : 'STOP (Keep Positions Open)'}
              </button>

              <button
                onClick={() => setShowEmergencyConfirm(false)}
                disabled={emergencyLoading}
                className="w-full btn btn-secondary py-3"
              >
                Cancel
              </button>
            </div>

            <p className="text-xs text-muted text-center mt-4">
              ⚠️ In live mode, positions will be market-sold at current prices
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
