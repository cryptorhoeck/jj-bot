import React, { useState, useEffect } from 'react';

export function MarketChart({ colors, darkMode, API_BASE }) {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC');
  const [timeframe, setTimeframe] = useState('1h');
  const [marketData, setMarketData] = useState([]);
  const [priceData, setPriceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];

  // Fetch market overview data
  const fetchMarketData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/live`);
      if (response.ok) {
        const data = await response.json();
        setMarketData(data.prices || []);
      }
    } catch (error) {
      console.error('Error fetching market data:', error);
    }
  };

  // Fetch price data for selected symbol
  const fetchPriceData = async (symbol) => {
    setLoading(true);
    try {
      // For now, we'll generate sample price movement
      // In a real implementation, this would fetch historical OHLCV data
      const mockPriceData = generateMockPriceData(100);
      setPriceData(mockPriceData);
    } catch (error) {
      console.error('Error fetching price data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Generate mock price data for demo
  const generateMockPriceData = (points) => {
    const data = [];
    let basePrice = marketData.find(m => m.symbol === selectedSymbol)?.price || 45000;
    let currentPrice = basePrice;

    for (let i = 0; i < points; i++) {
      const change = (Math.random() - 0.5) * (basePrice * 0.02);
      currentPrice += change;
      data.push({
        timestamp: Date.now() - (points - i) * 60000,
        price: currentPrice,
        high: currentPrice * 1.01,
        low: currentPrice * 0.99,
        volume: Math.random() * 1000000
      });
    }

    return data;
  };

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedSymbol) {
      fetchPriceData(selectedSymbol);
    }
  }, [selectedSymbol, timeframe]);

  // Render price chart
  const renderPriceChart = () => {
    if (!priceData || priceData.length === 0) {
      return <div style={{ textAlign: 'center', padding: '3rem', color: colors.textMuted }}>
        Loading chart data...
      </div>;
    }

    const prices = priceData.map(d => d.price);
    const maxPrice = Math.max(...prices);
    const minPrice = Math.min(...prices);
    const priceRange = maxPrice - minPrice || 1;

    const width = 1000;
    const height = 400;
    const padding = 40;
    const chartWidth = width - (padding * 2);
    const chartHeight = height - (padding * 2);

    return (
      <div style={{ position: 'relative', height: '400px', backgroundColor: darkMode ? '#0a0a0a' : '#ffffff' }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((percent, i) => (
            <g key={i}>
              <line
                x1={padding}
                y1={padding + (chartHeight * percent)}
                x2={width - padding}
                y2={padding + (chartHeight * percent)}
                stroke={darkMode ? '#1f1f1f' : '#e5e7eb'}
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={padding - 5}
                y={padding + (chartHeight * percent) + 4}
                textAnchor="end"
                fill={colors.textMuted}
                fontSize="11"
              >
                ${(minPrice + (priceRange * (1 - percent))).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </text>
            </g>
          ))}

          {/* Price line */}
          <polyline
            points={priceData.map((point, index) => {
              const x = padding + (index / (priceData.length - 1)) * chartWidth;
              const y = padding + chartHeight - ((point.price - minPrice) / priceRange) * chartHeight;
              return `${x},${y}`;
            }).join(' ')}
            fill="none"
            stroke="#3b82f6"
            strokeWidth="2"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {/* Fill area under line */}
          <polygon
            points={
              `${padding},${padding + chartHeight} ` +
              priceData.map((point, index) => {
                const x = padding + (index / (priceData.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((point.price - minPrice) / priceRange) * chartHeight;
                return `${x},${y}`;
              }).join(' ') +
              ` ${width - padding},${padding + chartHeight}`
            }
            fill="url(#priceGradient)"
            opacity="0.3"
          />

          {/* Gradient definition */}
          <defs>
            <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>

        {/* Current price indicator */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '60px',
          padding: '0.5rem 1rem',
          backgroundColor: darkMode ? '#1f1f1f' : '#f9fafb',
          border: `1px solid ${colors.border}`,
          borderRadius: '0.375rem'
        }}>
          <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
            {selectedSymbol}/USD
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: '700', color: colors.text }}>
            ${priceData[priceData.length - 1].price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#10b981' }}>
            +2.45%
          </div>
        </div>
      </div>
    );
  };

  // Filter market data by search term
  const filteredMarketData = marketData.filter(m =>
    m.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', gap: '1rem', height: 'calc(100vh - 200px)' }}>
      {/* Left Sidebar - Symbol List */}
      <div style={{
        width: '250px',
        backgroundColor: colors.card,
        borderRadius: '0.5rem',
        padding: '1rem',
        overflowY: 'auto'
      }}>
        <input
          type="text"
          placeholder="Search symbol..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{
            width: '100%',
            padding: '0.5rem',
            marginBottom: '1rem',
            backgroundColor: darkMode ? '#1a1a1a' : '#f9fafb',
            border: `1px solid ${colors.border}`,
            borderRadius: '0.375rem',
            color: colors.text,
            fontSize: '0.875rem'
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
          {filteredMarketData.slice(0, 20).map((coin) => (
            <button
              key={coin.symbol}
              onClick={() => setSelectedSymbol(coin.symbol)}
              style={{
                padding: '0.75rem',
                backgroundColor: selectedSymbol === coin.symbol
                  ? (darkMode ? '#1f2937' : '#e5e7eb')
                  : 'transparent',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background-color 0.2s'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontWeight: '600', color: colors.text }}>{coin.symbol}</span>
                <span style={{ fontSize: '0.875rem', color: coin.change_24h >= 0 ? '#10b981' : '#ef4444' }}>
                  {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(2)}%
                </span>
              </div>
              <div style={{ fontSize: '0.875rem', color: colors.textMuted }}>
                ${coin.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Main Chart Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {/* Toolbar */}
        <div style={{
          backgroundColor: colors.card,
          borderRadius: '0.5rem',
          padding: '1rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          {/* Timeframe selector */}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                style={{
                  padding: '0.375rem 0.75rem',
                  backgroundColor: timeframe === tf ? '#3b82f6' : 'transparent',
                  color: timeframe === tf ? 'white' : colors.text,
                  border: `1px solid ${timeframe === tf ? '#3b82f6' : colors.border}`,
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  fontSize: '0.875rem',
                  fontWeight: '500'
                }}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Indicators */}
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.875rem', color: colors.textMuted }}>Indicators:</span>
            <button style={{
              padding: '0.375rem 0.75rem',
              backgroundColor: 'transparent',
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}>
              MA
            </button>
            <button style={{
              padding: '0.375rem 0.75rem',
              backgroundColor: 'transparent',
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}>
              RSI
            </button>
            <button style={{
              padding: '0.375rem 0.75rem',
              backgroundColor: 'transparent',
              color: colors.text,
              border: `1px solid ${colors.border}`,
              borderRadius: '0.375rem',
              cursor: 'pointer',
              fontSize: '0.875rem'
            }}>
              MACD
            </button>
          </div>
        </div>

        {/* Chart */}
        <div style={{
          flex: 1,
          backgroundColor: colors.card,
          borderRadius: '0.5rem',
          overflow: 'hidden'
        }}>
          {renderPriceChart()}
        </div>

        {/* Volume Chart */}
        <div style={{
          height: '100px',
          backgroundColor: colors.card,
          borderRadius: '0.5rem',
          padding: '1rem'
        }}>
          {priceData && (
            <div style={{ display: 'flex', alignItems: 'flex-end', height: '100%', gap: '2px' }}>
              {priceData.map((point, index) => {
                const maxVolume = Math.max(...priceData.map(p => p.volume));
                const height = (point.volume / maxVolume) * 100;
                return (
                  <div
                    key={index}
                    style={{
                      flex: 1,
                      height: `${height}%`,
                      backgroundColor: index > 0 && point.price > priceData[index - 1].price
                        ? '#10b981'
                        : '#ef4444',
                      opacity: 0.6,
                      borderRadius: '2px 2px 0 0'
                    }}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
