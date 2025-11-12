import React, { useState, useEffect } from 'react';

export function ControlPanel({ colors, API_BASE }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState({});
  const [tradingMode, setTradingMode] = useState('paper');
  const [positions, setPositions] = useState([]);

  // Fetch service status
  const fetchServices = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/services/list`);
      if (response.ok) {
        const data = await response.json();
        setServices(data.services || []);
      }
    } catch (error) {
      console.error('Error fetching services:', error);
    }
  };

  // Start a service
  const startService = async (name) => {
    setLoading(prev => ({ ...prev, [name]: true }));
    try {
      const response = await fetch(`${API_BASE}/api/services/${name}/start`, { method: 'POST' });
      if (response.ok) {
        const result = await response.json();
        console.log(`Service ${name} start result:`, result);
        // Wait a moment for service to fully start
        await new Promise(resolve => setTimeout(resolve, 1000));
        await fetchServices(); // Refresh to get actual status
      }
    } catch (error) {
      console.error(`Error starting ${name}:`, error);
      alert(`Failed to start ${name}. Check console for details.`);
    } finally {
      setLoading(prev => ({ ...prev, [name]: false }));
    }
  };

  // Stop a service
  const stopService = async (name) => {
    setLoading(prev => ({ ...prev, [name]: true }));
    try {
      const response = await fetch(`${API_BASE}/api/services/${name}/stop`, { method: 'POST' });
      if (response.ok) {
        const result = await response.json();
        console.log(`Service ${name} stop result:`, result);
        await new Promise(resolve => setTimeout(resolve, 500));
        await fetchServices(); // Refresh to get actual status
      }
    } catch (error) {
      console.error(`Error stopping ${name}:`, error);
      alert(`Failed to stop ${name}. Check console for details.`);
    } finally {
      setLoading(prev => ({ ...prev, [name]: false }));
    }
  };

  // Start all services
  const startAll = async () => {
    for (const service of services) {
      if (service.status !== 'running') {
        await startService(service.name);
        await new Promise(resolve => setTimeout(resolve, 500)); // Small delay between starts
      }
    }
  };

  // Stop all services
  const stopAll = async () => {
    if (!confirm('Stop all running services?')) return;

    for (const service of services) {
      if (service.status === 'running') {
        await stopService(service.name);
      }
    }
  };

  // Fetch open positions
  const fetchPositions = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/services/realistic_simulator/positions`);
      if (response.ok) {
        const data = await response.json();
        setPositions(data.positions || []);
      }
    } catch (error) {
      console.error('Error fetching positions:', error);
    }
  };

  useEffect(() => {
    fetchServices();
    fetchPositions();
    const interval = setInterval(() => {
      fetchServices();
      fetchPositions();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Display names and descriptions
  const serviceInfo = {
    'simulator': {
      displayName: 'Trade Simulator',
      description: 'Paper trading with virtual funds',
      icon: '📊'
    },
    'market_feed': {
      displayName: 'Market Data Feed',
      description: 'Real-time cryptocurrency prices from CoinGecko',
      icon: '📈'
    },
    'strategy_engine': {
      displayName: 'Strategy Engine',
      description: 'Technical analysis and trading signals (RSI, SMA, MACD)',
      icon: '🎯'
    },
    'analytics': {
      displayName: 'Analytics Engine',
      description: 'Performance tracking and trade analysis',
      icon: '📉'
    },
    'trading_bot': {
      displayName: 'Trading Bot',
      description: 'Automated trading (⚠️ disabled by default)',
      icon: '🤖'
    }
  };

  return (
    <div style={{ backgroundColor: colors.card, borderRadius: '0.5rem', padding: '1.5rem' }}>
      {/* Header with Trading Mode */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '1.5rem',
        paddingBottom: '1rem',
        borderBottom: `1px solid ${colors.border}`
      }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: '600', color: colors.text }}>
          🎮 Control Panel
        </h2>
        
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ color: colors.textMuted, fontSize: '0.875rem', marginRight: '0.5rem' }}>Trading Mode:</span>
          <button
            onClick={() => setTradingMode('paper')}
            style={{
              padding: '0.375rem 0.75rem',
              backgroundColor: tradingMode === 'paper' ? '#10b981' : colors.bg,
              color: tradingMode === 'paper' ? 'white' : colors.textMuted,
              border: `1px solid ${tradingMode === 'paper' ? '#10b981' : colors.border}`,
              borderRadius: '0.375rem 0 0 0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500'
            }}
          >
            📝 Paper
          </button>
          <button
            onClick={() => {
              if (confirm('⚠️ Live trading uses REAL MONEY. Are you sure?')) {
                setTradingMode('live');
              }
            }}
            style={{
              padding: '0.375rem 0.75rem',
              backgroundColor: tradingMode === 'live' ? '#dc2626' : colors.bg,
              color: tradingMode === 'live' ? 'white' : colors.textMuted,
              border: `1px solid ${tradingMode === 'live' ? '#dc2626' : colors.border}`,
              borderRadius: '0 0.375rem 0.375rem 0',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '500'
            }}
          >
            💰 Live
          </button>
        </div>
      </div>

      {/* Service Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
        {services.map(service => {
          const info = serviceInfo[service.name] || { 
            displayName: service.name, 
            description: 'Service',
            icon: '⚙️'
          };
          
          return (
            <div 
              key={service.name}
              style={{ 
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                padding: '1rem',
                backgroundColor: colors.bg
              }}
            >
              {/* Service Header */}
              <div style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                  <h3 style={{ color: colors.text, fontSize: '1rem', fontWeight: '600', margin: 0 }}>
                    {info.icon} {info.displayName}
                  </h3>
                  {service.auto_start && (
                    <span style={{ 
                      fontSize: '0.625rem', 
                      padding: '0.125rem 0.25rem',
                      backgroundColor: '#3b82f6',
                      color: 'white',
                      borderRadius: '0.25rem',
                      fontWeight: '500'
                    }}>
                      AUTO
                    </span>
                  )}
                </div>
                <p style={{ color: colors.textMuted, fontSize: '0.75rem', margin: 0 }}>
                  {info.description}
                </p>
              </div>

              {/* Status */}
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.5rem',
                marginBottom: '0.75rem'
              }}>
                <div style={{
                  width: '0.5rem',
                  height: '0.5rem',
                  borderRadius: '50%',
                  backgroundColor: service.status === 'running' ? '#10b981' : '#6b7280'
                }} />
                <span style={{ 
                  color: service.status === 'running' ? '#10b981' : colors.textMuted,
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}>
                  {service.status === 'running' ? 'Running' : 'Stopped'}
                </span>
              </div>

              {/* Buttons */}
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                {service.status !== 'running' ? (
                  <button
                    onClick={() => startService(service.name)}
                    disabled={loading[service.name]}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      backgroundColor: loading[service.name] ? '#6b7280' : '#10b981',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: loading[service.name] ? 'not-allowed' : 'pointer',
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      transition: 'background-color 0.2s'
                    }}
                  >
                    {loading[service.name] ? '⏳ Starting...' : '▶ START'}
                  </button>
                ) : (
                  <button
                    onClick={() => stopService(service.name)}
                    disabled={loading[service.name]}
                    style={{
                      width: '100%',
                      padding: '0.5rem',
                      backgroundColor: loading[service.name] ? '#6b7280' : '#dc2626',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: loading[service.name] ? 'not-allowed' : 'pointer',
                      fontSize: '0.875rem',
                      fontWeight: '600',
                      transition: 'background-color 0.2s'
                    }}
                  >
                    {loading[service.name] ? '⏳ Stopping...' : '⏹ STOP'}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Actions - Simplified */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between',
        paddingTop: '1rem',
        borderTop: `1px solid ${colors.border}`
      }}>
        <button
          onClick={startAll}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#3b82f6',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '600'
          }}
        >
          🚀 Start All Services
        </button>
        
        <button
          onClick={stopAll}
          style={{
            padding: '0.5rem 1rem',
            backgroundColor: '#dc2626',
            color: 'white',
            border: 'none',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
            fontWeight: '700'
          }}
        >
          ⏹ Stop All Services
        </button>
      </div>

      {/* Open Positions Section */}
      <div style={{
        marginTop: '1.5rem',
        paddingTop: '1.5rem',
        borderTop: `1px solid ${colors.border}`
      }}>
        <h3 style={{
          fontSize: '1.125rem',
          fontWeight: '600',
          color: colors.text,
          marginBottom: '1rem'
        }}>
          📊 Open Positions ({positions.length})
        </h3>

        {positions.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {positions.map((pos, index) => {
              const pnlColor = pos.unrealized_pnl >= 0 ? '#10b981' : '#ef4444';
              const pnlPercentage = ((pos.unrealized_pnl / pos.position_value) * 100).toFixed(2);

              return (
                <div
                  key={index}
                  style={{
                    border: `1px solid ${colors.border}`,
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    backgroundColor: colors.bg
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    marginBottom: '0.75rem'
                  }}>
                    {/* Left: Symbol and Side */}
                    <div>
                      <h4 style={{
                        fontSize: '1.125rem',
                        fontWeight: '700',
                        color: colors.text,
                        margin: 0,
                        marginBottom: '0.25rem'
                      }}>
                        {pos.symbol}
                        <span style={{
                          marginLeft: '0.5rem',
                          fontSize: '0.875rem',
                          padding: '0.125rem 0.5rem',
                          borderRadius: '0.25rem',
                          backgroundColor: pos.side === 'LONG' ? '#10b981' : '#ef4444',
                          color: 'white',
                          fontWeight: '600'
                        }}>
                          {pos.side}
                        </span>
                      </h4>
                      <p style={{
                        fontSize: '0.75rem',
                        color: colors.textMuted,
                        margin: 0
                      }}>
                        Strategy: {pos.strategy}
                      </p>
                    </div>

                    {/* Right: P&L */}
                    <div style={{ textAlign: 'right' }}>
                      <div style={{
                        fontSize: '1.25rem',
                        fontWeight: '700',
                        color: pnlColor
                      }}>
                        {pos.unrealized_pnl >= 0 ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                      </div>
                      <div style={{
                        fontSize: '0.875rem',
                        color: pnlColor,
                        fontWeight: '600'
                      }}>
                        ({pnlPercentage >= 0 ? '+' : ''}{pnlPercentage}%)
                      </div>
                    </div>
                  </div>

                  {/* Position Details Grid */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '0.75rem',
                    fontSize: '0.875rem'
                  }}>
                    <div>
                      <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>Entry Price</div>
                      <div style={{ color: colors.text, fontWeight: '600' }}>
                        ${pos.entry_price.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>Quantity</div>
                      <div style={{ color: colors.text, fontWeight: '600' }}>
                        {pos.quantity.toFixed(4)}
                      </div>
                    </div>
                    <div>
                      <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>Position Value</div>
                      <div style={{ color: colors.text, fontWeight: '600' }}>
                        ${pos.position_value.toFixed(2)}
                      </div>
                    </div>
                  </div>

                  {/* Risk Management */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '0.75rem',
                    marginTop: '0.75rem',
                    fontSize: '0.875rem'
                  }}>
                    {pos.stop_loss && (
                      <div>
                        <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>Stop Loss</div>
                        <div style={{ color: '#ef4444', fontWeight: '600' }}>
                          ${pos.stop_loss.toFixed(2)}
                        </div>
                      </div>
                    )}
                    {pos.take_profit && (
                      <div>
                        <div style={{ color: colors.textMuted, fontSize: '0.75rem' }}>Take Profit</div>
                        <div style={{ color: '#10b981', fontWeight: '600' }}>
                          ${pos.take_profit.toFixed(2)}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Entry Time */}
                  <div style={{
                    marginTop: '0.75rem',
                    paddingTop: '0.75rem',
                    borderTop: `1px solid ${colors.border}`,
                    fontSize: '0.75rem',
                    color: colors.textMuted
                  }}>
                    Opened: {new Date(pos.entry_time).toLocaleString()}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{
            padding: '2rem',
            textAlign: 'center',
            color: colors.textMuted,
            backgroundColor: colors.bg,
            borderRadius: '0.5rem',
            border: `1px dashed ${colors.border}`
          }}>
            <p style={{ margin: 0 }}>No open positions</p>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.875rem' }}>
              Start the realistic_simulator service to see live positions
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
