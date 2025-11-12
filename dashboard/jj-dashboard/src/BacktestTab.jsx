import React, { useState, useEffect } from 'react';

export function BacktestTab({ colors, darkMode, API_BASE }) {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState('rsi_strategy');
  const [symbol, setSymbol] = useState('BTC');
  const [initialCapital, setInitialCapital] = useState(10000);
  const [commission, setCommission] = useState(0.001);
  const [slippage, setSlippage] = useState(0.0005);
  const [positionSize, setPositionSize] = useState(0.1);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [csvContent, setCsvContent] = useState('');

  // Fetch available strategies
  useEffect(() => {
    fetchStrategies();
  }, []);

  const fetchStrategies = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/backtest/strategies`);
      const data = await response.json();
      if (data.success) {
        setStrategies(Object.entries(data.strategies).map(([key, value]) => ({
          id: key,
          ...value
        })));
      }
    } catch (error) {
      console.error('Error fetching strategies:', error);
    }
  };

  const generateSampleData = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/backtest/generate-sample-data?symbol=${symbol}&days=${days}`,
        { method: 'POST' }
      );
      const data = await response.json();
      if (data.success) {
        alert(`✅ Generated ${days} days of sample ${symbol} data`);
      }
    } catch (error) {
      alert('Error generating data: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const uploadCSV = async () => {
    if (!csvContent.trim()) {
      alert('Please paste CSV content first');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/backtest/upload-csv?symbol=${symbol}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, csv_content: csvContent })
      });
      const data = await response.json();
      if (data.success) {
        alert(`✅ Loaded ${data.data_points} data points`);
        setCsvContent('');
      }
    } catch (error) {
      alert('Error uploading CSV: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async () => {
    setLoading(true);
    setResults(null);
    try {
      const response = await fetch(`${API_BASE}/api/backtest/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          strategy: selectedStrategy,
          initial_capital: initialCapital,
          commission,
          slippage,
          position_size: positionSize
        })
      });
      const data = await response.json();
      if (data.success) {
        setResults(data.results);
      } else {
        alert('Backtest failed: ' + (data.error || 'Unknown error'));
      }
    } catch (error) {
      alert('Error running backtest: ' + error);
    } finally {
      setLoading(false);
    }
  };

  const renderEquityCurve = () => {
    if (!results || !results.equity_curve || results.equity_curve.length === 0) return null;

    const points = results.equity_curve;
    const maxEquity = Math.max(...points);
    const minEquity = Math.min(...points);
    const range = maxEquity - minEquity;

    return (
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>
          📈 Equity Curve
        </h3>
        <div style={{
          height: '200px',
          backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
          borderRadius: '0.5rem',
          padding: '1rem',
          position: 'relative',
          border: `1px solid ${colors.border}`
        }}>
          <svg width="100%" height="100%" style={{ overflow: 'visible' }}>
            <polyline
              points={points.map((value, index) => {
                const x = (index / (points.length - 1)) * 100;
                const y = 100 - ((value - minEquity) / range) * 80;
                return `${x}%,${y}%`;
              }).join(' ')}
              fill="none"
              stroke={results.total_pnl >= 0 ? '#10b981' : '#ef4444'}
              strokeWidth="2"
            />
          </svg>
          <div style={{
            position: 'absolute',
            bottom: '0.5rem',
            left: '0.5rem',
            fontSize: '0.75rem',
            color: colors.textMuted
          }}>
            ${minEquity.toFixed(2)}
          </div>
          <div style={{
            position: 'absolute',
            top: '0.5rem',
            left: '0.5rem',
            fontSize: '0.75rem',
            color: colors.textMuted
          }}>
            ${maxEquity.toFixed(2)}
          </div>
        </div>
      </div>
    );
  };

  const renderTradeTable = () => {
    if (!results || !results.trades || results.trades.length === 0) return null;

    return (
      <div style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>
          📋 Trade History ({results.trades.length} trades)
        </h3>
        <div style={{
          maxHeight: '400px',
          overflowY: 'auto',
          backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
          borderRadius: '0.5rem',
          border: `1px solid ${colors.border}`
        }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead style={{
              position: 'sticky',
              top: 0,
              backgroundColor: darkMode ? '#2d2d2d' : 'white',
              borderBottom: `2px solid ${colors.border}`
            }}>
              <tr>
                <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.text, fontSize: '0.75rem' }}>#</th>
                <th style={{ padding: '0.75rem', textAlign: 'left', color: colors.text, fontSize: '0.75rem' }}>Type</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>Entry</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>Exit</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>P&L</th>
                <th style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>Return %</th>
              </tr>
            </thead>
            <tbody>
              {results.trades.map((trade, index) => (
                <tr key={index} style={{
                  borderBottom: `1px solid ${colors.border}`,
                  backgroundColor: index % 2 === 0 ? (darkMode ? '#1a1a1a' : '#f9fafb') : 'transparent'
                }}>
                  <td style={{ padding: '0.75rem', color: colors.textMuted, fontSize: '0.75rem' }}>{index + 1}</td>
                  <td style={{ padding: '0.75rem', fontSize: '0.75rem' }}>
                    <span style={{
                      padding: '0.125rem 0.5rem',
                      borderRadius: '0.25rem',
                      backgroundColor: trade.type === 'LONG' ? '#10b981' : '#ef4444',
                      color: 'white',
                      fontSize: '0.625rem',
                      fontWeight: '600'
                    }}>
                      {trade.type}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>
                    ${trade.entry_price?.toFixed(2)}
                  </td>
                  <td style={{ padding: '0.75rem', textAlign: 'right', color: colors.text, fontSize: '0.75rem' }}>
                    ${trade.exit_price?.toFixed(2)}
                  </td>
                  <td style={{
                    padding: '0.75rem',
                    textAlign: 'right',
                    color: trade.pnl >= 0 ? '#10b981' : '#ef4444',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                  }}>
                    {trade.pnl >= 0 ? '+' : ''}${trade.pnl?.toFixed(2)}
                  </td>
                  <td style={{
                    padding: '0.75rem',
                    textAlign: 'right',
                    color: trade.return_pct >= 0 ? '#10b981' : '#ef4444',
                    fontSize: '0.75rem',
                    fontWeight: '600'
                  }}>
                    {trade.return_pct >= 0 ? '+' : ''}{trade.return_pct?.toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div style={{
      backgroundColor: colors.card,
      borderRadius: '0.5rem',
      padding: '1.5rem',
      boxShadow: darkMode ? '0 1px 3px rgba(0,0,0,0.5)' : '0 1px 3px rgba(0,0,0,0.1)'
    }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1.5rem', color: colors.text }}>
        📊 Strategy Backtesting
      </h2>

      {/* Configuration Panel */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '1rem',
        marginBottom: '1.5rem'
      }}>
        {/* Data Source */}
        <div style={{
          padding: '1rem',
          backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
          borderRadius: '0.5rem',
          border: `1px solid ${colors.border}`
        }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>
            📥 Data Source
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Symbol
              </label>
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Days of Data
              </label>
              <input
                type="number"
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <button
              onClick={generateSampleData}
              disabled={loading}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: loading ? colors.gray : colors.blue,
                color: 'white',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
                fontWeight: '600'
              }}
            >
              {loading ? '⏳ Loading...' : '📥 Generate Sample Data'}
            </button>
            <div style={{
              padding: '0.75rem',
              backgroundColor: colors.card,
              borderRadius: '0.375rem',
              border: `1px dashed ${colors.border}`
            }}>
              <textarea
                placeholder="Or paste CSV data here (timestamp,price,volume)"
                value={csvContent}
                onChange={(e) => setCsvContent(e.target.value)}
                rows={4}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.bg,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.75rem',
                  fontFamily: 'monospace',
                  resize: 'vertical'
                }}
              />
              <button
                onClick={uploadCSV}
                disabled={loading || !csvContent.trim()}
                style={{
                  marginTop: '0.5rem',
                  width: '100%',
                  padding: '0.375rem',
                  backgroundColor: loading || !csvContent.trim() ? colors.gray : colors.green,
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.375rem',
                  cursor: loading || !csvContent.trim() ? 'not-allowed' : 'pointer',
                  fontSize: '0.75rem',
                  fontWeight: '600'
                }}
              >
                📤 Upload CSV
              </button>
            </div>
          </div>
        </div>

        {/* Strategy Selection */}
        <div style={{
          padding: '1rem',
          backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
          borderRadius: '0.5rem',
          border: `1px solid ${colors.border}`
        }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>
            🎯 Strategy Selection
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              style={{
                width: '100%',
                padding: '0.5rem',
                backgroundColor: colors.card,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                color: colors.text,
                fontSize: '0.875rem'
              }}
            >
              {strategies.map(strategy => (
                <option key={strategy.id} value={strategy.id}>
                  {strategy.name} ({strategy.complexity})
                </option>
              ))}
            </select>
            {strategies.find(s => s.id === selectedStrategy) && (
              <div style={{
                padding: '0.75rem',
                backgroundColor: colors.card,
                borderRadius: '0.375rem',
                fontSize: '0.75rem',
                color: colors.textMuted
              }}>
                <strong style={{ color: colors.text }}>
                  {strategies.find(s => s.id === selectedStrategy)?.name}
                </strong>
                <br />
                {strategies.find(s => s.id === selectedStrategy)?.description}
                <br />
                <span style={{ fontSize: '0.625rem', marginTop: '0.25rem', display: 'inline-block' }}>
                  Category: {strategies.find(s => s.id === selectedStrategy)?.category}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Backtest Parameters */}
        <div style={{
          padding: '1rem',
          backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
          borderRadius: '0.5rem',
          border: `1px solid ${colors.border}`
        }}>
          <h3 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.75rem', color: colors.text }}>
            ⚙️ Parameters
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Initial Capital ($)
              </label>
              <input
                type="number"
                value={initialCapital}
                onChange={(e) => setInitialCapital(parseFloat(e.target.value))}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Commission (%)
              </label>
              <input
                type="number"
                step="0.001"
                value={commission * 100}
                onChange={(e) => setCommission(parseFloat(e.target.value) / 100)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Slippage (%)
              </label>
              <input
                type="number"
                step="0.001"
                value={slippage * 100}
                onChange={(e) => setSlippage(parseFloat(e.target.value) / 100)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem', display: 'block' }}>
                Position Size (% of capital)
              </label>
              <input
                type="number"
                step="0.01"
                value={positionSize * 100}
                onChange={(e) => setPositionSize(parseFloat(e.target.value) / 100)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  backgroundColor: colors.card,
                  border: `1px solid ${colors.border}`,
                  borderRadius: '0.375rem',
                  color: colors.text,
                  fontSize: '0.875rem'
                }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Run Backtest Button */}
      <button
        onClick={runBacktest}
        disabled={loading}
        style={{
          width: '100%',
          padding: '1rem',
          backgroundColor: loading ? colors.gray : colors.green,
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          cursor: loading ? 'not-allowed' : 'pointer',
          fontSize: '1.125rem',
          fontWeight: '700',
          marginBottom: '2rem',
          boxShadow: loading ? 'none' : '0 2px 4px rgba(16, 185, 129, 0.2)'
        }}
      >
        {loading ? '⏳ Running Backtest...' : '▶ RUN BACKTEST'}
      </button>

      {/* Results Section */}
      {results && (
        <div>
          {/* Performance Metrics */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '1rem',
            marginBottom: '2rem'
          }}>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Total Trades
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
                {results.total_trades}
              </div>
            </div>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Win Rate
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: results.win_rate >= 50 ? '#10b981' : '#ef4444'
              }}>
                {results.win_rate?.toFixed(1)}%
              </div>
            </div>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Total P&L
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: results.total_pnl >= 0 ? '#10b981' : '#ef4444'
              }}>
                {results.total_pnl >= 0 ? '+' : ''}${results.total_pnl?.toFixed(2)}
              </div>
            </div>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Return
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: results.total_return >= 0 ? '#10b981' : '#ef4444'
              }}>
                {results.total_return >= 0 ? '+' : ''}{results.total_return?.toFixed(2)}%
              </div>
            </div>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Max Drawdown
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: '#ef4444'
              }}>
                {results.max_drawdown?.toFixed(2)}%
              </div>
            </div>
            <div style={{
              padding: '1rem',
              backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
              borderRadius: '0.5rem',
              border: `1px solid ${colors.border}`,
              textAlign: 'center'
            }}>
              <div style={{ fontSize: '0.75rem', color: colors.textMuted, marginBottom: '0.25rem' }}>
                Sharpe Ratio
              </div>
              <div style={{
                fontSize: '1.5rem',
                fontWeight: '700',
                color: results.sharpe_ratio >= 1 ? '#10b981' : colors.text
              }}>
                {results.sharpe_ratio?.toFixed(2)}
              </div>
            </div>
          </div>

          {/* Equity Curve */}
          {renderEquityCurve()}

          {/* Trade Table */}
          {renderTradeTable()}
        </div>
      )}
    </div>
  );
}
