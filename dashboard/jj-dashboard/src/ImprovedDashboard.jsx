import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// Map internal IQ (0-100) to human IQ scale (70-160)
const mapToHumanIQ = (internalIQ) => {
  // Scale: 0 → 70, 100 → 160
  return Math.round(70 + (internalIQ * 0.9));
};

// Get IQ classification based on human scale
const getIQClassification = (humanIQ) => {
  if (humanIQ < 80) return { label: 'Developing', color: 'text-muted' };
  if (humanIQ < 90) return { label: 'Low Average', color: 'text-muted' };
  if (humanIQ < 100) return { label: 'Average', color: 'text-info' };
  if (humanIQ < 110) return { label: 'Average', color: 'text-info' };
  if (humanIQ < 120) return { label: 'Above Average', color: 'text-success' };
  if (humanIQ < 130) return { label: 'Superior', color: 'text-success' };
  if (humanIQ < 145) return { label: 'Gifted', color: 'text-warning' };
  return { label: 'Genius', color: 'text-danger' };
};

export function DashboardTab({ darkMode, summary, trades, API_BASE, botStatus }) {
  const [equityCurve, setEquityCurve] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [riskStatus, setRiskStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setError(null);

        const equityRes = await fetch(`${API_BASE}/api/equity-curve`);
        if (equityRes.ok) {
          const equityData = await equityRes.json();
          setEquityCurve(equityData.equity_curve || []);
        }

        const positionsRes = await fetch(`${API_BASE}/api/positions/open`);
        if (positionsRes.ok) {
          const positionsData = await positionsRes.json();
          setOpenPositions(positionsData.open_positions || []);
        }

        const riskRes = await fetch(`${API_BASE}/api/risk/status`);
        if (riskRes.ok) {
          const riskData = await riskRes.json();
          setRiskStatus(riskData);
        }

        setLoading(false);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000);
    return () => clearInterval(interval);
  }, [API_BASE]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="stat-card">
              <div className="skeleton h-4 w-20 mb-3" />
              <div className="skeleton h-8 w-24 mb-2" />
              <div className="skeleton h-3 w-16" />
            </div>
          ))}
        </div>
        <div className="card p-6">
          <div className="skeleton h-6 w-40 mb-4" />
          <div className="skeleton h-64 w-full rounded-lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-8 text-center">
        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-danger/10 flex items-center justify-center">
          <svg className="w-8 h-8 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold mb-2">Connection Error</h3>
        <p className="text-muted mb-4">Unable to load dashboard data. The server may be offline.</p>
        <button onClick={() => { setLoading(true); setError(null); }} className="btn btn-primary">
          Retry Connection
        </button>
      </div>
    );
  }

  const recentTrades = trades.slice(0, 5);
  const chartColors = {
    stroke: darkMode ? '#60a5fa' : '#3b82f6',
    fill: darkMode ? 'rgba(96, 165, 250, 0.1)' : 'rgba(59, 130, 246, 0.1)',
    grid: darkMode ? '#334155' : '#e2e8f0',
    text: darkMode ? '#94a3b8' : '#64748b'
  };

  return (
    <div className="space-y-6">
      {/* Performance Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Current Equity */}
        <div className="stat-card">
          <p className="stat-label">Current Equity</p>
          <p className="stat-value text-info">
            ${(summary.current_equity || 10000).toLocaleString()}
          </p>
          <p className={`stat-change ${summary.return_pct >= 0 ? 'positive' : 'negative'}`}>
            {summary.return_pct >= 0 ? '+' : ''}{summary.return_pct?.toFixed(2) || '0.00'}% return
          </p>
        </div>

        {/* Total P&L */}
        <div className={`stat-card ${summary.total_pnl >= 0 ? 'success' : 'danger'}`}>
          <p className="stat-label">Total P&L</p>
          <p className={`stat-value ${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
            {summary.total_pnl >= 0 ? '+' : ''}${summary.total_pnl?.toFixed(2) || '0.00'}
          </p>
          <p className="stat-change text-muted">
            {summary.winning_trades || 0}W / {summary.losing_trades || 0}L
          </p>
        </div>

        {/* Win Rate */}
        <div className="stat-card">
          <p className="stat-label">Win Rate</p>
          <p className="stat-value">{summary.win_rate?.toFixed(1) || '0'}%</p>
          <p className="stat-change text-muted">{summary.total_trades || 0} total trades</p>
        </div>

        {/* Profit Factor */}
        <div className={`stat-card ${summary.profit_factor >= 1 ? 'success' : 'danger'}`}>
          <p className="stat-label">Profit Factor</p>
          <p className={`stat-value ${summary.profit_factor >= 1 ? 'text-success' : 'text-danger'}`}>
            {summary.profit_factor?.toFixed(2) || '0.00'}
          </p>
          <p className="stat-change text-muted">
            {summary.profit_factor >= 1.5 ? 'Excellent' : summary.profit_factor >= 1 ? 'Good' : 'Poor'}
          </p>
        </div>

        {/* Max Drawdown */}
        <div className={`stat-card ${Math.abs(summary.max_drawdown || 0) > 500 ? 'danger' : ''}`}>
          <p className="stat-label">Max Drawdown</p>
          <p className="stat-value text-danger">
            ${Math.abs(summary.max_drawdown || 0).toFixed(2)}
          </p>
          <p className="stat-change text-muted">Peak to trough</p>
        </div>

        {/* Open Positions */}
        <div className={`stat-card ${openPositions.length > 0 ? 'warning' : ''}`}>
          <p className="stat-label">Open Positions</p>
          <p className="stat-value">{openPositions.length}</p>
          <p className="stat-change text-muted">Active trades</p>
        </div>
      </div>

      {/* Equity Curve */}
      {equityCurve.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              Equity Curve
            </h3>
            <span className="badge badge-info">Live</span>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColors.stroke} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={chartColors.stroke} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis
                dataKey="timestamp"
                stroke={chartColors.text}
                tick={{ fill: chartColors.text, fontSize: 12 }}
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis
                stroke={chartColors.text}
                tick={{ fill: chartColors.text, fontSize: 12 }}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: darkMode ? '#1e293b' : '#ffffff',
                  border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}
                formatter={(value) => [`$${value.toFixed(2)}`, 'Equity']}
                labelFormatter={(value) => new Date(value).toLocaleString()}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={chartColors.stroke}
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Open Positions */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <svg className="w-5 h-5 text-warning" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              Open Positions
            </h3>
            <span className="badge badge-warning">{openPositions.length} Active</span>
          </div>

          {openPositions.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th className="text-right">Entry</th>
                    <th className="text-right">Current</th>
                    <th className="text-right">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((pos, idx) => (
                    <tr key={idx}>
                      <td className="font-semibold">{pos.symbol}</td>
                      <td className="text-right text-muted">${pos.entry_price?.toFixed(2)}</td>
                      <td className="text-right text-muted">${pos.current_price?.toFixed(2)}</td>
                      <td className={`text-right font-semibold ${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl?.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
                <svg className="w-6 h-6 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                </svg>
              </div>
              <p className="text-muted">No open positions</p>
            </div>
          )}
        </div>

        {/* Risk Management & Trading Intelligence */}
        <div className="space-y-6">
          {/* Risk Management */}
          {riskStatus && riskStatus.status === 'success' && (
            <div className={`card p-6 ${riskStatus.risk_status?.circuit_breaker_active ? 'card-danger' : ''}`}>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Risk Management
                </h3>
                <span className={`badge ${riskStatus.risk_status?.circuit_breaker_active ? 'badge-danger' : 'badge-success'}`}>
                  {riskStatus.risk_status?.circuit_breaker_active ? 'Alert' : 'Normal'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-1">Circuit Breaker</p>
                  <p className={`text-lg font-semibold ${riskStatus.risk_status?.circuit_breaker_active ? 'text-danger' : 'text-success'}`}>
                    {riskStatus.risk_status?.circuit_breaker_active ? 'ACTIVE' : 'OK'}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-1">Daily P&L</p>
                  <p className={`text-lg font-semibold ${riskStatus.risk_status?.daily_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                    ${riskStatus.risk_status?.daily_pnl?.toFixed(2) || '0.00'}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-1">Loss Remaining</p>
                  <p className="text-lg font-semibold">
                    ${riskStatus.risk_status?.daily_loss_remaining?.toFixed(2) || '0.00'}
                  </p>
                </div>
                <div className="p-4 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-1">Consecutive Losses</p>
                  <p className={`text-lg font-semibold ${riskStatus.risk_status?.consecutive_losses >= 3 ? 'text-danger' : ''}`}>
                    {riskStatus.risk_status?.consecutive_losses || 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Trading Intelligence */}
          {botStatus && (botStatus.trading_iq > 0 || botStatus.expertise_level !== 'Untrained') && (() => {
            const internalIQ = botStatus.trading_iq || 0;
            const humanIQ = mapToHumanIQ(internalIQ);
            const classification = getIQClassification(humanIQ);
            const iqProgress = Math.min(100, ((humanIQ - 70) / 90) * 100); // 70-160 range to 0-100%

            return (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    Trading Intelligence
                  </h3>
                  <span className={`badge badge-info`}>
                    {botStatus.expertise_level || 'Untrained'}
                  </span>
                </div>

                {/* IQ Display */}
                <div className="flex items-center gap-6 mb-4">
                  {/* IQ Score Circle */}
                  <div className="relative flex-shrink-0">
                    <div className="w-24 h-24 rounded-full border-4 border-[var(--bg-tertiary)] flex items-center justify-center"
                      style={{
                        background: `conic-gradient(var(--accent) ${iqProgress * 3.6}deg, var(--bg-tertiary) 0deg)`
                      }}>
                      <div className="w-20 h-20 rounded-full bg-[var(--bg-primary)] flex flex-col items-center justify-center">
                        <span className="text-2xl font-bold">{humanIQ}</span>
                        <span className="text-xs text-muted">IQ</span>
                      </div>
                    </div>
                  </div>

                  {/* IQ Details */}
                  <div className="flex-1">
                    <p className={`text-lg font-semibold ${classification.color} mb-1`}>
                      {classification.label}
                    </p>
                    <p className="text-sm text-muted mb-2">
                      Human IQ Scale (70-160)
                    </p>
                    {/* IQ Progress Bar */}
                    <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 via-green-500 to-yellow-500 rounded-full transition-all duration-500"
                        style={{ width: `${iqProgress}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-muted mt-1">
                      <span>70</span>
                      <span>100</span>
                      <span>130</span>
                      <span>160</span>
                    </div>
                  </div>
                </div>

                {/* Training Stats */}
                {botStatus.training && (
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[var(--bg-tertiary)]">
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className="text-xs text-muted uppercase tracking-wide mb-1">Episodes</p>
                      <p className="text-lg font-semibold">
                        {botStatus.training.completed_episodes || 0} / {botStatus.training.total_episodes || 0}
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-[var(--bg-tertiary)]">
                      <p className="text-xs text-muted uppercase tracking-wide mb-1">Avg Win Rate</p>
                      <p className={`text-lg font-semibold ${(botStatus.training.avg_win_rate || 0) >= 50 ? 'text-success' : 'text-danger'}`}>
                        {(botStatus.training.avg_win_rate || 0).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            Recent Trades
          </h3>
          <span className="text-sm text-muted">Last 5 trades</span>
        </div>

        {recentTrades.length > 0 ? (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Symbol</th>
                  <th>Signal</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">P&L</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((trade, idx) => (
                  <tr key={idx}>
                    <td className="text-muted text-sm">
                      {new Date(trade.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="font-semibold">{trade.symbol}</td>
                    <td>
                      <span className={`badge ${trade.signal === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                        {trade.signal}
                      </span>
                    </td>
                    <td className="text-right text-muted">${trade.last_price?.toFixed(2)}</td>
                    <td className={`text-right font-semibold ${trade.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8">
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
              <svg className="w-6 h-6 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <p className="text-muted">No trades yet. Start the bot to begin trading.</p>
          </div>
        )}
      </div>
    </div>
  );
}
