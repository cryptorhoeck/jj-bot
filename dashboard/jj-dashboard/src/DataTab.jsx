import React, { useState, useEffect, useMemo } from 'react';
import toast from 'react-hot-toast';
import { ConfirmModal } from './components';

// Simple bar chart component
function BarChart({ data, valueKey, labelKey, colorFn, height = 120 }) {
  if (!data || data.length === 0) return null;
  const maxVal = Math.max(...data.map(d => Math.abs(d[valueKey] || 0)), 1);

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((item, idx) => {
        const val = item[valueKey] || 0;
        const barHeight = Math.abs(val) / maxVal * (height - 20);
        const color = colorFn ? colorFn(val, item) : (val >= 0 ? 'var(--color-success)' : 'var(--color-danger)');

        return (
          <div key={idx} className="flex-1 flex flex-col items-center justify-end">
            <div
              className="w-full rounded-t transition-all hover:opacity-80"
              style={{
                height: barHeight,
                backgroundColor: color,
                minHeight: 2
              }}
              title={`${item[labelKey]}: $${val.toFixed(2)}`}
            />
            <span className="text-[9px] text-muted mt-1 truncate w-full text-center">
              {item[labelKey]?.slice(0, 3) || idx}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// Simple line chart for equity curve
function EquityChart({ data, height = 150 }) {
  if (!data || data.length < 2) return null;

  const values = data.map(d => d.equity);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal || 1;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * 100;
    const y = 100 - ((d.equity - minVal) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  const startEquity = data[0]?.equity || 0;
  const endEquity = data[data.length - 1]?.equity || 0;
  const isPositive = endEquity >= startEquity;

  return (
    <div style={{ height }} className="relative">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={isPositive ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'} stopOpacity="0.3" />
            <stop offset="100%" stopColor={isPositive ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'} stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon
          points={`0,100 ${points} 100,100`}
          fill="url(#equityGradient)"
        />
        <polyline
          points={points}
          fill="none"
          stroke={isPositive ? 'rgb(34, 197, 94)' : 'rgb(239, 68, 68)'}
          strokeWidth="0.5"
        />
      </svg>
      <div className="absolute top-1 left-2 text-xs text-muted">${maxVal.toLocaleString()}</div>
      <div className="absolute bottom-1 left-2 text-xs text-muted">${minVal.toLocaleString()}</div>
    </div>
  );
}

// Histogram component
function Histogram({ bins, counts, height = 100 }) {
  if (!bins || !counts || counts.length === 0) return null;
  const maxCount = Math.max(...counts, 1);

  return (
    <div className="flex items-end gap-px" style={{ height }}>
      {counts.map((count, idx) => {
        const barHeight = (count / maxCount) * (height - 10);
        const binStart = bins[idx];
        const binEnd = bins[idx + 1];
        const isPositive = (binStart + binEnd) / 2 >= 0;

        return (
          <div
            key={idx}
            className="flex-1 rounded-t transition-all hover:opacity-80"
            style={{
              height: barHeight,
              backgroundColor: isPositive ? 'var(--color-success)' : 'var(--color-danger)',
              minHeight: count > 0 ? 2 : 0
            }}
            title={`$${binStart?.toFixed(0)} to $${binEnd?.toFixed(0)}: ${count} trades`}
          />
        );
      })}
    </div>
  );
}

export function DataTab({ darkMode, API_BASE, trades, summary }) {
  const [viewMode, setViewMode] = useState('trades');
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [trainingConfirmOpen, setTrainingConfirmOpen] = useState(false);
  const [resetAllConfirmOpen, setResetAllConfirmOpen] = useState(false);

  // Backup management state
  const [backups, setBackups] = useState([]);
  const [backupSummary, setBackupSummary] = useState({ trading: 0, state: 0, model: 0, total_size: 0 });
  const [loadingBackups, setLoadingBackups] = useState(false);
  const [restoreConfirmOpen, setRestoreConfirmOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState(null);
  const [creatingBackup, setCreatingBackup] = useState(false);
  const [showBackupList, setShowBackupList] = useState(false);

  // Analytics state
  const [analyticsData, setAnalyticsData] = useState(null);
  const [analyticsPeriod, setAnalyticsPeriod] = useState('all');
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  // Model versions state
  const [modelVersions, setModelVersions] = useState([]);
  const [activeModel, setActiveModel] = useState(null);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelStats, setModelStats] = useState([]);

  // Load backups on mount
  useEffect(() => {
    loadBackups();
  }, []);

  // Load analytics when switching to analytics view or period changes
  useEffect(() => {
    if (viewMode === 'analytics') {
      loadAnalytics();
    }
  }, [viewMode, analyticsPeriod]);

  // Load model versions when switching to models view
  useEffect(() => {
    if (viewMode === 'models') {
      loadModelVersions();
    }
  }, [viewMode]);

  const loadBackups = async () => {
    setLoadingBackups(true);
    try {
      const response = await fetch(`${API_BASE}/api/data/backups`);
      const data = await response.json();
      if (data.status === 'success') {
        setBackups(data.backups || []);
        setBackupSummary(data.summary || { trading: 0, state: 0, model: 0, total_size: 0 });
      }
    } catch (error) {
      console.error('Error loading backups:', error);
    }
    setLoadingBackups(false);
  };

  const loadAnalytics = async () => {
    setLoadingAnalytics(true);
    try {
      const response = await fetch(`${API_BASE}/api/analytics/enhanced/comprehensive?period=${analyticsPeriod}`);
      const data = await response.json();
      if (data.success) {
        setAnalyticsData(data);
      }
    } catch (error) {
      console.error('Error loading analytics:', error);
    }
    setLoadingAnalytics(false);
  };

  const loadModelVersions = async () => {
    setLoadingModels(true);
    try {
      // Fetch model versions, active model, and performance by model
      const [versionsRes, activeRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/api/analytics/enhanced/model-versions?limit=50`),
        fetch(`${API_BASE}/api/analytics/enhanced/model-versions/active`),
        fetch(`${API_BASE}/api/analytics/enhanced/trades-by-model?limit=20`)
      ]);

      const versionsData = await versionsRes.json();
      const activeData = await activeRes.json();
      const statsData = await statsRes.json();

      if (versionsData.success) {
        setModelVersions(versionsData.data?.versions || []);
      }
      if (activeData.success) {
        setActiveModel(activeData.data);
      }
      if (statsData.success) {
        setModelStats(statsData.data?.models || []);
      }
    } catch (error) {
      console.error('Error loading model versions:', error);
    }
    setLoadingModels(false);
  };

  const createBackup = async () => {
    setCreatingBackup(true);
    try {
      const response = await fetch(`${API_BASE}/api/data/backup`, { method: 'POST' });
      const data = await response.json();
      if (data.status === 'success') {
        toast.success(data.message);
        loadBackups();
        setShowBackupList(true);
      } else {
        toast.error(data.message || 'Backup failed');
      }
    } catch (error) {
      toast.error('Error creating backup');
    }
    setCreatingBackup(false);
  };

  const handleRestoreConfirm = async () => {
    if (!selectedBackup) return;
    try {
      const response = await fetch(`${API_BASE}/api/data/restore`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: selectedBackup.filename })
      });
      const data = await response.json();
      if (data.status === 'success') {
        toast.success(data.message);
        loadBackups();
      } else {
        toast.error(data.message || 'Restore failed');
      }
    } catch (error) {
      toast.error('Error restoring backup');
    }
    setSelectedBackup(null);
  };

  const handleDeleteConfirm = async () => {
    if (!selectedBackup) return;
    try {
      const response = await fetch(`${API_BASE}/api/data/backup/${selectedBackup.filename}`, {
        method: 'DELETE'
      });
      const data = await response.json();
      if (data.status === 'success') {
        toast.success(data.message);
        loadBackups();
      } else {
        toast.error(data.message || 'Delete failed');
      }
    } catch (error) {
      toast.error('Error deleting backup');
    }
    setSelectedBackup(null);
  };

  const getBackupTypeIcon = (type) => {
    switch (type) {
      case 'trading': return '📊';
      case 'state': return '🧠';
      case 'model': return '🤖';
      default: return '📁';
    }
  };

  const getBackupTypeLabel = (type) => {
    switch (type) {
      case 'trading': return 'Trade History';
      case 'state': return 'Bot State & IQ';
      case 'model': return 'AI Model';
      default: return 'Unknown';
    }
  };

  const getBackupTypeBadgeClass = (type) => {
    switch (type) {
      case 'trading': return 'badge-info';
      case 'state': return 'badge-warning';
      case 'model': return 'badge-success';
      default: return 'badge-secondary';
    }
  };

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
      toast.success('CSV exported successfully!');
    } catch (error) {
      toast.error('Export failed');
    }
  };

  const handleClearDatabaseConfirm = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/clear`, { method: 'POST' });
      const data = await response.json();
      toast.success(data.message || 'Trading data cleared!');
      window.location.reload();
    } catch (error) {
      toast.error('Error clearing database');
    }
  };

  const handleClearTrainingConfirm = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/clear-training`, { method: 'POST' });
      const data = await response.json();
      toast.success(data.message || 'Training data cleared!');
      window.location.reload();
    } catch (error) {
      toast.error('Error clearing training data');
    }
  };

  const handleResetAllConfirm = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/reset-all`, { method: 'POST' });
      const data = await response.json();

      // Clear all localStorage data related to JJ-Bot
      localStorage.removeItem('jjbot_last_training_session');
      localStorage.removeItem('jjbot_currency');
      localStorage.removeItem('marketFavorites');

      toast.success(data.message || 'All data reset!');
      window.location.reload();
    } catch (error) {
      toast.error('Error resetting all data');
    }
  };

  const archiveData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/archive`, { method: 'POST' });
      const data = await response.json();
      toast.success(data.message || 'Data archived!');
      loadBackups();
    } catch (error) {
      toast.error('Archive failed');
    }
  };

  // Shorthand for analytics data
  const a = analyticsData;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h1 className="text-2xl font-bold">Data & Analytics</h1>
        <div className="nav-tabs">
          <button
            onClick={() => setViewMode('trades')}
            className={`nav-tab ${viewMode === 'trades' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <span>Trades</span>
          </button>
          <button
            onClick={() => setViewMode('analytics')}
            className={`nav-tab ${viewMode === 'analytics' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Analytics</span>
          </button>
          <button
            onClick={() => setViewMode('models')}
            className={`nav-tab ${viewMode === 'models' ? 'active' : ''}`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span>Models</span>
          </button>
        </div>
      </div>

      {/* Trades View */}
      {viewMode === 'trades' && (
        <>
          {/* Data Management */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
              </svg>
              Data Management
            </h3>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
              <button onClick={exportCSV} className="btn btn-primary btn-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export CSV
              </button>
              <button onClick={createBackup} disabled={creatingBackup} className="btn btn-success btn-sm">
                {creatingBackup ? (
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                  </svg>
                )}
                Create Backup
              </button>
              <button onClick={archiveData} className="btn btn-secondary btn-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Archive
              </button>
              <button
                onClick={() => setShowBackupList(!showBackupList)}
                className={`btn btn-sm ${showBackupList ? 'btn-info' : 'btn-secondary'}`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                Restore ({backups.length})
              </button>
              <button onClick={() => setConfirmModalOpen(true)} className="btn btn-danger btn-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Clear Trades
              </button>
              <button onClick={() => setTrainingConfirmOpen(true)} className="btn btn-warning btn-sm">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Reset AI
              </button>
              <button onClick={() => setResetAllConfirmOpen(true)} className="btn btn-sm" style={{ backgroundColor: '#dc2626', color: 'white' }}>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Reset All
              </button>
            </div>

            {/* Stats Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-[var(--bg-tertiary)] text-center">
                <p className="text-2xl font-bold">{summary.total_trades || 0}</p>
                <p className="text-xs text-muted">Total Trades</p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-tertiary)] text-center">
                <p className={`text-2xl font-bold ${(summary.total_pnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                  ${summary.total_pnl?.toFixed(2) || '0.00'}
                </p>
                <p className="text-xs text-muted">Total P&L</p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-tertiary)] text-center">
                <p className="text-2xl font-bold">{summary.win_rate?.toFixed(1) || '0'}%</p>
                <p className="text-xs text-muted">Win Rate</p>
              </div>
              <div className="p-4 rounded-xl bg-[var(--bg-tertiary)] text-center">
                <p className="text-2xl font-bold text-info">{backups.length}</p>
                <p className="text-xs text-muted">Backups Available</p>
              </div>
            </div>
          </div>

          {/* Backup List */}
          {showBackupList && (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Available Backups</h3>
                <button onClick={() => setShowBackupList(false)} className="btn btn-secondary btn-sm">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {backups.length > 0 ? (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {backups.map((backup, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{getBackupTypeIcon(backup.type)}</span>
                        <div>
                          <p className="font-medium text-sm">{backup.filename}</p>
                          <p className="text-xs text-muted">{backup.size_formatted}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`badge ${getBackupTypeBadgeClass(backup.type)} text-xs`}>
                          {getBackupTypeLabel(backup.type)}
                        </span>
                        <button
                          onClick={() => { setSelectedBackup(backup); setRestoreConfirmOpen(true); }}
                          className="btn btn-success btn-sm"
                        >
                          Restore
                        </button>
                        <button
                          onClick={() => { setSelectedBackup(backup); setDeleteConfirmOpen(true); }}
                          className="btn btn-danger btn-sm"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted py-4">No backups found</p>
              )}
            </div>
          )}

          {/* Trade History Table */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">Trade History</h3>
            {trades && trades.length > 0 ? (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Time</th>
                      <th>Symbol</th>
                      <th>Signal</th>
                      <th className="text-right">Price</th>
                      <th className="text-right">P&L</th>
                      <th>Strategy</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trades.map((trade, idx) => (
                      <tr key={idx}>
                        <td className="text-muted text-sm">{new Date(trade.timestamp).toLocaleString()}</td>
                        <td className="font-semibold">{trade.symbol}</td>
                        <td>
                          <span className={`badge ${trade.signal === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                            {trade.signal}
                          </span>
                        </td>
                        <td className="text-right">${parseFloat(trade.last_price).toFixed(2)}</td>
                        <td className={`text-right font-semibold ${trade.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                          {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                        </td>
                        <td className="text-muted text-sm">{trade.strategy || 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-center text-muted py-8">No trades yet. Start trading to see history.</p>
            )}
          </div>
        </>
      )}

      {/* Analytics View */}
      {viewMode === 'analytics' && (
        <>
          {/* Period Selector */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {['all', '24h', '7d', '30d', '90d'].map(period => (
                <button
                  key={period}
                  onClick={() => setAnalyticsPeriod(period)}
                  className={`btn btn-sm ${analyticsPeriod === period ? 'btn-info' : 'btn-secondary'}`}
                >
                  {period === 'all' ? 'All Time' : period.toUpperCase()}
                </button>
              ))}
            </div>
            <button onClick={loadAnalytics} disabled={loadingAnalytics} className="btn btn-secondary btn-sm">
              {loadingAnalytics ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {loadingAnalytics && !analyticsData && (
            <div className="card p-12 text-center">
              <div className="spinner w-8 h-8 mx-auto mb-4"></div>
              <p className="text-muted">Loading analytics...</p>
            </div>
          )}

          {analyticsData && (
            <>
              {/* Overview Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <div className="card p-4 text-center">
                  <p className={`text-2xl font-bold ${(a.overview?.total_pnl || 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                    ${a.overview?.total_pnl?.toLocaleString() || '0'}
                  </p>
                  <p className="text-xs text-muted">Total P&L</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xl font-bold">{a.overview?.win_rate?.toFixed(1) || 0}%</p>
                  <p className="text-xs text-muted">Win Rate</p>
                </div>
                <div className="card p-4 text-center">
                  <p className={`text-2xl font-bold ${(a.overview?.profit_factor || 0) >= 1 ? 'text-success' : 'text-danger'}`}>
                    {a.overview?.profit_factor?.toFixed(2) || '0'}
                  </p>
                  <p className="text-xs text-muted">Profit Factor</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xl font-bold">{a.overview?.total_trades || 0}</p>
                  <p className="text-xs text-muted">Total Trades</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xl font-bold text-success">{a.overview?.winning_trades || 0}</p>
                  <p className="text-xs text-muted">Wins</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-2xl font-bold text-danger">{a.overview?.losing_trades || 0}</p>
                  <p className="text-xs text-muted">Losses</p>
                </div>
              </div>

              {/* Equity Curve & Risk Metrics */}
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Equity Curve</h3>
                  {a.equity_curve && a.equity_curve.length > 1 ? (
                    <EquityChart data={a.equity_curve} height={180} />
                  ) : (
                    <p className="text-center text-muted py-8">Need more trades for equity curve</p>
                  )}
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Risk Metrics</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className={`text-xl font-bold ${(a.risk_metrics?.sharpe_ratio || 0) >= 1 ? 'text-success' : 'text-warning'}`}>
                        {a.risk_metrics?.sharpe_ratio?.toFixed(2) || '0'}
                      </p>
                      <p className="text-xs text-muted">Sharpe Ratio</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className={`text-xl font-bold ${(a.risk_metrics?.sortino_ratio || 0) >= 1.5 ? 'text-success' : 'text-warning'}`}>
                        {a.risk_metrics?.sortino_ratio?.toFixed(2) || '0'}
                      </p>
                      <p className="text-xs text-muted">Sortino Ratio</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className="text-xl font-bold text-danger">
                        {a.risk_metrics?.max_drawdown_pct?.toFixed(1) || '0'}%
                      </p>
                      <p className="text-xs text-muted">Max Drawdown</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className={`text-xl font-bold ${(a.risk_metrics?.calmar_ratio || 0) >= 1 ? 'text-success' : 'text-warning'}`}>
                        {a.risk_metrics?.calmar_ratio?.toFixed(2) || '0'}
                      </p>
                      <p className="text-xs text-muted">Calmar Ratio</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* P&L Distribution */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold mb-4">P&L Distribution</h3>
                <div className="grid lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    {a.pnl_distribution?.counts?.length > 0 ? (
                      <Histogram bins={a.pnl_distribution.bins} counts={a.pnl_distribution.counts} height={120} />
                    ) : (
                      <p className="text-center text-muted py-8">No distribution data</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Best Trade</span>
                      <span className="text-success font-semibold">${a.overview?.best_trade?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Worst Trade</span>
                      <span className="text-danger font-semibold">${a.overview?.worst_trade?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Avg Win</span>
                      <span className="text-success font-semibold">${a.overview?.avg_win?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Avg Loss</span>
                      <span className="text-danger font-semibold">${a.overview?.avg_loss?.toFixed(2) || 0}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-muted">Expectancy</span>
                      <span className="font-semibold">${a.overview?.expectancy?.toFixed(2) || 0}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Time Analysis */}
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Performance by Hour</h3>
                  {a.time_of_day?.length > 0 ? (
                    <BarChart
                      data={a.time_of_day}
                      valueKey="total_pnl"
                      labelKey="label"
                      height={120}
                    />
                  ) : (
                    <p className="text-center text-muted py-8">No hourly data</p>
                  )}
                </div>

                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Performance by Day</h3>
                  {a.day_of_week?.length > 0 ? (
                    <BarChart
                      data={a.day_of_week}
                      valueKey="total_pnl"
                      labelKey="short_label"
                      height={120}
                    />
                  ) : (
                    <p className="text-center text-muted py-8">No daily data</p>
                  )}
                </div>
              </div>

              {/* Symbol Performance */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold mb-4">Symbol Performance</h3>
                {a.symbols?.length > 0 ? (
                  <div className="table-container">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Symbol</th>
                          <th className="text-center">Trades</th>
                          <th className="text-center">Win Rate</th>
                          <th className="text-right">Total P&L</th>
                          <th className="text-right">Avg P&L</th>
                          <th className="text-right">Best</th>
                          <th className="text-right">Worst</th>
                        </tr>
                      </thead>
                      <tbody>
                        {a.symbols.map((s, idx) => (
                          <tr key={idx}>
                            <td className="font-semibold">{s.symbol}</td>
                            <td className="text-center">{s.trades}</td>
                            <td className="text-center">
                              <span className={s.win_rate >= 50 ? 'text-success' : 'text-danger'}>
                                {s.win_rate}%
                              </span>
                            </td>
                            <td className={`text-right font-semibold ${s.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                              ${s.total_pnl}
                            </td>
                            <td className={`text-right ${s.avg_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                              ${s.avg_pnl}
                            </td>
                            <td className="text-right text-success">${s.best_trade}</td>
                            <td className="text-right text-danger">${s.worst_trade}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-center text-muted py-8">No symbol data</p>
                )}
              </div>

              {/* Strategy Performance */}
              <div className="card p-6">
                <h3 className="text-lg font-semibold mb-4">Strategy Performance</h3>
                {a.strategies?.length > 0 ? (
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {a.strategies.map((s, idx) => (
                      <div key={idx} className={`p-4 rounded-xl ${s.total_pnl >= 0 ? 'bg-success/10 border border-success/30' : 'bg-danger/10 border border-danger/30'}`}>
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-semibold">{s.strategy}</p>
                          {idx === 0 && <span className="badge badge-success text-xs">Top</span>}
                        </div>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <span className="text-muted">Trades:</span>
                            <span className="ml-1 font-medium">{s.trades}</span>
                          </div>
                          <div>
                            <span className="text-muted">Win Rate:</span>
                            <span className="ml-1 font-medium">{s.win_rate}%</span>
                          </div>
                          <div>
                            <span className="text-muted">P&L:</span>
                            <span className={`ml-1 font-medium ${s.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                              ${s.total_pnl}
                            </span>
                          </div>
                          <div>
                            <span className="text-muted">PF:</span>
                            <span className={`ml-1 font-medium ${s.profit_factor >= 1 ? 'text-success' : 'text-danger'}`}>
                              {s.profit_factor}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-center text-muted py-8">No strategy data</p>
                )}
              </div>

              {/* Streaks & Monthly */}
              <div className="grid lg:grid-cols-2 gap-6">
                {/* Streaks */}
                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Trading Streaks</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className={`text-2xl font-bold ${a.streaks?.current_streak >= 0 ? 'text-success' : 'text-danger'}`}>
                        {a.streaks?.current_streak > 0 ? '+' : ''}{a.streaks?.current_streak || 0}
                      </p>
                      <p className="text-xs text-muted">Current Streak</p>
                    </div>
                    <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-2xl font-bold text-success">{a.streaks?.longest_win_streak || 0}</p>
                      <p className="text-xs text-muted">Best Win Streak</p>
                    </div>
                    <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-2xl font-bold text-danger">{a.streaks?.longest_loss_streak || 0}</p>
                      <p className="text-xs text-muted">Worst Loss Streak</p>
                    </div>
                    <div className="p-4 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-2xl font-bold">{a.risk_metrics?.volatility?.toFixed(2) || 0}</p>
                      <p className="text-xs text-muted">Volatility</p>
                    </div>
                  </div>
                </div>

                {/* Monthly Performance */}
                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">Monthly Performance</h3>
                  {a.monthly?.length > 0 ? (
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {a.monthly.map((m, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded bg-[var(--bg-tertiary)]">
                          <span className="font-medium">{m.month}</span>
                          <div className="flex items-center gap-4 text-sm">
                            <span className="text-muted">{m.trades} trades</span>
                            <span className="text-muted">{m.win_rate}%</span>
                            <span className={`font-semibold ${m.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                              ${m.total_pnl}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-muted py-8">No monthly data</p>
                  )}
                </div>
              </div>

              {/* Best & Worst Trades */}
              <div className="grid lg:grid-cols-2 gap-6">
                <div className="card card-success p-6">
                  <h3 className="text-lg font-semibold mb-4 text-success">Best Trades</h3>
                  {a.best_trades?.length > 0 ? (
                    <div className="space-y-2">
                      {a.best_trades.slice(0, 5).map((t, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded bg-success/10">
                          <div>
                            <span className="font-semibold">{t.symbol}</span>
                            <span className="text-xs text-muted ml-2">{t.signal}</span>
                          </div>
                          <span className="text-success font-bold">+${t.pnl}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-muted py-4">No trades</p>
                  )}
                </div>

                <div className="card card-danger p-6">
                  <h3 className="text-lg font-semibold mb-4 text-danger">Worst Trades</h3>
                  {a.worst_trades?.length > 0 ? (
                    <div className="space-y-2">
                      {a.worst_trades.slice(0, 5).map((t, idx) => (
                        <div key={idx} className="flex items-center justify-between p-2 rounded bg-danger/10">
                          <div>
                            <span className="font-semibold">{t.symbol}</span>
                            <span className="text-xs text-muted ml-2">{t.signal}</span>
                          </div>
                          <span className="text-danger font-bold">${t.pnl}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-center text-muted py-4">No trades</p>
                  )}
                </div>
              </div>

              {/* AI Performance */}
              {a.ai_performance && a.ai_performance.trading_iq > 0 && (
                <div className="card p-6">
                  <h3 className="text-lg font-semibold mb-4">AI Training Performance</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                    <div className="p-3 rounded-lg bg-purple-500/10 border border-purple-500/30 text-center">
                      <p className="text-2xl font-bold text-purple-400">{a.ai_performance.trading_iq}</p>
                      <p className="text-xs text-muted">Trading IQ</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-lg font-bold">{a.ai_performance.expertise_level}</p>
                      <p className="text-xs text-muted">Expertise</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-lg font-bold">{a.ai_performance.training_sessions}</p>
                      <p className="text-xs text-muted">Sessions</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-lg font-bold">{a.ai_performance.total_training_episodes?.toLocaleString()}</p>
                      <p className="text-xs text-muted">Episodes</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-lg font-bold">{a.ai_performance.avg_win_rate?.toFixed(1)}%</p>
                      <p className="text-xs text-muted">Avg Win Rate</p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                      <p className="text-lg font-bold">{a.ai_performance.avg_profit_factor?.toFixed(2)}</p>
                      <p className="text-xs text-muted">Avg PF</p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}

          {!analyticsData && !loadingAnalytics && (
            <div className="card p-12 text-center">
              <p className="text-muted">No analytics data available. Start trading to generate analytics.</p>
            </div>
          )}
        </>
      )}

      {/* Models View */}
      {viewMode === 'models' && (
        <>
          {/* Header with Refresh */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">🤖</span>
              <div>
                <h2 className="text-lg font-semibold">AI Model Versions</h2>
                <p className="text-sm text-muted">Track and compare different model versions</p>
              </div>
            </div>
            <button onClick={loadModelVersions} disabled={loadingModels} className="btn btn-secondary btn-sm">
              {loadingModels ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {loadingModels && modelVersions.length === 0 && (
            <div className="card p-12 text-center">
              <div className="spinner w-8 h-8 mx-auto mb-4"></div>
              <p className="text-muted">Loading model versions...</p>
            </div>
          )}

          {/* Active Model Card */}
          {activeModel && (
            <div className="card card-success p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <span className="text-success">●</span>
                  Active Model
                </h3>
                <span className="badge badge-success">Currently In Use</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
                <div className="p-3 rounded-lg bg-success/10 text-center">
                  <p className="text-lg font-mono font-bold text-success">{activeModel.version}</p>
                  <p className="text-xs text-muted">Version</p>
                </div>
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                  <p className="text-xl font-bold text-purple-400">{activeModel.final_iq || 0}</p>
                  <p className="text-xs text-muted">Trading IQ</p>
                </div>
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                  <p className="text-xl font-bold">{activeModel.final_win_rate?.toFixed(1) || 0}%</p>
                  <p className="text-xs text-muted">Win Rate</p>
                </div>
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                  <p className={`text-xl font-bold ${(activeModel.final_profit_factor || 0) >= 1 ? 'text-success' : 'text-danger'}`}>
                    {activeModel.final_profit_factor?.toFixed(2) || '0.00'}
                  </p>
                  <p className="text-xs text-muted">Profit Factor</p>
                </div>
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                  <p className="text-xl font-bold">{activeModel.training_episodes?.toLocaleString() || 0}</p>
                  <p className="text-xs text-muted">Episodes</p>
                </div>
                <div className="p-3 rounded-lg bg-[var(--bg-tertiary)] text-center">
                  <p className="text-sm font-medium">
                    {activeModel.created_at ? new Date(activeModel.created_at).toLocaleDateString() : 'N/A'}
                  </p>
                  <p className="text-xs text-muted">Created</p>
                </div>
              </div>
              {activeModel.notes && (
                <p className="mt-4 text-sm text-muted">{activeModel.notes}</p>
              )}
            </div>
          )}

          {/* Model Performance Comparison */}
          {modelStats.length > 0 && (
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Performance by Model Version</h3>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>Model Version</th>
                      <th className="text-center">Trades</th>
                      <th className="text-center">Wins</th>
                      <th className="text-center">Losses</th>
                      <th className="text-center">Win Rate</th>
                      <th className="text-right">Total P&L</th>
                      <th className="text-right">Avg P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {modelStats.map((stat, idx) => (
                      <tr key={idx}>
                        <td className="font-mono font-semibold">
                          {stat.model_version === activeModel?.version && (
                            <span className="text-success mr-2">●</span>
                          )}
                          {stat.model_version}
                        </td>
                        <td className="text-center">{stat.trade_count}</td>
                        <td className="text-center text-success">{stat.wins}</td>
                        <td className="text-center text-danger">{stat.losses}</td>
                        <td className="text-center">
                          <span className={stat.win_rate >= 50 ? 'text-success' : 'text-danger'}>
                            {stat.win_rate}%
                          </span>
                        </td>
                        <td className={`text-right font-semibold ${stat.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                          ${stat.total_pnl?.toFixed(2)}
                        </td>
                        <td className={`text-right ${stat.avg_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                          ${stat.avg_pnl?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* All Model Versions */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4">All Model Versions ({modelVersions.length})</h3>
            {modelVersions.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {modelVersions.map((model, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border ${
                      model.is_active
                        ? 'bg-success/5 border-success/30'
                        : 'bg-[var(--bg-tertiary)] border-[var(--border-color)]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-mono font-bold text-sm">{model.version}</span>
                      {model.is_active && <span className="badge badge-success text-xs">Active</span>}
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted">IQ:</span>
                        <span className="ml-1 font-medium text-purple-400">{model.final_iq || 0}</span>
                      </div>
                      <div>
                        <span className="text-muted">Win Rate:</span>
                        <span className="ml-1 font-medium">{model.final_win_rate?.toFixed(1) || 0}%</span>
                      </div>
                      <div>
                        <span className="text-muted">PF:</span>
                        <span className={`ml-1 font-medium ${(model.final_profit_factor || 0) >= 1 ? 'text-success' : 'text-danger'}`}>
                          {model.final_profit_factor?.toFixed(2) || '0.00'}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted">Episodes:</span>
                        <span className="ml-1 font-medium">{model.training_episodes?.toLocaleString() || 0}</span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-[var(--border-color)]">
                      <p className="text-xs text-muted">
                        Created: {model.created_at ? new Date(model.created_at).toLocaleString() : 'N/A'}
                      </p>
                      {model.notes && (
                        <p className="text-xs text-muted mt-1 truncate" title={model.notes}>
                          {model.notes}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">🤖</div>
                <p className="text-lg font-semibold mb-2">No Model Versions Yet</p>
                <p className="text-muted">
                  Model versions are created automatically when training completes.
                  <br />
                  Start a training session to create your first model version!
                </p>
              </div>
            )}
          </div>

          {/* Info Card */}
          <div className="card p-6 bg-info/5 border-info/30">
            <h4 className="font-semibold mb-2 flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              About Model Versioning
            </h4>
            <p className="text-sm text-muted">
              Each time training completes, a new model version is automatically created and backed up.
              Model versions track the AI's performance at each training checkpoint, including Trading IQ,
              win rate, profit factor, and training episode count. This allows you to compare how
              your AI improves over time and track which model version made each trade.
            </p>
          </div>
        </>
      )}

      {/* Confirm Modals */}
      <ConfirmModal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        onConfirm={handleClearDatabaseConfirm}
        title="Clear Trading Data"
        message="This will clear all trade history. A backup will be created. Training IQ will be preserved."
        confirmText="Clear"
        confirmVariant="danger"
        darkMode={darkMode}
      />

      <ConfirmModal
        isOpen={trainingConfirmOpen}
        onClose={() => setTrainingConfirmOpen(false)}
        onConfirm={handleClearTrainingConfirm}
        title="Reset AI Training"
        message="This will reset the AI to untrained state. A backup will be created."
        confirmText="Reset"
        confirmVariant="danger"
        darkMode={darkMode}
      />

      <ConfirmModal
        isOpen={resetAllConfirmOpen}
        onClose={() => setResetAllConfirmOpen(false)}
        onConfirm={handleResetAllConfirm}
        title="Reset ALL Data"
        message="This will clear ALL data: trades, training, AI model, and browser cache. A backup will be created. This cannot be undone."
        confirmText="Reset Everything"
        confirmVariant="danger"
        darkMode={darkMode}
      />

      <ConfirmModal
        isOpen={restoreConfirmOpen}
        onClose={() => { setRestoreConfirmOpen(false); setSelectedBackup(null); }}
        onConfirm={handleRestoreConfirm}
        title="Restore Backup"
        message={`Restore from ${selectedBackup?.filename}? A safety backup will be created first.`}
        confirmText="Restore"
        confirmVariant="warning"
        darkMode={darkMode}
      />

      <ConfirmModal
        isOpen={deleteConfirmOpen}
        onClose={() => { setDeleteConfirmOpen(false); setSelectedBackup(null); }}
        onConfirm={handleDeleteConfirm}
        title="Delete Backup"
        message={`Permanently delete ${selectedBackup?.filename}?`}
        confirmText="Delete"
        confirmVariant="danger"
        darkMode={darkMode}
      />
    </div>
  );
}
