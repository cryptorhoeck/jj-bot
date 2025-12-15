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
  { value: '5m', label: '5 min', minutes: 5 },
  { value: '15m', label: '15 min', minutes: 15 },
  { value: '1h', label: '1 hour', minutes: 60 },
  { value: '4h', label: '4 hours', minutes: 240 },
  { value: '1d', label: '1 day', minutes: 1440 },
];

// Available history periods
const HISTORY_OPTIONS = [
  { value: 30, label: '30 days' },
  { value: 90, label: '90 days' },
  { value: 180, label: '180 days' },
  { value: 365, label: '1 year' },
];

// Calculate estimated candles based on timeframe and history
const calculateCandles = (timeframe, historyDays) => {
  const tf = TIMEFRAME_OPTIONS.find(t => t.value === timeframe);
  const minutes = tf?.minutes || 60;
  return Math.floor((historyDays * 24 * 60) / minutes);
};

export function TrainingTab({
  API_BASE,
  sharedBotStatus,
  onBotStatusChange,
  selectedSymbols = [],
  setSelectedSymbols,
  availableSymbols = []
}) {
  const [isTraining, setIsTraining] = useState(false);
  const [loading, setLoading] = useState(false);
  const [symbolSearch, setSymbolSearch] = useState('');

  // Training settings
  const [trainSettings, setTrainSettings] = useState({
    episodes: 1000,
    timeframe: '1h',
    history_days: 90
  });

  // Training progress from bot
  const [trainingProgress, setTrainingProgress] = useState(null);

  // Last session metrics - now fetched from server (no localStorage caching)
  const [lastSessionMetrics, setLastSessionMetrics] = useState(null);

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
    avg_profit_factor: 0,
    avg_reward: 0,
    best_win_rate: 0,
    best_profit_factor: 0
  });

  // Training time tracking - use milliseconds for precision
  const [trainingStartTime, setTrainingStartTime] = useState(null);
  const [elapsedMs, setElapsedMs] = useState(0);

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
        // Always update training history from response (keeps it fresh)
        if (data.training_history) {
          setTrainingHistory(data.training_history);
        }
        if (!data.training?.is_training && isTraining) {
          // Training just finished - save final metrics
          if (trainingProgress) {
            setLastSessionMetrics({
              ...trainingProgress,
              session_date: new Date().toISOString(),
              final_elapsed_ms: elapsedMs
            });
          }
          // Fetch one more time to get final updated stats
          const finalResponse = await fetch(`${API_BASE}/api/pro/status`);
          const finalData = await finalResponse.json();
          if (finalData.training_history) {
            setTrainingHistory(finalData.training_history);
          }
          if (finalData.trading_iq) {
            setTradingIQ({
              iq: finalData.trading_iq,
              level: finalData.expertise_level || 'Untrained'
            });
          }
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

  // Track elapsed time during training (millisecond precision)
  useEffect(() => {
    if (isTraining && !trainingStartTime) {
      setTrainingStartTime(Date.now());
    }
    if (!isTraining) {
      setTrainingStartTime(null);
      setElapsedMs(0);
    }
  }, [isTraining, trainingStartTime]);

  useEffect(() => {
    if (!isTraining || !trainingStartTime) return;

    const timer = setInterval(() => {
      setElapsedMs(Date.now() - trainingStartTime);
    }, 100); // Update every 100ms for smoother display

    return () => clearInterval(timer);
  }, [isTraining, trainingStartTime]);

  // Format elapsed time as HH:MM:SS
  const formatTime = (ms) => {
    const totalSeconds = Math.floor(ms / 1000);
    const hrs = Math.floor(totalSeconds / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format time per episode (handles sub-second values)
  const formatTimePerEpisode = (ms, episodes) => {
    if (!episodes || episodes === 0) return '0ms';
    const msPerEpisode = ms / episodes;
    if (msPerEpisode < 1000) {
      return `${Math.round(msPerEpisode)}ms`;
    }
    return `${(msPerEpisode / 1000).toFixed(1)}s`;
  };

  // Estimate remaining time
  const estimateRemainingTime = () => {
    if (!isTraining || !elapsedMs || !currentEpisode) return null;
    const episodesRemaining = totalEpisodes - currentEpisode;
    const msPerEpisode = elapsedMs / currentEpisode;
    const remainingMs = Math.floor(episodesRemaining * msPerEpisode);
    return formatTime(remainingMs);
  };

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

  // Unified metrics source - use live data if training, otherwise last session
  const metrics = isTraining && trainingProgress ? trainingProgress : lastSessionMetrics;
  const metricsElapsedMs = isTraining ? elapsedMs : (lastSessionMetrics?.final_elapsed_ms || 0);
  const metricsCurrentEpisode = isTraining ? currentEpisode : (lastSessionMetrics?.current_episode || lastSessionMetrics?.total_episodes || 0);
  const metricsTotalEpisodes = isTraining ? totalEpisodes : (lastSessionMetrics?.total_episodes || 0);
  const hasMetrics = !!metrics;

  // Compute profit factor from available data as fallback
  const computedProfitFactor = (() => {
    if (metrics?.avg_profit_factor && metrics.avg_profit_factor > 0) {
      return metrics.avg_profit_factor;
    }
    // Try to compute from gross profit/loss if available
    if (metrics?.gross_profit && metrics?.gross_loss && metrics.gross_loss > 0) {
      return metrics.gross_profit / metrics.gross_loss;
    }
    // Compute from wins/losses and average amounts
    // Only compute if we have actual average amounts (not fake fallbacks)
    const avgWin = metrics?.avg_win_amount;
    const avgLoss = metrics?.avg_loss_amount;
    if (!avgWin || !avgLoss) return null;

    const totalWins = metrics?.total_wins || Math.round((metrics?.total_trades || 0) * (metrics?.avg_win_rate || 50) / 100);
    const totalLosses = metrics?.total_losses || Math.round((metrics?.total_trades || 0) * (1 - (metrics?.avg_win_rate || 50) / 100));
    if (totalLosses > 0 && totalWins > 0) {
      const grossProfit = totalWins * avgWin;
      const grossLoss = totalLosses * avgLoss;
      if (grossLoss > 0) {
        return grossProfit / grossLoss;
      }
    }
    return null;
  })();

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
          <div className="flex items-center justify-between mb-2">
            <p className="text-sm text-muted uppercase">Training History</p>
            {isTraining && (
              <span className="badge badge-info text-xs">Live Session</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-2xl font-bold">
                {isTraining
                  ? <>{trainingHistory.training_sessions || 0} <span className="text-info text-sm">+1</span></>
                  : trainingHistory.training_sessions}
              </p>
              <p className="text-xs text-muted">Sessions</p>
            </div>
            <div>
              <p className="text-2xl font-bold">
                {isTraining && trainingProgress?.current_episode
                  ? ((trainingHistory.total_training_episodes || 0) + currentEpisode).toLocaleString()
                  : trainingHistory.total_training_episodes?.toLocaleString() || 0}
              </p>
              <p className="text-xs text-muted">Total Episodes</p>
            </div>
            <div>
              <p className="text-2xl font-bold">
                {isTraining && trainingProgress?.avg_win_rate
                  ? trainingProgress.avg_win_rate.toFixed(1)
                  : trainingHistory.avg_win_rate?.toFixed(1) || 0}%
              </p>
              <p className="text-xs text-muted">{isTraining ? 'Current' : 'Avg'} Win Rate</p>
            </div>
            <div>
              <p className={`text-2xl font-bold ${isTraining && computedProfitFactor && computedProfitFactor >= 1 ? 'text-success' : isTraining && computedProfitFactor ? 'text-danger' : ''}`}>
                {isTraining
                  ? (computedProfitFactor ? computedProfitFactor.toFixed(2) : '—')
                  : trainingHistory.avg_profit_factor?.toFixed(2) || '—'}
              </p>
              <p className="text-xs text-muted">{isTraining ? 'Current' : 'Avg'} Profit Factor</p>
            </div>
          </div>
          {!isTraining && trainingHistory.last_training_date && (
            <p className="text-xs text-muted mt-3 text-center border-t border-[var(--border-color)] pt-2">
              Last trained: {new Date(trainingHistory.last_training_date).toLocaleDateString()}
            </p>
          )}
          {isTraining && (
            <p className="text-xs text-info mt-3 text-center border-t border-[var(--border-color)] pt-2">
              Training in progress...
            </p>
          )}
        </div>
      </div>

      {/* Additional Training Stats - shown when we have history */}
      {(trainingHistory.training_sessions > 0 || trainingHistory.total_training_trades > 0) && (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">📈 Training Performance</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">{trainingHistory.total_training_trades?.toLocaleString() || 0}</p>
              <p className="text-xs text-muted">Total Training Trades</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold">{trainingHistory.avg_reward?.toFixed(2) || 0}</p>
              <p className="text-xs text-muted">Avg Reward</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold text-success">{trainingHistory.best_win_rate?.toFixed(1) || 0}%</p>
              <p className="text-xs text-muted">Best Win Rate</p>
            </div>
            <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
              <p className="text-2xl font-bold text-success">{trainingHistory.best_profit_factor?.toFixed(2) || 0}</p>
              <p className="text-xs text-muted">Best Profit Factor</p>
            </div>
          </div>
        </div>
      )}

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

      {/* Training Metrics - Live or Last Session */}
      {hasMetrics && (
        <>
          {/* Main Metrics Card */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-semibold">
                  📊 {isTraining ? 'Live Training Metrics' : 'Last Session Metrics'}
                </h3>
                {!isTraining && lastSessionMetrics?.session_date && (
                  <span className="badge badge-warning text-xs">
                    {new Date(lastSessionMetrics.session_date).toLocaleDateString()} {new Date(lastSessionMetrics.session_date).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                  </span>
                )}
                {isTraining && (
                  <span className="badge badge-success text-xs animate-pulse">LIVE</span>
                )}
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted">
                  ⏱️ {isTraining ? 'Elapsed' : 'Duration'}: <span className="font-mono text-info">{formatTime(metricsElapsedMs)}</span>
                </span>
                {isTraining && estimateRemainingTime() && (
                  <span className="text-muted">
                    ⏳ Remaining: <span className="font-mono text-warning">{estimateRemainingTime()}</span>
                  </span>
                )}
              </div>
            </div>

            {/* Primary Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className="text-2xl font-bold">{metrics.last_win_rate?.toFixed(1) || 0}%</p>
                <p className="text-xs text-muted">{isTraining ? 'Last' : 'Final'} Win Rate</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${(metrics.last_pnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                  ${metrics.last_pnl?.toFixed(2) || '0.00'}
                </p>
                <p className="text-xs text-muted">{isTraining ? 'Last' : 'Final'} Episode P&L</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className="text-2xl font-bold">{(metrics.total_trades || 0).toLocaleString()}</p>
                <p className="text-xs text-muted">Total Trades</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.simulated_equity != null ? (metrics.simulated_equity >= 10000 ? 'text-success' : 'text-danger') : 'text-muted'}`}>
                  {metrics.simulated_equity != null ? `$${metrics.simulated_equity.toLocaleString(undefined, {maximumFractionDigits: 0})}` : '—'}
                </p>
                <p className="text-xs text-muted">{isTraining ? 'Simulated' : 'Final'} Equity</p>
              </div>
            </div>

            {/* Secondary Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
              <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-lg">
                <p className="text-lg font-bold">{metrics.avg_win_rate?.toFixed(1) || 0}%</p>
                <p className="text-xs text-muted">Avg Win Rate</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-lg">
                <p className={`text-lg font-bold ${(metrics.avg_reward || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                  {metrics.avg_reward?.toFixed(2) || 0}
                </p>
                <p className="text-xs text-muted">Avg Reward</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-lg">
                <p className={`text-lg font-bold ${computedProfitFactor && computedProfitFactor >= 1 ? 'text-success' : computedProfitFactor ? 'text-danger' : ''}`}>
                  {computedProfitFactor ? computedProfitFactor.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Profit Factor</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-secondary)] rounded-lg">
                <p className="text-lg font-bold text-info">{formatTimePerEpisode(metricsElapsedMs, metricsCurrentEpisode)}</p>
                <p className="text-xs text-muted">Per Episode</p>
              </div>
            </div>

            {isTraining && metrics.current_symbol && (
              <p className="text-sm text-muted mt-4 text-center">
                Currently training on: <span className="font-medium text-info">{metrics.current_symbol}</span>
              </p>
            )}
            {!isTraining && (
              <p className="text-sm text-muted mt-4 text-center">
                Session completed with <span className="font-medium text-info">{metricsCurrentEpisode.toLocaleString()}</span> episodes
              </p>
            )}
          </div>

          {/* Episode Performance Analytics */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <h3 className="text-lg font-semibold mb-4">🎯 Episode Performance</h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-success">
                  ${metrics.best_episode_pnl != null ? metrics.best_episode_pnl.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Best Episode</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-danger">
                  ${metrics.worst_episode_pnl != null ? metrics.worst_episode_pnl.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Worst Episode</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.best_win_rate != null ? `${metrics.best_win_rate.toFixed(0)}%` : '—'}
                </p>
                <p className="text-xs text-muted">Best Win Rate</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-success">
                  {metrics.win_streak != null ? metrics.win_streak : '—'}
                </p>
                <p className="text-xs text-muted">Win Streak</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-danger">
                  {metrics.loss_streak != null ? metrics.loss_streak : '—'}
                </p>
                <p className="text-xs text-muted">Loss Streak</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metricsCurrentEpisode > 0 ? ((metrics.total_trades || 0) / metricsCurrentEpisode).toFixed(1) : '—'}
                </p>
                <p className="text-xs text-muted">Trades/Episode</p>
              </div>
            </div>
          </div>

          {/* Trade Analytics */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <h3 className="text-lg font-semibold mb-4">📈 Trade Analytics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
              {/* Wins/Losses */}
              <div className="text-center p-3 bg-success/10 rounded-lg border border-success/30">
                <p className="text-lg font-bold text-success">
                  {metrics.total_wins != null ? metrics.total_wins.toLocaleString() : '—'}
                </p>
                <p className="text-xs text-muted">Total Wins</p>
              </div>
              <div className="text-center p-3 bg-danger/10 rounded-lg border border-danger/30">
                <p className="text-lg font-bold text-danger">
                  {metrics.total_losses != null ? metrics.total_losses.toLocaleString() : '—'}
                </p>
                <p className="text-xs text-muted">Total Losses</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-success">
                  ${metrics.avg_win_amount != null ? metrics.avg_win_amount.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Avg Win $</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-danger">
                  ${metrics.avg_loss_amount != null ? metrics.avg_loss_amount.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Avg Loss $</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-success">
                  ${metrics.largest_win != null ? metrics.largest_win.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Largest Win</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold text-danger">
                  ${metrics.largest_loss != null ? metrics.largest_loss.toFixed(0) : '—'}
                </p>
                <p className="text-xs text-muted">Largest Loss</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.long_trades != null ? metrics.long_trades.toLocaleString() : '—'}
                </p>
                <p className="text-xs text-muted">Long Trades</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.short_trades != null ? metrics.short_trades.toLocaleString() : '—'}
                </p>
                <p className="text-xs text-muted">Short Trades</p>
              </div>
            </div>
          </div>

          {/* Risk & Performance Metrics */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <h3 className="text-lg font-semibold mb-4">⚖️ Risk & Performance Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.sharpe_ratio != null ? (metrics.sharpe_ratio >= 1 ? 'text-success' : metrics.sharpe_ratio >= 0 ? 'text-warning' : 'text-danger') : 'text-muted'}`}>
                  {metrics.sharpe_ratio != null ? metrics.sharpe_ratio.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Sharpe Ratio</p>
                <p className="text-[10px] text-muted mt-1">Risk-adj return</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.sortino_ratio != null ? (metrics.sortino_ratio >= 1.5 ? 'text-success' : 'text-warning') : 'text-muted'}`}>
                  {metrics.sortino_ratio != null ? metrics.sortino_ratio.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Sortino Ratio</p>
                <p className="text-[10px] text-muted mt-1">Downside risk</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.max_drawdown != null ? 'text-danger' : 'text-muted'}`}>
                  {metrics.max_drawdown != null ? `${metrics.max_drawdown.toFixed(1)}%` : '—'}
                </p>
                <p className="text-xs text-muted">Max Drawdown</p>
                <p className="text-[10px] text-muted mt-1">Peak to trough</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.calmar_ratio != null ? (metrics.calmar_ratio >= 1 ? 'text-success' : 'text-warning') : 'text-muted'}`}>
                  {metrics.calmar_ratio != null ? metrics.calmar_ratio.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Calmar Ratio</p>
                <p className="text-[10px] text-muted mt-1">Return/Drawdown</p>
              </div>
              <div className="text-center p-4 bg-[var(--bg-tertiary)] rounded-xl">
                <p className={`text-2xl font-bold ${metrics.simulated_equity != null ? ((metrics.simulated_equity - 10000) >= 0 ? 'text-success' : 'text-danger') : 'text-muted'}`}>
                  {metrics.simulated_equity != null ? `${((metrics.simulated_equity - 10000) / 10000 * 100).toFixed(1)}%` : '—'}
                </p>
                <p className="text-xs text-muted">Total Return</p>
                <p className="text-[10px] text-muted mt-1">From $10,000</p>
              </div>
            </div>
          </div>

          {/* Learning Progress */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <h3 className="text-lg font-semibold mb-4">🧠 Learning Progress</h3>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
              <div className="text-center p-3 bg-purple-500/10 rounded-lg border border-purple-500/30">
                <p className={`text-lg font-bold ${metrics.policy_loss != null ? 'text-purple-400' : 'text-muted'}`}>
                  {metrics.policy_loss != null ? metrics.policy_loss.toFixed(3) : '—'}
                </p>
                <p className="text-xs text-muted">Policy Loss</p>
              </div>
              <div className="text-center p-3 bg-blue-500/10 rounded-lg border border-blue-500/30">
                <p className={`text-lg font-bold ${metrics.value_loss != null ? 'text-blue-400' : 'text-muted'}`}>
                  {metrics.value_loss != null ? metrics.value_loss.toFixed(3) : '—'}
                </p>
                <p className="text-xs text-muted">Value Loss</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.entropy != null ? metrics.entropy.toFixed(3) : '—'}
                </p>
                <p className="text-xs text-muted">Entropy</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.learning_rate != null ? metrics.learning_rate.toExponential(1) : '3.0e-4'}
                </p>
                <p className="text-xs text-muted">Learning Rate</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.gradient_norm != null ? metrics.gradient_norm.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Gradient Norm</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.clip_fraction != null ? metrics.clip_fraction.toFixed(2) : '—'}
                </p>
                <p className="text-xs text-muted">Clip Fraction</p>
              </div>
            </div>

            {/* Progress bars for losses - based on actual loss reduction */}
            <div className="mt-4 space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted">Policy Loss Convergence</span>
                  <span className="text-purple-400">
                    {metrics.policy_loss != null
                      ? `${Math.max(0, Math.min(100, (1 - metrics.policy_loss / 0.1) * 100)).toFixed(0)}%`
                      : '—'}
                  </span>
                </div>
                <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-purple-400 transition-all duration-300"
                    style={{ width: `${metrics.policy_loss != null ? Math.max(0, Math.min(100, (1 - metrics.policy_loss / 0.1) * 100)) : 0}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-muted">Value Loss Convergence</span>
                  <span className="text-blue-400">
                    {metrics.value_loss != null
                      ? `${Math.max(0, Math.min(100, (1 - metrics.value_loss / 50.0) * 100)).toFixed(0)}%`
                      : '—'}
                  </span>
                </div>
                <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-blue-400 transition-all duration-300"
                    style={{ width: `${metrics.value_loss != null ? Math.max(0, Math.min(100, (1 - metrics.value_loss / 50.0) * 100)) : 0}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Session Statistics */}
          <div className={`card p-6 ${!isTraining ? 'opacity-90' : ''}`}>
            <h3 className="text-lg font-semibold mb-4">📋 Session Statistics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">{metricsCurrentEpisode.toLocaleString()}</p>
                <p className="text-xs text-muted">{isTraining ? 'Episodes Done' : 'Total Episodes'}</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">{isTraining ? (metricsTotalEpisodes - metricsCurrentEpisode).toLocaleString() : '0'}</p>
                <p className="text-xs text-muted">{isTraining ? 'Episodes Left' : 'Completed'}</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {isTraining
                    ? ((metrics.total_trades || 0) / Math.max(1, metricsCurrentEpisode) * metricsTotalEpisodes).toLocaleString(undefined, {maximumFractionDigits: 0})
                    : (metrics.total_trades || 0).toLocaleString()}
                </p>
                <p className="text-xs text-muted">{isTraining ? 'Est.' : ''} Total Trades</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {(calculateCandles(trainSettings.timeframe, trainSettings.history_days) * metricsCurrentEpisode / 1000).toFixed(1)}K
                </p>
                <p className="text-xs text-muted">Data Points</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.symbols_trained || 1}
                </p>
                <p className="text-xs text-muted">Symbols</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {metrics.model_updates || metricsCurrentEpisode}
                </p>
                <p className="text-xs text-muted">Model Updates</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {(metricsElapsedMs / 1000 / 60).toFixed(1)} min
                </p>
                <p className="text-xs text-muted">{isTraining ? 'Training' : 'Total'} Time</p>
              </div>
              <div className="text-center p-3 bg-[var(--bg-tertiary)] rounded-lg">
                <p className="text-lg font-bold">
                  {(metricsCurrentEpisode / (metricsElapsedMs / 1000 / 60) || 0).toFixed(0)}/min
                </p>
                <p className="text-xs text-muted">Episode Rate</p>
              </div>
            </div>
          </div>
        </>
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

        {/* Symbol Selection */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold">📊 Training Symbols</h4>
            <span className="badge badge-info">{selectedSymbols.length} selected</span>
          </div>
          <p className="text-xs text-muted mb-3">
            Select symbols for training and trading. Changes apply to both tabs.
          </p>

          {/* Symbol Search */}
          <input
            type="text"
            placeholder="Search symbols..."
            value={symbolSearch}
            onChange={(e) => setSymbolSearch(e.target.value)}
            className="input mb-3"
          />

          {/* Quick Select Buttons */}
          <div className="flex flex-wrap gap-2 mb-3">
            <button
              onClick={() => setSelectedSymbols(availableSymbols.slice(0, 10))}
              className="btn btn-ghost btn-sm"
            >
              Top 10
            </button>
            <button
              onClick={() => setSelectedSymbols(availableSymbols.slice(0, 25))}
              className="btn btn-ghost btn-sm"
            >
              Top 25
            </button>
            <button
              onClick={() => setSelectedSymbols([...availableSymbols])}
              className="btn btn-ghost btn-sm"
            >
              All ({availableSymbols.length})
            </button>
            <button
              onClick={() => setSelectedSymbols([])}
              className="btn btn-ghost btn-sm text-danger"
            >
              Clear
            </button>
          </div>

          {/* Symbol Grid */}
          <div className="grid grid-cols-5 md:grid-cols-8 lg:grid-cols-10 gap-2 max-h-48 overflow-y-auto p-2 bg-[var(--bg-secondary)] rounded-lg">
            {availableSymbols
              .filter(s => s.toLowerCase().includes(symbolSearch.toLowerCase()))
              .map(symbol => (
                <button
                  key={symbol}
                  onClick={() => {
                    if (selectedSymbols.includes(symbol)) {
                      setSelectedSymbols(selectedSymbols.filter(s => s !== symbol));
                    } else {
                      setSelectedSymbols([...selectedSymbols, symbol]);
                    }
                  }}
                  className={`px-2 py-1.5 rounded text-xs font-medium transition-colors ${
                    selectedSymbols.includes(symbol)
                      ? 'bg-info text-white'
                      : 'bg-[var(--bg-tertiary)] text-muted hover:text-[var(--text-color)]'
                  }`}
                >
                  {symbol}
                </button>
              ))}
          </div>
        </div>

        {/* Data Info */}
        <div className="mt-6 p-4 rounded-lg bg-[var(--bg-tertiary)]">
          <h4 className="text-sm font-semibold mb-2">📊 Training Data Estimate</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-muted">Candles per symbol</p>
              <p className="font-bold text-info">
                {calculateCandles(trainSettings.timeframe, trainSettings.history_days).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-muted">Total episodes</p>
              <p className="font-bold">{trainSettings.episodes.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-muted">Estimated trades</p>
              <p className="font-bold">{(trainSettings.episodes * 5).toLocaleString()}+</p>
            </div>
            <div>
              <p className="text-muted">Est. training time</p>
              <p className="font-bold">
                {trainSettings.episodes <= 500 ? '~2-5 min' :
                 trainSettings.episodes <= 1000 ? '~5-10 min' :
                 trainSettings.episodes <= 2000 ? '~10-20 min' : '~20+ min'}
              </p>
            </div>
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
