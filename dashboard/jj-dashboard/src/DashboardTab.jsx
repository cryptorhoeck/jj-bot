import React, { useState, useEffect } from 'react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Brush } from 'recharts';

// Currency configuration - CAD is the base currency (rate 1.0)
// Rates are FROM CAD TO other currencies
const CURRENCIES = {
  CAD: { symbol: 'C$', name: 'Canadian Dollar', rate: 1.0 },
  USD: { symbol: '$', name: 'US Dollar', rate: 0.735 },  // 1 CAD = 0.735 USD
  EUR: { symbol: '€', name: 'Euro', rate: 0.676 },       // 1 CAD = 0.676 EUR
  GBP: { symbol: '£', name: 'British Pound', rate: 0.581 }, // 1 CAD = 0.581 GBP
  AUD: { symbol: 'A$', name: 'Australian Dollar', rate: 1.125 }, // 1 CAD = 1.125 AUD
  JPY: { symbol: '¥', name: 'Japanese Yen', rate: 109.9 }, // 1 CAD = 109.9 JPY
  CHF: { symbol: 'Fr', name: 'Swiss Franc', rate: 0.647 }, // 1 CAD = 0.647 CHF
};

// Format currency - amounts are in CAD, convert to selected currency
const formatCurrency = (value, currency = 'CAD') => {
  const curr = CURRENCIES[currency] || CURRENCIES.CAD;
  const converted = value * curr.rate;

  return `${curr.symbol}${converted.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })}`;
};

// Calculate font size based on text length to auto-fit in container
const getAutoFontSize = (text, baseSize = 1.5, minSize = 0.65) => {
  const len = String(text).length;
  // Scale down aggressively as text gets longer - must fit on ONE line
  if (len <= 8) return `${baseSize}rem`;        // $10,000 = 1.5rem
  if (len <= 10) return `${baseSize * 0.85}rem`; // $100,000.00 = 1.275rem
  if (len <= 12) return `${baseSize * 0.75}rem`; // C$137,274.76 = 1.125rem
  if (len <= 14) return `${baseSize * 0.65}rem`; // +C$1,234.56 = 0.975rem
  if (len <= 16) return `${baseSize * 0.58}rem`; // longer = 0.87rem
  if (len <= 18) return `${baseSize * 0.52}rem`; // even longer = 0.78rem
  return `${minSize}rem`;                        // max length = 0.65rem
};

export function DashboardTab({ darkMode, summary, trades, API_BASE, botStatus, currency = 'CAD' }) {
  const [equityCurve, setEquityCurve] = useState([]);
  const [openPositions, setOpenPositions] = useState([]);
  const [riskStatus, setRiskStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Trading IQ state
  const [tradingIQ, setTradingIQ] = useState({ iq: 0, level: 'Untrained' });
  const [trainingHistory, setTrainingHistory] = useState({});
  const [trainingProgress, setTrainingProgress] = useState(null);

  // Equity curve zoom/range state
  const [chartRange, setChartRange] = useState('all'); // '1h', '4h', '1d', '1w', 'all'
  const [chartHeight, setChartHeight] = useState(300);

  // Y-axis zoom state (dollar range)
  const [yAxisZoom, setYAxisZoom] = useState(100); // percentage of data range to show (100 = full, 50 = zoomed in 2x)
  const [yAxisOffset, setYAxisOffset] = useState(50); // where the zoom window is centered (0-100)

  // Use botStatus from props as fallback for training detection
  const isTraining = trainingProgress?.is_training || (botStatus?.mode === 'training' && botStatus?.running);
  const currentTrainingProgress = trainingProgress || botStatus?.training;

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

        // Fetch Trading IQ from pro status
        const proStatusRes = await fetch(`${API_BASE}/api/pro/status`);
        if (proStatusRes.ok) {
          const proData = await proStatusRes.json();
          setTradingIQ({
            iq: proData.trading_iq || 0,
            level: proData.expertise_level || 'Untrained'
          });
          if (proData.training_history) {
            setTrainingHistory(proData.training_history);
          }
          // Store training progress for live updates
          if (proData.training) {
            setTrainingProgress(proData.training);
          } else {
            setTrainingProgress(null);
          }
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
        <div className="card p-4">
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

  // Filter equity curve by time range
  const getFilteredEquityCurve = () => {
    if (!equityCurve.length || chartRange === 'all') return equityCurve;

    const now = new Date();
    const ranges = {
      '1h': 60 * 60 * 1000,
      '4h': 4 * 60 * 60 * 1000,
      '1d': 24 * 60 * 60 * 1000,
      '1w': 7 * 24 * 60 * 60 * 1000,
      '1m': 30 * 24 * 60 * 60 * 1000,
    };

    const cutoff = new Date(now - ranges[chartRange]);
    return equityCurve.filter(point => new Date(point.timestamp) >= cutoff);
  };

  const filteredEquityCurve = getFilteredEquityCurve();

  // Chart height options
  const heightOptions = [200, 300, 400, 500];

  // Calculate Y-axis domain based on zoom level and offset
  const getYAxisDomain = () => {
    if (!filteredEquityCurve.length) return ['auto', 'auto'];

    // Get min/max equity values from data
    const equityValues = filteredEquityCurve.map(d => d.equity).filter(v => v != null);
    if (!equityValues.length) return ['auto', 'auto'];

    const dataMin = Math.min(...equityValues);
    const dataMax = Math.max(...equityValues);
    const dataRange = dataMax - dataMin;

    // Add 5% padding to the full range
    const padding = dataRange * 0.05;
    const fullMin = dataMin - padding;
    const fullMax = dataMax + padding;
    const fullRange = fullMax - fullMin;

    // If zoom is 100%, show full range
    if (yAxisZoom >= 100) {
      return [fullMin, fullMax];
    }

    // Calculate zoomed range
    const zoomFactor = yAxisZoom / 100;
    const zoomedRange = fullRange * zoomFactor;

    // Calculate center point based on offset (0-100)
    // offset 50 = center of data, 0 = bottom, 100 = top
    const offsetFactor = yAxisOffset / 100;
    const centerValue = fullMin + (fullRange * offsetFactor);

    // Calculate new min/max centered on the offset point
    let yMin = centerValue - (zoomedRange / 2);
    let yMax = centerValue + (zoomedRange / 2);

    // Clamp to reasonable bounds (don't go too far outside data)
    const clampMin = fullMin - fullRange * 0.5;
    const clampMax = fullMax + fullRange * 0.5;
    yMin = Math.max(clampMin, yMin);
    yMax = Math.min(clampMax, yMax);

    return [yMin, yMax];
  };

  const yAxisDomain = getYAxisDomain();

  return (
    <div className="space-y-4">
      {/* Performance Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Current Equity - with auto-scaling text */}
        <div className="stat-card">
          <p className="stat-label">Current Equity</p>
          <p
            className="stat-value text-info"
            style={{ fontSize: getAutoFontSize(formatCurrency(summary.current_equity || 0, currency)) }}
          >
            {formatCurrency(summary.current_equity || 0, currency)}
          </p>
          <p className={`stat-change ${summary.return_pct >= 0 ? 'positive' : 'negative'}`}>
            {summary.return_pct >= 0 ? '+' : ''}{summary.return_pct?.toFixed(2) || '0.00'}% return
          </p>
        </div>

        {/* Total P&L */}
        <div className={`stat-card ${summary.total_pnl >= 0 ? 'success' : 'danger'}`}>
          <p className="stat-label">Total P&L</p>
          <p
            className={`stat-value ${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}`}
            style={{ fontSize: getAutoFontSize(`${summary.total_pnl >= 0 ? '+' : '-'}${formatCurrency(Math.abs(summary.total_pnl || 0), currency)}`) }}
          >
            {summary.total_pnl >= 0 ? '+' : '-'}{formatCurrency(Math.abs(summary.total_pnl || 0), currency)}
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
          <p
            className="stat-value text-danger"
            style={{ fontSize: getAutoFontSize(formatCurrency(Math.abs(summary.max_drawdown || 0), currency)) }}
          >
            {formatCurrency(Math.abs(summary.max_drawdown || 0), currency)}
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
        <div className="card p-4">
          <div className="flex flex-col gap-3 mb-4">
            {/* Header row */}
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <svg className="w-5 h-5 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                </svg>
                Equity Curve
              </h3>
              <span className="badge badge-info">Live • {filteredEquityCurve.length} points</span>
            </div>

            {/* Controls row */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Time range buttons */}
              <div className="flex items-center gap-1 bg-[var(--bg-tertiary)] rounded-lg p-1">
                {['1h', '4h', '1d', '1w', '1m', 'all'].map((range) => (
                  <button
                    key={range}
                    onClick={() => setChartRange(range)}
                    className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                      chartRange === range
                        ? 'bg-info text-white'
                        : 'text-muted hover:text-[var(--text-primary)] hover:bg-[var(--bg-secondary)]'
                    }`}
                  >
                    {range.toUpperCase()}
                  </button>
                ))}
              </div>

              {/* Height control */}
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">Height:</span>
                <select
                  value={chartHeight}
                  onChange={(e) => setChartHeight(Number(e.target.value))}
                  className="px-2 py-1 text-xs rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-color)] text-[var(--text-primary)]"
                >
                  {heightOptions.map((h) => (
                    <option key={h} value={h}>{h}px</option>
                  ))}
                </select>
              </div>

              {/* Height +/- buttons */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setChartHeight(Math.max(200, chartHeight - 50))}
                  className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-muted hover:text-[var(--text-primary)] transition-colors"
                  title="Decrease height"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                </button>
                <button
                  onClick={() => setChartHeight(Math.min(600, chartHeight + 50))}
                  className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-muted hover:text-[var(--text-primary)] transition-colors"
                  title="Increase height"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>

              {/* Y-Axis Zoom Controls (Dollar Range) */}
              <div className="flex items-center gap-2 border-l border-[var(--border-color)] pl-3">
                <span className="text-xs text-muted">$ Range:</span>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setYAxisZoom(Math.max(10, yAxisZoom - 15))}
                    className="p-1.5 rounded-lg bg-info/20 hover:bg-info/30 text-info transition-colors"
                    title="Zoom in (tighter range)"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v6m3-3H7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setYAxisZoom(Math.min(100, yAxisZoom + 15))}
                    className="p-1.5 rounded-lg bg-info/20 hover:bg-info/30 text-info transition-colors"
                    title="Zoom out (wider range)"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM13 10H7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => { setYAxisZoom(100); setYAxisOffset(50); }}
                    className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-muted hover:text-[var(--text-primary)] transition-colors"
                    title="Reset to auto-fit"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                  </button>
                </div>
                <span className="text-xs text-muted font-mono w-10 text-right">{yAxisZoom}%</span>
              </div>

              {/* Y-Axis Pan Controls (only show when zoomed in) */}
              {yAxisZoom < 100 && (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setYAxisOffset(Math.min(100, yAxisOffset + 10))}
                    className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-muted hover:text-[var(--text-primary)] transition-colors"
                    title="Pan up"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setYAxisOffset(Math.max(0, yAxisOffset - 10))}
                    className="p-1.5 rounded-lg bg-[var(--bg-tertiary)] hover:bg-[var(--bg-secondary)] text-muted hover:text-[var(--text-primary)] transition-colors"
                    title="Pan down"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </div>

          <ResponsiveContainer width="100%" height={chartHeight}>
            <AreaChart data={filteredEquityCurve}>
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
                tick={{ fill: chartColors.text, fontSize: 11 }}
                tickFormatter={(value) => {
                  const date = new Date(value);
                  // Show date + time for shorter ranges, date only for longer
                  if (chartRange === '1h' || chartRange === '4h') {
                    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                  } else if (chartRange === '1d') {
                    return date.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
                  }
                  return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
                }}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke={chartColors.text}
                tick={{ fill: chartColors.text, fontSize: 11 }}
                tickFormatter={(value) => formatCurrency(value, currency, value >= 100000)}
                width={80}
                domain={yAxisDomain}
                allowDataOverflow={true}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: darkMode ? '#1e293b' : '#ffffff',
                  border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                  borderRadius: '8px',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
                }}
                formatter={(value) => [formatCurrency(value, currency), 'Equity']}
                labelFormatter={(value) => {
                  const date = new Date(value);
                  return date.toLocaleString([], {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit'
                  });
                }}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke={chartColors.stroke}
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
              {/* Brush for additional zoom control */}
              {filteredEquityCurve.length > 50 && (
                <Brush
                  dataKey="timestamp"
                  height={30}
                  stroke={chartColors.stroke}
                  fill={darkMode ? '#1e293b' : '#f8fafc'}
                  tickFormatter={(value) => new Date(value).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Two Column Layout - Open Positions left, Risk + IQ stacked on right */}
      <div className="grid lg:grid-cols-2 gap-4">
        {/* Open Positions - Full height on left */}
        <div className="card p-4 flex flex-col">
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
            <div className="table-container flex-1" style={{ maxHeight: '340px', overflowY: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Opened</th>
                    <th className="text-right">Entry</th>
                    <th className="text-right">Current</th>
                    <th className="text-right">P&L</th>
                  </tr>
                </thead>
                <tbody>
                  {openPositions.map((pos, idx) => (
                    <tr key={idx}>
                      <td className="font-semibold">{pos.symbol}</td>
                      <td className="text-muted text-sm">
                        {pos.entry_time ? new Date(pos.entry_time).toLocaleString() : '-'}
                      </td>
                      <td className="text-right text-muted">{formatCurrency(pos.entry_price || 0, currency)}</td>
                      <td className="text-right text-muted">{formatCurrency(pos.current_price || 0, currency)}</td>
                      <td className={`text-right font-semibold ${pos.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}{formatCurrency(pos.unrealized_pnl || 0, currency)}
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

        {/* Right column - Risk Management + Trading IQ stacked */}
        <div className="flex flex-col gap-4">
          {/* Risk Management - Compact */}
          {riskStatus && riskStatus.status === 'success' && (
            <div className={`card p-4 ${riskStatus.risk_status?.circuit_breaker_active ? 'card-danger' : ''}`}>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-semibold flex items-center gap-2">
                  <svg className="w-4 h-4 text-info" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                  Risk Management
                </h3>
                <span className={`badge ${riskStatus.risk_status?.circuit_breaker_active ? 'badge-danger' : 'badge-success'}`}>
                  {riskStatus.risk_status?.circuit_breaker_active ? 'Alert' : 'Normal'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Circuit Breaker</p>
                  <p className={`text-base font-semibold truncate ${riskStatus.risk_status?.circuit_breaker_active ? 'text-danger' : 'text-success'}`}>
                    {riskStatus.risk_status?.circuit_breaker_active ? 'ACTIVE' : 'OK'}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Daily P&L</p>
                  <p
                    className={`font-semibold ${riskStatus.risk_status?.daily_pnl >= 0 ? 'text-success' : 'text-danger'}`}
                    style={{ fontSize: getAutoFontSize(formatCurrency(riskStatus.risk_status?.daily_pnl || 0, currency), 1.0, 0.65) }}
                  >
                    {formatCurrency(riskStatus.risk_status?.daily_pnl || 0, currency)}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Loss Remaining</p>
                  <p
                    className="font-semibold"
                    style={{ fontSize: getAutoFontSize(formatCurrency(riskStatus.risk_status?.daily_loss_remaining || 0, currency), 1.0, 0.65) }}
                  >
                    {formatCurrency(riskStatus.risk_status?.daily_loss_remaining || 0, currency)}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                  <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Consecutive Losses</p>
                  <p className={`text-base font-semibold truncate ${riskStatus.risk_status?.consecutive_losses >= 3 ? 'text-danger' : ''}`}>
                    {riskStatus.risk_status?.consecutive_losses || 0}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Trading IQ Card */}
          <div className={`card p-4 ${isTraining ? 'card-info' : ''}`}>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold flex items-center gap-2">
                <span className="text-lg">🧠</span>
                Trading IQ
              </h3>
              <span className={`badge ${isTraining ? 'badge-info' : 'badge-info'}`}>
                {isTraining ? '⚡ Training' : tradingIQ.level}
              </span>
            </div>

            <div className="flex items-center gap-3 mb-3">
              <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center shadow-lg flex-shrink-0">
                <span className="text-xl font-bold text-white">
                  {isTraining ? currentTrainingProgress?.trading_iq || tradingIQ.iq : tradingIQ.iq}
                </span>
              </div>
              <div className="flex-1">
                {isTraining ? (
                  <div>
                    <p className="text-sm font-semibold text-info mb-0.5">
                      {currentTrainingProgress?.expertise_level || tradingIQ.level}
                    </p>
                    <p className="text-xs text-muted">
                      Episode {currentTrainingProgress?.current_episode || 0}/{currentTrainingProgress?.total_episodes || 0}
                      <span className="ml-1">
                        ({(currentTrainingProgress?.total_episodes || 0) - (currentTrainingProgress?.current_episode || 0)} left)
                      </span>
                    </p>
                  </div>
                ) : (
                  <p className="text-sm text-muted">
                    {tradingIQ.iq === 0
                      ? 'Train AI to improve decisions'
                      : 'AI-powered trading intelligence'}
                  </p>
                )}
              </div>
            </div>

            {/* Live Training Progress Bar */}
            {isTraining && (
              <div className="mb-3">
                {/* Real Data Indicator */}
                <div className={`flex items-center gap-2 mb-2 px-2 py-1.5 rounded-md text-xs ${currentTrainingProgress?.using_real_data ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>
                  <span>{currentTrainingProgress?.using_real_data ? '📊' : '⚠️'}</span>
                  <span className="font-medium">
                    {currentTrainingProgress?.using_real_data ? 'Real Data' : 'Simulated'}
                  </span>
                  {currentTrainingProgress?.using_real_data && currentTrainingProgress?.current_symbol && (
                    <span className="text-muted">• <span className="font-mono">{currentTrainingProgress.current_symbol}</span></span>
                  )}
                </div>

                <div className="flex justify-between text-xs text-muted mb-1">
                  <span>Progress</span>
                  <span className="font-semibold">{currentTrainingProgress?.progress_pct?.toFixed(1) || 0}%</span>
                </div>
                <div className="w-full h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500 ease-out"
                    style={{ width: `${currentTrainingProgress?.progress_pct || 0}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted mt-1">
                  <span>Win: {currentTrainingProgress?.avg_win_rate?.toFixed(1) || 0}%</span>
                  <span>Trades: {(currentTrainingProgress?.total_trades || 0).toLocaleString()}</span>
                  <span>Reward: {currentTrainingProgress?.avg_reward?.toFixed(0) || 0}</span>
                </div>
              </div>
            )}

            <div className="grid grid-cols-3 gap-2">
              <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Sessions</p>
                <p className="text-base font-semibold truncate">
                  {(trainingHistory.training_sessions || 0).toLocaleString()}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Episodes</p>
                <p className="text-base font-semibold truncate">
                  {(trainingHistory.total_training_episodes || 0).toLocaleString()}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-[var(--bg-tertiary)]">
                <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Trades</p>
                <p className="text-base font-semibold truncate">
                  {(trainingHistory.total_training_trades || 0).toLocaleString()}
                </p>
              </div>
              <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] col-span-1">
                <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Avg Win Rate</p>
                <p className="text-base font-semibold text-success truncate">
                  {trainingHistory.avg_win_rate?.toFixed(1) || '0'}%
                </p>
              </div>
              <div className="p-2 rounded-lg bg-[var(--bg-tertiary)] col-span-2">
                <p className="text-xs text-muted uppercase tracking-wide mb-0.5">Profit Factor</p>
                <p className="text-base font-semibold text-success truncate">
                  {trainingHistory.avg_profit_factor?.toFixed(2) || '0.00'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card p-4">
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
                      {new Date(trade.timestamp).toLocaleString()}
                    </td>
                    <td className="font-semibold">{trade.symbol}</td>
                    <td>
                      <span className={`badge ${trade.signal === 'BUY' ? 'badge-success' : 'badge-danger'}`}>
                        {trade.signal}
                      </span>
                    </td>
                    <td className="text-right text-muted">{formatCurrency(trade.last_price || 0, currency)}</td>
                    <td className={`text-right font-semibold ${trade.pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                      {trade.pnl >= 0 ? '+' : ''}{formatCurrency(trade.pnl || 0, currency)}
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
