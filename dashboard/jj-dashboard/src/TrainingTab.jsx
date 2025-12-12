import React, { useState, useEffect, useCallback } from 'react';
import toast from 'react-hot-toast';

// Input component that only saves on blur or Enter
function DelayedNumberInput({ value, onChange, className, step, min, max }) {
  const [localValue, setLocalValue] = useState(value);

  useEffect(() => {
    setLocalValue(value);
  }, [value]);

  const commitValue = () => {
    const parsed = parseFloat(localValue);
    if (!isNaN(parsed)) {
      onChange(parsed);
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
        if (e.key === 'Enter') e.target.blur();
      }}
      className={className}
    />
  );
}

// Available timeframes for training
const TIMEFRAME_OPTIONS = [
  { value: '5m', label: '5 min' },
  { value: '15m', label: '15 min' },
  { value: '1h', label: '1 hour' },
  { value: '4h', label: '4 hours' },
  { value: '1d', label: '1 day' },
];

// Available history periods
const HISTORY_OPTIONS = [
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 180, label: '180 days' },
  { value: 365, label: '1 year' },
];

export function TrainingTab({ API_BASE, sharedBotStatus, onBotStatusChange }) {
  const [isTraining, setIsTraining] = useState(false);
  const [loading, setLoading] = useState(false);

  // Training settings
  const [trainSettings, setTrainSettings] = useState({
    episodes: 1000,
    timeframe: '1h',
    history_days: 90
  });

  // Training progress from bot
  const [trainingProgress, setTrainingProgress] = useState(null);

  // Trading IQ and history
  const [tradingIQ, setTradingIQ] = useState({
    iq: 0,
    level: 'Untrained'
  });
  const [trainingHistory, setTrainingHistory] = useState({
    training_sessions: 0,
    total_training_episodes: 0,
    total_training_trades: 0,
    last_training_date: null,
    avg_win_rate: 0,
    avg_profit_factor: 0
  });

  // Sync with shared status
  useEffect(() => {
    if (sharedBotStatus) {
      setIsTraining(sharedBotStatus.training?.is_training || false);
      if (sharedBotStatus.training) {
        setTrainingProgress(sharedBotStatus.training);
      }
      setTradingIQ({
        iq: sharedBotStatus.trading_iq || 0,
        level: sharedBotStatus.expertise_level || 'Untrained'
      });
      if (sharedBotStatus.training_history) {
        setTrainingHistory(sharedBotStatus.training_history);
      }
    }
  }, [sharedBotStatus]);

  // Load config on mount
  useEffect(() => {
    const loadConfig = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/pro/config`);
        const data = await response.json();
        if (data.config) {
          setTrainSettings({
            episodes: data.config.train_episodes || 1000,
            timeframe: data.config.train_timeframe || '1h',
            history_days: data.config.train_history_days || 90
          });
        }
      } catch (error) {
        console.error('Error loading config:', error);
      }
    };
    loadConfig();
  }, [API_BASE]);

  // Poll for training progress
  useEffect(() => {
    if (!isTraining) return;

    const pollProgress = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/pro/status`);
        const data = await response.json();
        if (data.training) {
          setTrainingProgress(data.training);
          setIsTraining(data.training.is_training);
          if (data.training.trading_iq) {
            setTradingIQ({
              iq: data.training.trading_iq,
              level: data.training.expertise_level || 'Untrained'
            });
          }
        }
        if (!data.training?.is_training && isTraining) {
          // Training just finished
          setIsTraining(false);
          toast.success('Training complete!');
          onBotStatusChange?.();
        }
      } catch (error) {
        console.error('Error polling status:', error);
      }
    };

    const interval = setInterval(pollProgress, 1000);
    return () => clearInterval(interval);
  }, [isTraining, API_BASE, onBotStatusChange]);

  // Save settings to config
  const saveSettings = async (updates) => {
    try {
      const payload = {};
      if (updates.episodes !== undefined) payload.train_episodes = updates.episodes;
      if (updates.timeframe !== undefined) payload.train_timeframe = updates.timeframe;
      if (updates.history_days !== undefined) payload.train_history_days = updates.history_days;

      await fetch(`${API_BASE}/api/pro/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
    } catch (error) {
      console.error('Error saving settings:', error);
    }
  };

  // Start training
  const startTraining = async () => {
    if (sharedBotStatus?.running && !sharedBotStatus?.training?.is_training) {
      toast.error('Stop trading before starting training');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/pro/train?episodes=${trainSettings.episodes}&timeframe=${trainSettings.timeframe}&history_days=${trainSettings.history_days}`,
        { method: 'POST' }
      );
      const data = await response.json();
      if (data.status === 'started') {
        setIsTraining(true);
        toast.success(`Training started for ${trainSettings.episodes} episodes`);
        onBotStatusChange?.();
      } else if (data.status === 'error') {
        toast.error(data.message || 'Failed to start training');
      }
    } catch (error) {
      toast.error('Error starting training');
    }
    setLoading(false);
  };

  // Stop training
  const stopTraining = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/pro/stop`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'stopped') {
        setIsTraining(false);
        toast.success('Training stopped - progress saved');
        onBotStatusChange?.();
      }
    } catch (error) {
      toast.error('Error stopping training');
    }
    setLoading(false);
  };

  // Calculate progress percentage
  const progressPct = trainingProgress?.progress_pct || 0;
  const currentEpisode = trainingProgress?.current_episode || 0;
  const totalEpisodes = trainingProgress?.total_episodes || trainSettings.episodes;

  // Get IQ color based on level
  const getIQColor = (iq) => {
    if (iq >= 140) return 'text-purple-400';
    if (iq >= 120) return 'text-blue-400';
    if (iq >= 100) return 'text-green-400';
    if (iq >= 80) return 'text-yellow-400';
    return 'text-gray-400';
  };

  return (
    <div className="space-y-6">
      {/* Header with IQ Display */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Trading IQ Card */}
        <div className="card p-6 flex-1">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center">
              <span className="text-3xl">🧠</span>
            </div>
            <div>
              <p className="text-sm text-muted uppercase">Trading IQ</p>
              <p className={`text-4xl font-bold ${getIQColor(tradingIQ.iq)}`}>
                {tradingIQ.iq}
              </p>
              <p className="text-sm font-medium">{tradingIQ.level}</p>
            </div>
          </div>
        </div>

        {/* Training Stats Card */}
        <div className="card p-6 flex-1">
          <p className="text-sm text-muted uppercase mb-2">Training History</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-2xl font-bold">{trainingHistory.training_sessions}</p>
              <p className="text-xs text-muted">Sessions</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{trainingHistory.total_training_episodes?.toLocaleString()}</p>
              <p className="text-xs text-muted">Total Episodes</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{trainingHistory.avg_win_rate?.toFixed(1)}%</p>
              <p className="text-xs text-muted">Avg Win Rate</p>
            </div>
            <div>
              <p className="text-2xl font-bold">{trainingHistory.avg_profit_factor?.toFixed(2)}</p>
              <p className="text-xs text-muted">Avg Profit Factor</p>
            </div>
          </div>
        </div>
      </div>

      {/* Training Control */}
      <div className={`card p-6 ${isTraining ? 'border-2 border-info' : ''}`}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center ${isTraining ? 'bg-info/20 animate-pulse' : 'bg-[var(--bg-tertiary)]'}`}>
              <span className="text-3xl">{isTraining ? '🔄' : '🧠'}</span>
            </div>
            <div>
              <h2 className="text-xl font-bold">AI Training</h2>
              <p className="text-sm text-muted">
                {isTraining
                  ? `Episode ${currentEpisode} / ${totalEpisodes}`
                  : 'Train the RL model to improve trading decisions'}
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            {isTraining ? (
              <button
                onClick={stopTraining}
                disabled={loading}
                className="btn btn-lg btn-warning"
              >
                {loading ? <div className="spinner w-5 h-5" /> : '⏹️ Stop Training'}
              </button>
            ) : (
              <button
                onClick={startTraining}
                disabled={loading || (sharedBotStatus?.running && !sharedBotStatus?.training?.is_training)}
                className="btn btn-lg btn-info"
                title={sharedBotStatus?.running ? 'Stop trading first' : 'Start AI training'}
              >
                {loading ? <div className="spinner w-5 h-5" /> : '🧠 Start Training'}
              </button>
            )}
          </div>
        </div>

        {/* Progress Bar */}
        {isTraining && (
          <div className="mt-6">
            <div className="flex justify-between text-sm mb-2">
              <span>Progress</span>
              <span>{progressPct.toFixed(1)}%</span>
            </div>
            <div className="h-4 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Live Training Stats */}
      {isTraining && trainingProgress && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">📊 Live Training Metrics</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">{trainingProgress.last_win_rate?.toFixed(1)}%</p>
              <p className="text-xs text-muted">Last Win Rate</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">${trainingProgress.last_pnl?.toFixed(2)}</p>
              <p className="text-xs text-muted">Last Episode P&L</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">{trainingProgress.total_trades || 0}</p>
              <p className="text-xs text-muted">Total Trades</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">${trainingProgress.simulated_equity?.toLocaleString()}</p>
              <p className="text-xs text-muted">Simulated Equity</p>
            </div>
          </div>

          {trainingProgress.current_symbol && (
            <p className="text-sm text-muted mt-4 text-center">
              Currently training on: <span className="font-medium text-info">{trainingProgress.current_symbol}</span>
            </p>
          )}
        </div>
      )}

      {/* Training Settings */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">⚙️ Training Settings</h3>
        <div className="grid md:grid-cols-3 gap-6">
          {/* Episodes */}
          <div>
            <label className="input-label">Training Episodes</label>
            <DelayedNumberInput
              value={trainSettings.episodes}
              onChange={(val) => {
                const episodes = Math.max(100, Math.round(val));
                setTrainSettings(prev => ({ ...prev, episodes }));
                saveSettings({ episodes });
              }}
              min={100}
              step={100}
              className="input"
            />
            <p className="text-xs text-muted mt-1">More episodes = better learning (1000+ recommended)</p>
          </div>

          {/* Timeframe */}
          <div>
            <label className="input-label">Candle Timeframe</label>
            <select
              value={trainSettings.timeframe}
              onChange={(e) => {
                const timeframe = e.target.value;
                setTrainSettings(prev => ({ ...prev, timeframe }));
                saveSettings({ timeframe });
              }}
              className="input"
            >
              {TIMEFRAME_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted mt-1">Size of candles used for training data</p>
          </div>

          {/* History Days */}
          <div>
            <label className="input-label">Historical Data</label>
            <select
              value={trainSettings.history_days}
              onChange={(e) => {
                const history_days = parseInt(e.target.value);
                setTrainSettings(prev => ({ ...prev, history_days }));
                saveSettings({ history_days });
              }}
              className="input"
            >
              {HISTORY_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted mt-1">How far back to learn from</p>
          </div>
        </div>
      </div>

      {/* How Training Works */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">ℹ️ How Training Works</h3>
        <div className="space-y-3 text-sm text-muted">
          <p>
            <strong className="text-[var(--text-color)]">1. Data Collection:</strong> The AI loads historical price data from your selected symbols.
          </p>
          <p>
            <strong className="text-[var(--text-color)]">2. Episode Training:</strong> Each episode simulates many trades, learning from wins and losses.
          </p>
          <p>
            <strong className="text-[var(--text-color)]">3. Model Improvement:</strong> The RL model updates its neural network to make better decisions.
          </p>
          <p>
            <strong className="text-[var(--text-color)]">4. Trading IQ:</strong> As the model improves, your Trading IQ increases, reflecting learned expertise.
          </p>
          <p className="mt-4 p-3 bg-[var(--bg-tertiary)] rounded-lg">
            💡 <strong>Tip:</strong> Training doesn't affect your real equity. The trained model is saved and used when you start live/paper trading.
          </p>
        </div>
      </div>
    </div>
  );
}
