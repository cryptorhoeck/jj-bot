import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { StatsGridSkeleton, ChartSkeleton, TableSkeleton, NoTrades, NoPositions, ErrorState } from './components';

export function DashboardTab({ colors, darkMode, summary, trades, API_BASE }) {
  const [equityCurve, setEquityCurve] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [riskStatus, setRiskStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch all dashboard data
  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setError(null);

        // Fetch equity curve
        const equityRes = await fetch(`${API_BASE}/api/equity-curve`);
        if (equityRes.ok) {
          const equityData = await equityRes.json();
          setEquityCurve(equityData.equity_curve || []);
        }

        // Fetch open positions
        const positionsRes = await fetch(`${API_BASE}/api/positions/open`);
        if (positionsRes.ok) {
          const positionsData = await positionsRes.json();
          setOpenPositions(positionsData.open_positions || []);
        }

        // Fetch risk status
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
    const interval = setInterval(fetchDashboardData, 10000); // Update every 10s

    return () => clearInterval(interval);
  }, [API_BASE]);

  // Show loading skeletons
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            📊 Performance Overview
          </h2>
          <StatsGridSkeleton count={6} darkMode={darkMode} />
        </div>
        <ChartSkeleton darkMode={darkMode} height="300px" />
        <TableSkeleton rows={5} cols={5} darkMode={darkMode} />
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <ErrorState
        icon="📡"
        title="Connection Error"
        description="Unable to load dashboard data. The server may be offline or unreachable."
        error={error}
        onRetry={() => {
          setLoading(true);
          setError(null);
        }}
        darkMode={darkMode}
      />
    );
  }

  const recentTrades = trades.slice(0, 5);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Performance Overview */}
      <div>
        <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📊 Performance Overview
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          {/* Current Equity */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Current Equity</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.blue }}>
              ${summary.current_equity?.toLocaleString() || '10,000'}
            </p>
            <p style={{ fontSize: '0.75rem', color: summary.return_pct >= 0 ? colors.green : colors.red, marginTop: '0.5rem' }}>
              {summary.return_pct >= 0 ? '+' : ''}{summary.return_pct?.toFixed(2)}% return
            </p>
          </div>

          {/* Total P&L */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${summary.total_pnl >= 0 ? colors.green : colors.red}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Total P&L</p>
            <p style={{
              fontSize: '2rem',
              fontWeight: '700',
              color: summary.total_pnl >= 0 ? colors.green : colors.red
            }}>
              ${summary.total_pnl >= 0 ? '+' : ''}{summary.total_pnl?.toFixed(2)}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              {summary.winning_trades || 0}W / {summary.losing_trades || 0}L
            </p>
          </div>

          {/* Win Rate */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Win Rate</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.text }}>
              {summary.win_rate?.toFixed(1) || 0}%
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              {summary.total_trades || 0} trades
            </p>
          </div>

          {/* Profit Factor */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Profit Factor</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: summary.profit_factor >= 1 ? colors.green : colors.red }}>
              {summary.profit_factor?.toFixed(2) || '0.00'}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              {summary.profit_factor >= 1.5 ? 'Excellent' : summary.profit_factor >= 1 ? 'Good' : 'Poor'}
            </p>
          </div>

          {/* Max Drawdown */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${Math.abs(summary.max_drawdown) > 500 ? colors.red : colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Max Drawdown</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.red }}>
              ${Math.abs(summary.max_drawdown || 0).toFixed(2)}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              Peak to trough
            </p>
          </div>

          {/* Open Positions */}
          <div style={{
            backgroundColor: colors.card,
            padding: '1.5rem',
            borderRadius: '0.75rem',
            border: `2px solid ${openPositions.length > 0 ? colors.yellow : colors.border}`
          }}>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '0.5rem' }}>Open Positions</p>
            <p style={{ fontSize: '2rem', fontWeight: '700', color: colors.text }}>
              {openPositions.length}
            </p>
            <p style={{ fontSize: '0.75rem', color: colors.textMuted, marginTop: '0.5rem' }}>
              Active trades
            </p>
          </div>
        </div>
      </div>

      {/* Equity Curve Chart */}
      {equityCurve.length > 0 && (
        <div style={{
          backgroundColor: colors.card,
          padding: '1.5rem',
          borderRadius: '0.75rem',
          border: `1px solid ${colors.border}`
        }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            📈 Equity Curve
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={equityCurve}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors.blue} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={colors.blue} stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
              <XAxis
                dataKey="timestamp"
                stroke={colors.textMuted}
                tick={{ fill: colors.textMuted }}
                tickFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <YAxis
                stroke={colors.textMuted}
                tick={{ fill: colors.textMuted }}
                tickFormatter={(value) => `$${value.toLocaleString()}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.5rem',
                  color: colors.text
                }}
                formatter={(value) => [`$${value.toFixed(2)}`, 'Equity']}
                labelFormatter={(value) => new Date(value).toLocaleString()}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={colors.blue}
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Open Positions */}
      {openPositions.length > 0 && (
        <div style={{
          backgroundColor: colors.card,
          padding: '1.5rem',
          borderRadius: '0.75rem',
          border: `1px solid ${colors.border}`
        }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            💼 Open Positions
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${colors.border}` }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.textMuted, fontSize: '0.875rem' }}>Symbol</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>Entry</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>Current</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>P&L</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>%</th>
                </tr>
              </thead>
              <tbody>
                {openPositions.map((pos, idx) => (
                  <tr key={idx} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: '0.75rem', color: colors.text, fontWeight: '600' }}>{pos.symbol}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted }}>${pos.entry_price?.toFixed(2)}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted }}>${pos.current_price?.toFixed(2)}</td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: pos.unrealized_pnl >= 0 ? colors.green : colors.red, fontWeight: '600' }}>
                      ${pos.unrealized_pnl >= 0 ? '+' : ''}{pos.unrealized_pnl?.toFixed(2)}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: pos.pnl_pct >= 0 ? colors.green : colors.red }}>
                      {pos.pnl_pct >= 0 ? '+' : ''}{pos.pnl_pct?.toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Risk Management Status */}
      {riskStatus && riskStatus.status === 'success' && (
        <div style={{
          backgroundColor: colors.card,
          padding: '1.5rem',
          borderRadius: '0.75rem',
          border: `1px solid ${riskStatus.risk_status.circuit_breaker_active ? colors.red : colors.border}`
        }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
            🛡️ Risk Management
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Circuit Breaker</p>
              <p style={{ fontSize: '1.25rem', fontWeight: '600', color: riskStatus.risk_status.circuit_breaker_active ? colors.red : colors.green }}>
                {riskStatus.risk_status.circuit_breaker_active ? '🔴 ACTIVE' : '✅ OK'}
              </p>
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Daily P&L</p>
              <p style={{ fontSize: '1.25rem', fontWeight: '600', color: riskStatus.risk_status.daily_pnl >= 0 ? colors.green : colors.red }}>
                ${riskStatus.risk_status.daily_pnl?.toFixed(2)}
              </p>
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Loss Remaining</p>
              <p style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.text }}>
                ${riskStatus.risk_status.daily_loss_remaining?.toFixed(2)}
              </p>
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: colors.textMuted }}>Consecutive Losses</p>
              <p style={{ fontSize: '1.25rem', fontWeight: '600', color: riskStatus.risk_status.consecutive_losses >= 3 ? colors.red : colors.text }}>
                {riskStatus.risk_status.consecutive_losses}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Trades */}
      <div style={{
        backgroundColor: colors.card,
        padding: '1.5rem',
        borderRadius: '0.75rem',
        border: `1px solid ${colors.border}`
      }}>
        <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
          📋 Recent Trades
        </h3>
        {recentTrades.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: `2px solid ${colors.border}` }}>
                  <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.textMuted, fontSize: '0.875rem' }}>Time</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.textMuted, fontSize: '0.875rem' }}>Symbol</th>
                  <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.textMuted, fontSize: '0.875rem' }}>Signal</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>Price</th>
                  <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted, fontSize: '0.875rem' }}>P&L</th>
                </tr>
              </thead>
              <tbody>
                {recentTrades.map((trade, idx) => (
                  <tr key={idx} style={{ borderBottom: `1px solid ${colors.border}` }}>
                    <td style={{ padding: '0.75rem', color: colors.textMuted, fontSize: '0.875rem' }}>
                      {new Date(trade.timestamp).toLocaleTimeString()}
                    </td>
                    <td style={{ padding: '0.75rem', color: colors.text, fontWeight: '600' }}>{trade.symbol}</td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        backgroundColor: trade.signal === 'BUY' ? `${colors.green}20` : `${colors.red}20`,
                        color: trade.signal === 'BUY' ? colors.green : colors.red
                      }}>
                        {trade.signal}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', color: colors.textMuted }}>
                      ${trade.last_price?.toFixed(2)}
                    </td>
                    <td style={{ padding: '0.75rem', textAlign: 'right', fontWeight: '600', color: trade.pnl >= 0 ? colors.green : colors.red }}>
                      ${trade.pnl >= 0 ? '+' : ''}{trade.pnl?.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <NoTrades darkMode={darkMode} />
        )}
      </div>
    </div>
  );
}
