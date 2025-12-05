import React, { useState, useMemo } from 'react';
import toast from 'react-hot-toast';
import { ConfirmModal } from './components';

export function DataTab({ darkMode, API_BASE, trades, summary }) {
  const [confirmModalOpen, setConfirmModalOpen] = useState(false);
  const [trainingConfirmOpen, setTrainingConfirmOpen] = useState(false);
  const [viewMode, setViewMode] = useState('trades');

  const analytics = useMemo(() => {
    if (!trades || trades.length === 0) return null;

    const bySymbol = {};
    trades.forEach(trade => {
      if (!bySymbol[trade.symbol]) {
        bySymbol[trade.symbol] = { trades: 0, wins: 0, losses: 0, totalPnL: 0 };
      }
      bySymbol[trade.symbol].trades++;
      bySymbol[trade.symbol].totalPnL += trade.pnl || 0;
      if (trade.pnl >= 0) bySymbol[trade.symbol].wins++;
      else bySymbol[trade.symbol].losses++;
    });

    const symbolStats = Object.entries(bySymbol).map(([symbol, stats]) => ({
      symbol, ...stats,
      winRate: (stats.wins / stats.trades) * 100,
      avgPnL: stats.totalPnL / stats.trades
    })).sort((a, b) => b.totalPnL - a.totalPnL);

    const byStrategy = {};
    trades.forEach(trade => {
      const strategy = trade.strategy || 'unknown';
      if (!byStrategy[strategy]) {
        byStrategy[strategy] = { trades: 0, wins: 0, losses: 0, totalPnL: 0 };
      }
      byStrategy[strategy].trades++;
      byStrategy[strategy].totalPnL += trade.pnl || 0;
      if (trade.pnl >= 0) byStrategy[strategy].wins++;
      else byStrategy[strategy].losses++;
    });

    const strategyStats = Object.entries(byStrategy).map(([strategy, stats]) => ({
      strategy, ...stats,
      winRate: (stats.wins / stats.trades) * 100,
      avgPnL: stats.totalPnL / stats.trades
    })).sort((a, b) => b.totalPnL - a.totalPnL);

    const sortedByPnL = [...trades].sort((a, b) => b.pnl - a.pnl);
    const bestTrades = sortedByPnL.slice(0, 5);
    const worstTrades = sortedByPnL.slice(-5).reverse();

    return { symbolStats, strategyStats, bestTrades, worstTrades };
  }, [trades]);

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

  const archiveData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/archive`, { method: 'POST' });
      const data = await response.json();
      toast.success(data.message || 'Data archived!');
    } catch (error) {
      toast.error('Archive failed');
    }
  };

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

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
              <button onClick={exportCSV} className="btn btn-primary">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Export CSV
              </button>
              <button onClick={archiveData} className="btn btn-secondary">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Archive
              </button>
              <button onClick={() => setConfirmModalOpen(true)} className="btn btn-danger">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Clear Trading Data
              </button>
              <button onClick={() => setTrainingConfirmOpen(true)} className="btn btn-warning">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Reset Training/IQ
              </button>
            </div>

            {/* Stats Summary */}
            <div className="p-4 rounded-xl bg-[var(--bg-tertiary)]">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Total Trades</p>
                  <p className="text-xl font-bold">{summary.total_trades || 0}</p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Total P&L</p>
                  <p className={`text-xl font-bold ${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                    ${summary.total_pnl?.toFixed(2) || '0.00'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted uppercase tracking-wide">Win Rate</p>
                  <p className="text-xl font-bold">{summary.win_rate?.toFixed(1) || '0'}%</p>
                </div>
              </div>
            </div>
          </div>

          {/* Trade History */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
              Trade History
              <span className="badge badge-info ml-2">{trades.length} trades</span>
            </h3>

            {trades.length > 0 ? (
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
                        <td className="text-right text-muted">${parseFloat(trade.last_price).toFixed(2)}</td>
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
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
                  <svg className="w-8 h-8 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-muted">No trades yet. Start the bot to generate trades.</p>
              </div>
            )}
          </div>
        </>
      )}

      {/* Analytics View */}
      {viewMode === 'analytics' && analytics && (
        <>
          {/* Performance by Symbol */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Performance by Symbol
            </h3>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {analytics.symbolStats.map((stat, idx) => (
                <div key={stat.symbol} className={`stat-card ${stat.totalPnL >= 0 ? 'success' : 'danger'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-lg font-bold">{stat.symbol}</p>
                    {idx === 0 && <span className="badge badge-success">Top</span>}
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted">Trades</span>
                      <span className="font-semibold">{stat.trades}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Win Rate</span>
                      <span className="font-semibold">{stat.winRate.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Total P&L</span>
                      <span className={`font-semibold ${stat.totalPnL >= 0 ? 'text-success' : 'text-danger'}`}>
                        ${stat.totalPnL.toFixed(2)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Avg P&L</span>
                      <span className={`font-semibold ${stat.avgPnL >= 0 ? 'text-success' : 'text-danger'}`}>
                        ${stat.avgPnL.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Performance by Strategy */}
          <div className="card p-6">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Performance by Strategy
            </h3>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {analytics.strategyStats.map((stat, idx) => (
                <div key={stat.strategy} className={`stat-card ${stat.totalPnL >= 0 ? 'success' : 'danger'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-semibold flex items-center gap-2">
                      {idx === 0 && <span className="text-yellow-500">1st</span>}
                      {idx === 1 && <span className="text-gray-400">2nd</span>}
                      {idx === 2 && <span className="text-amber-600">3rd</span>}
                      {stat.strategy}
                    </p>
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted">Trades</span>
                      <span className="font-semibold">{stat.trades}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Win Rate</span>
                      <span className="font-semibold">{stat.winRate.toFixed(1)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted">Total P&L</span>
                      <span className={`font-semibold ${stat.totalPnL >= 0 ? 'text-success' : 'text-danger'}`}>
                        ${stat.totalPnL.toFixed(2)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Best & Worst Trades */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Best Trades */}
            <div className="card card-success p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Best Trades
              </h3>

              <div className="space-y-3">
                {analytics.bestTrades.map((trade, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-success/10">
                    <div>
                      <p className="font-semibold">{trade.symbol} {trade.signal}</p>
                      <p className="text-xs text-muted">{new Date(trade.timestamp).toLocaleString()}</p>
                    </div>
                    <p className="text-lg font-bold text-success">+${trade.pnl.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Worst Trades */}
            <div className="card card-danger p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <svg className="w-5 h-5 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                Worst Trades
              </h3>

              <div className="space-y-3">
                {analytics.worstTrades.map((trade, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-danger/10">
                    <div>
                      <p className="font-semibold">{trade.symbol} {trade.signal}</p>
                      <p className="text-xs text-muted">{new Date(trade.timestamp).toLocaleString()}</p>
                    </div>
                    <p className="text-lg font-bold text-danger">${trade.pnl.toFixed(2)}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}

      {viewMode === 'analytics' && !analytics && (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
            <svg className="w-8 h-8 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="text-muted">No trades yet. Analytics will appear once you have trading data.</p>
        </div>
      )}

      <ConfirmModal
        isOpen={confirmModalOpen}
        onClose={() => setConfirmModalOpen(false)}
        onConfirm={handleClearDatabaseConfirm}
        title="Clear Trading Data"
        message="Are you sure you want to clear all trade history? A backup will be created. Training IQ will be preserved."
        confirmText="Clear Trading Data"
        cancelText="Cancel"
        confirmVariant="danger"
        darkMode={darkMode}
      />

      <ConfirmModal
        isOpen={trainingConfirmOpen}
        onClose={() => setTrainingConfirmOpen(false)}
        onConfirm={handleClearTrainingConfirm}
        title="Reset Training Data"
        message="This will reset the AI to its untrained state, clearing all learned IQ and the trained model. This cannot be undone. A backup will be created."
        confirmText="Reset Training"
        cancelText="Cancel"
        confirmVariant="danger"
        darkMode={darkMode}
      />
    </div>
  );
}
