import React, { useState, useEffect } from 'react';

export function ControlPanel({ colors, API_BASE }) {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState({});
  const [tradingMode, setTradingMode] = useState('paper');
  const [positions, setPositions] = useState([]);
  const [showBackgroundServices, setShowBackgroundServices] = useState(false);
  const [streamStatus, setStreamStatus] = useState(null);
  const [streamLoading, setStreamLoading] = useState(false);

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
        await new Promise(resolve => setTimeout(resolve, 1000));
        await fetchServices();
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
        await new Promise(resolve => setTimeout(resolve, 500));
        await fetchServices();
      }
    } catch (error) {
      console.error(`Error stopping ${name}:`, error);
      alert(`Failed to stop ${name}. Check console for details.`);
    } finally {
      setLoading(prev => ({ ...prev, [name]: false }));
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

  // Fetch WebSocket stream status
  const fetchStreamStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stream/status`);
      if (response.ok) {
        const data = await response.json();
        setStreamStatus(data.status);
      }
    } catch (error) {
      console.error('Error fetching stream status:', error);
    }
  };

  // Start WebSocket stream
  const startStream = async () => {
    setStreamLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/stream/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOGE', 'AVAX', 'DOT', 'MATIC'],
          exchange: 'kraken'
        })
      });
      if (response.ok) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        await fetchStreamStatus();
      } else {
        alert('Failed to start stream. Check console for details.');
      }
    } catch (error) {
      console.error('Error starting stream:', error);
      alert('Failed to start stream. Check console for details.');
    } finally {
      setStreamLoading(false);
    }
  };

  // Stop WebSocket stream
  const stopStream = async () => {
    setStreamLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/stream/stop`, { method: 'POST' });
      if (response.ok) {
        await new Promise(resolve => setTimeout(resolve, 500));
        await fetchStreamStatus();
      }
    } catch (error) {
      console.error('Error stopping stream:', error);
    } finally {
      setStreamLoading(false);
    }
  };

  useEffect(() => {
    fetchServices();
    fetchPositions();
    fetchStreamStatus();
    const interval = setInterval(() => {
      fetchServices();
      fetchPositions();
      fetchStreamStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Get specific services
  const simulator = services.find(s => s.name === 'realistic_simulator');
  const backgroundServices = services.filter(s =>
    s.name !== 'realistic_simulator' && s.name !== 'simulator' && s.name !== 'market_feed'
  );

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

      {/* Bot Control Link */}
      <div style={{
        border: `2px solid ${colors.border}`,
        borderRadius: '0.75rem',
        padding: '1.5rem',
        backgroundColor: colors.card,
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h3 style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.text, margin: 0, marginBottom: '0.25rem' }}>
              🤖 Trading Bot
            </h3>
            <p style={{ fontSize: '0.875rem', color: colors.textMuted, margin: 0 }}>
              Control bot trading, configure settings, and monitor performance
            </p>
          </div>
          <button
            onClick={() => window.location.href = '#'}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              cursor: 'pointer',
              fontSize: '0.875rem',
              fontWeight: '600',
              transition: 'background-color 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#2563eb'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#3b82f6'}
          >
            Go to Bot Tab →
          </button>
        </div>
      </div>

      {/* Real-Time Market Stream */}
      <div style={{
        backgroundColor: colors.card,
        border: `1px solid ${colors.border}`,
        borderRadius: '0.5rem',
        padding: '1rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.25rem' }}>📡</span>
            <h3 style={{ fontSize: '1rem', fontWeight: '600', color: colors.text, margin: 0 }}>
              Real-Time Market Stream
            </h3>
          </div>
          <div style={{
            padding: '0.25rem 0.625rem',
            borderRadius: '0.25rem',
            fontSize: '0.75rem',
            fontWeight: '600',
            backgroundColor: streamStatus?.running ? 'rgba(16, 185, 129, 0.1)' : 'rgba(156, 163, 175, 0.1)',
            color: streamStatus?.running ? '#10b981' : '#6b7280',
            border: `1px solid ${streamStatus?.running ? '#10b981' : '#6b7280'}`
          }}>
            {streamStatus?.running ? '● STREAMING' : '○ OFFLINE'}
          </div>
        </div>

        <div style={{ fontSize: '0.875rem', color: colors.textMuted, marginBottom: '1rem' }}>
          {streamStatus?.running ? (
            <>
              Live prices from <strong>{streamStatus.exchange || 'Kraken'}</strong> WebSocket
              {streamStatus.stream_stats?.price_updates > 0 && (
                <> • {streamStatus.stream_stats.price_updates.toLocaleString()} updates received</>
              )}
            </>
          ) : (
            'Connect to Kraken or Binance for real-time price updates'
          )}
        </div>

        {streamStatus?.running && streamStatus.symbols && streamStatus.symbols.length > 0 && (
          <div style={{
            backgroundColor: colors.bg,
            padding: '0.75rem',
            borderRadius: '0.375rem',
            marginBottom: '1rem',
            fontSize: '0.75rem'
          }}>
            <div style={{ color: colors.textMuted, marginBottom: '0.25rem' }}>Subscribed Symbols:</div>
            <div style={{ color: colors.text, fontWeight: '500' }}>
              {streamStatus.symbols.join(', ')}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            onClick={streamStatus?.running ? stopStream : startStream}
            disabled={streamLoading}
            style={{
              flex: 1,
              padding: '0.625rem 1rem',
              backgroundColor: streamStatus?.running ? '#ef4444' : '#10b981',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: streamLoading ? 'not-allowed' : 'pointer',
              fontWeight: '600',
              fontSize: '0.875rem',
              opacity: streamLoading ? 0.5 : 1,
              transition: 'all 0.15s'
            }}
            onMouseEnter={(e) => {
              if (!streamLoading) {
                e.currentTarget.style.opacity = '0.9';
                e.currentTarget.style.transform = 'translateY(-1px)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = '1';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            {streamLoading ? 'Loading...' : (streamStatus?.running ? '⏹ Stop Stream' : '▶ Start Stream')}
          </button>

          {streamStatus?.running && (
            <button
              onClick={() => window.open(`${API_BASE}/api/stream/status`, '_blank')}
              style={{
                padding: '0.625rem 1rem',
                backgroundColor: colors.bg,
                color: colors.text,
                border: `1px solid ${colors.border}`,
                borderRadius: '0.375rem',
                cursor: 'pointer',
                fontWeight: '600',
                fontSize: '0.875rem',
                transition: 'all 0.15s'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = colors.border;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = colors.bg;
              }}
            >
              📊 Stats
            </button>
          )}
        </div>

        {!streamStatus?.running && (
          <div style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderRadius: '0.375rem',
            border: '1px solid #3b82f6',
            fontSize: '0.75rem',
            color: '#3b82f6'
          }}>
            💡 <strong>Tip:</strong> Enable real-time streaming for live price updates with zero API calls
          </div>
        )}
      </div>

      {/* Collapsible Background Services */}
      {backgroundServices.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <button
            onClick={() => setShowBackgroundServices(!showBackgroundServices)}
            style={{
              width: '100%',
              padding: '0.75rem',
              backgroundColor: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.5rem',
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              color: colors.text,
              fontSize: '0.875rem',
              fontWeight: '600'
            }}
          >
            <span>⚙️ Background Services ({backgroundServices.length})</span>
            <span style={{ fontSize: '1rem' }}>{showBackgroundServices ? '▼' : '▶'}</span>
          </button>

          {showBackgroundServices && (
            <div style={{
              marginTop: '0.5rem',
              padding: '1rem',
              backgroundColor: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.5rem'
            }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {backgroundServices.map(service => {
                  const icons = {
                    'strategy_engine': '🎯',
                    'analytics': '📊',
                    'trading_bot': '🤖'
                  };
                  const names = {
                    'strategy_engine': 'Strategy Engine',
                    'analytics': 'Analytics',
                    'trading_bot': 'Trading Bot'
                  };

                  return (
                    <div
                      key={service.name}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        padding: '0.75rem',
                        backgroundColor: colors.card,
                        borderRadius: '0.375rem',
                        border: `1px solid ${colors.border}`
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
                        <span style={{ fontSize: '1.25rem' }}>{icons[service.name] || '⚙️'}</span>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span style={{ color: colors.text, fontWeight: '600', fontSize: '0.875rem' }}>
                              {names[service.name] || service.name}
                            </span>
                            {service.auto_start && (
                              <span style={{
                                fontSize: '0.625rem',
                                padding: '0.125rem 0.375rem',
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                borderRadius: '0.25rem',
                                fontWeight: '500'
                              }}>
                                AUTO
                              </span>
                            )}
                          </div>
                          <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
                            {service.auto_start ? 'Starts automatically on API boot' : 'Manual start only'}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{
                            width: '0.5rem',
                            height: '0.5rem',
                            borderRadius: '50%',
                            backgroundColor: service.status === 'running' ? '#10b981' : '#6b7280'
                          }} />
                          <span style={{
                            fontSize: '0.75rem',
                            fontWeight: '600',
                            color: service.status === 'running' ? '#10b981' : colors.textMuted
                          }}>
                            {service.status === 'running' ? 'Running' : 'Stopped'}
                          </span>
                        </div>
                        {service.status !== 'running' ? (
                          <button
                            onClick={() => startService(service.name)}
                            disabled={loading[service.name]}
                            style={{
                              padding: '0.375rem 0.75rem',
                              backgroundColor: loading[service.name] ? '#6b7280' : '#10b981',
                              color: 'white',
                              border: 'none',
                              borderRadius: '0.25rem',
                              cursor: loading[service.name] ? 'not-allowed' : 'pointer',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              transition: 'background-color 0.2s'
                            }}
                          >
                            {loading[service.name] ? '...' : '▶ Start'}
                          </button>
                        ) : (
                          <button
                            onClick={() => stopService(service.name)}
                            disabled={loading[service.name]}
                            style={{
                              padding: '0.375rem 0.75rem',
                              backgroundColor: loading[service.name] ? '#6b7280' : '#dc2626',
                              color: 'white',
                              border: 'none',
                              borderRadius: '0.25rem',
                              cursor: loading[service.name] ? 'not-allowed' : 'pointer',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              transition: 'background-color 0.2s'
                            }}
                          >
                            {loading[service.name] ? '...' : '⏹ Stop'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
              <div style={{
                marginTop: '0.75rem',
                padding: '0.75rem',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                borderRadius: '0.375rem',
                border: '1px solid rgba(59, 130, 246, 0.3)',
                fontSize: '0.75rem',
                color: colors.text
              }}>
                {backgroundServices.filter(s => s.auto_start).every(s => s.status === 'running') ? (
                  <>✅ All auto-start services are running. Manual services can be started on-demand.</>
                ) : backgroundServices.filter(s => s.auto_start).length > 0 ? (
                  <>⚠️ Some auto-start services are stopped. They'll restart when you reboot the API server.</>
                ) : (
                  <>ℹ️ Background services support the Trading Simulator. Use Start/Stop buttons to control them manually.</>
                )}
              </div>
            </div>
          )}
        </div>
      )}

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
            <p style={{ margin: 0, fontSize: '1rem' }}>No open positions</p>
            <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.875rem' }}>
              {simulator?.status === 'running'
                ? 'Waiting for trading signals...'
                : 'Start the Trading Simulator to see live positions'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
