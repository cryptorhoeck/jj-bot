// Module System Tab Component
import React from 'react';

export function ModuleTab({ colors, API_BASE }) {
  const [moduleStatus, setModuleStatus] = React.useState(null);
  const [modulePrices, setModulePrices] = React.useState(null);
  const [signals, setSignals] = React.useState(null);
  const [portfolio, setPortfolio] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  // Fetch module data
  const fetchModuleData = async () => {
    try {
      const [statusRes, pricesRes, signalsRes, portfolioRes] = await Promise.all([
        fetch(`${API_BASE}/api/modules/status`),
        fetch(`${API_BASE}/api/modules/prices`),
        fetch(`${API_BASE}/api/modules/signals`),
        fetch(`${API_BASE}/api/modules/portfolio`)
      ]);

      const status = await statusRes.json();
      const prices = await pricesRes.json();
      const sigs = await signalsRes.json();
      const port = await portfolioRes.json();

      setModuleStatus(status);
      setModulePrices(prices);
      setSignals(sigs);
      setPortfolio(port);
    } catch (error) {
      console.error('Error fetching module data:', error);
    }
  };

  // Start/stop modules
  const toggleModules = async () => {
    setLoading(true);
    const running = moduleStatus?.running;
    const endpoint = running ? '/api/modules/stop' : '/api/modules/start';
    
    try {
      const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      const data = await response.json();
      alert(data.message);
      setTimeout(fetchModuleData, 2000);
    } catch (error) {
      alert('Error: ' + error);
    }
    setLoading(false);
  };

  React.useEffect(() => {
    fetchModuleData();
    const interval = setInterval(fetchModuleData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!moduleStatus) {
    return (
      <div style={{ backgroundColor: colors.card, borderRadius: '0.5rem', padding: '1.5rem' }}>
        <h2 style={{ color: colors.text }}>Loading modules...</h2>
      </div>
    );
  }

  return (
    <div style={{ backgroundColor: colors.card, borderRadius: '0.5rem', padding: '1.5rem' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: colors.text }}>
        🤖 Trading Modules
      </h2>

      {/* Module Control */}
      <div style={{ marginBottom: '2rem' }}>
        <button
          onClick={toggleModules}
          disabled={loading}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: moduleStatus?.running ? '#ef4444' : '#10b981',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {moduleStatus?.running ? 'Stop Modules' : 'Start Modules'}
        </button>
        {moduleStatus?.running && (
          <span style={{ marginLeft: '1rem', color: '#10b981' }}>
            ✅ Modules Running
          </span>
        )}
      </div>

      {/* Module Stats */}
      {moduleStatus?.running && modulePrices && (
        <div>
          {/* Portfolio */}
          {portfolio && (
            <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: colors.bg, borderRadius: '0.5rem' }}>
              <h3 style={{ color: colors.text, marginBottom: '0.5rem' }}>Portfolio</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
                <div>
                  <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Balance</div>
                  <div style={{ color: colors.text }}>${portfolio.balance?.toFixed(2) || '10000.00'}</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>P&L</div>
                  <div style={{ color: portfolio.total_pnl >= 0 ? '#10b981' : '#ef4444' }}>
                    ${portfolio.total_pnl?.toFixed(2) || '0.00'}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Win Rate</div>
                  <div style={{ color: colors.text }}>{((portfolio.win_rate || 0.5) * 100).toFixed(1)}%</div>
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>Positions</div>
                  <div style={{ color: colors.text }}>{portfolio.open_positions || 0}</div>
                </div>
              </div>
            </div>
          )}

          {/* Market Summary */}
          {modulePrices?.summary && (
            <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: colors.bg, borderRadius: '0.5rem' }}>
              <h3 style={{ color: colors.text, marginBottom: '0.5rem' }}>Market Summary</h3>
              <p style={{ color: colors.textMuted }}>
                Tracking {modulePrices.summary.coins_tracked} coins | 
                Avg 24h Change: {modulePrices.summary.average_change_24h?.toFixed(2)}%
              </p>
            </div>
          )}

          {/* Top Movers */}
          {modulePrices?.movers && (
            <div style={{ marginBottom: '2rem' }}>
              <h3 style={{ color: colors.text, marginBottom: '0.5rem' }}>Top Movers</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div>
                  <h4 style={{ color: '#10b981', fontSize: '0.875rem' }}>🚀 Gainers</h4>
                  {(modulePrices.movers.gainers || []).slice(0, 3).map((coin, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem' }}>
                      <span style={{ color: colors.text }}>{coin.symbol}</span>
                      <span style={{ color: '#10b981' }}>+{coin.change_24h?.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
                <div>
                  <h4 style={{ color: '#ef4444', fontSize: '0.875rem' }}>📉 Losers</h4>
                  {(modulePrices.movers.losers || []).slice(0, 3).map((coin, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem' }}>
                      <span style={{ color: colors.text }}>{coin.symbol}</span>
                      <span style={{ color: '#ef4444' }}>{coin.change_24h?.toFixed(2)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!moduleStatus?.running && (
        <p style={{ color: colors.textMuted }}>
          Click "Start Modules" to begin tracking top 20 cryptocurrencies and generating trading signals.
        </p>
      )}
    </div>
  );
}
