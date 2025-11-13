import React, { useState, useEffect } from 'react';

export function MarketChart({ colors, darkMode, API_BASE }) {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC');
  const [timeframe, setTimeframe] = useState('1h');
  const [marketData, setMarketData] = useState([]);
  const [priceData, setPriceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [favorites, setFavorites] = useState(['BTC', 'ETH', 'SOL', 'BNB']);
  const [activeTab, setActiveTab] = useState('favorites'); // 'favorites' or 'all'

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

  // Toggle favorite
  const toggleFavorite = (symbol) => {
    setFavorites(prev =>
      prev.includes(symbol)
        ? prev.filter(s => s !== symbol)
        : [...prev, symbol]
    );
  };

  // Fetch price data for selected symbol
  const fetchPriceData = async (symbol) => {
    setLoading(true);
    try {
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

  // Render symbol in list
  const renderSymbolItem = (coin, isFavorite = false) => {
    const isSelected = selectedSymbol === coin.symbol;

    return (
      <div
        key={coin.symbol}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          padding: '0.5rem 0.75rem',
          backgroundColor: isSelected
            ? (darkMode ? '#1e293b' : '#dbeafe')
            : 'transparent',
          borderRadius: '0.25rem',
          cursor: 'pointer',
          transition: 'background-color 0.15s',
          borderLeft: isSelected ? '3px solid #3b82f6' : '3px solid transparent'
        }}
        onMouseEnter={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = darkMode ? '#1e293b20' : '#f1f5f9';
          }
        }}
        onMouseLeave={(e) => {
          if (!isSelected) {
            e.currentTarget.style.backgroundColor = 'transparent';
          }
        }}
      >
        <button
          onClick={(e) => {
            e.stopPropagation();
            toggleFavorite(coin.symbol);
          }}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: 0,
            fontSize: '1rem',
            color: isFavorite ? '#fbbf24' : colors.textMuted,
            transition: 'color 0.2s'
          }}
        >
          {isFavorite ? '★' : '☆'}
        </button>

        <div
          onClick={() => setSelectedSymbol(coin.symbol)}
          style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          <div>
            <div style={{ fontWeight: '600', color: colors.text, fontSize: '0.875rem' }}>
              {coin.symbol}
            </div>
            <div style={{ fontSize: '0.75rem', color: colors.textMuted }}>
              ${coin.price?.toLocaleString(undefined, { maximumFractionDigits: 2 })}
            </div>
          </div>

          <div style={{
            fontSize: '0.75rem',
            fontWeight: '600',
            color: coin.change_24h >= 0 ? '#10b981' : '#ef4444',
            textAlign: 'right'
          }}>
            {coin.change_24h >= 0 ? '+' : ''}{coin.change_24h?.toFixed(2)}%
          </div>
        </div>
      </div>
    );
  };

  // Render price chart
  const renderPriceChart = () => {
    if (!priceData || priceData.length === 0) {
      return <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: colors.textMuted
      }}>
        Loading chart data...
      </div>;
    }

    const prices = priceData.map(d => d.price);
    const maxPrice = Math.max(...prices);
    const minPrice = Math.min(...prices);
    const priceRange = maxPrice - minPrice || 1;
    const currentPrice = priceData[priceData.length - 1].price;
    const priceChange = ((currentPrice - priceData[0].price) / priceData[0].price) * 100;

    const width = 1000;
    const height = 450;
    const padding = 60;
    const chartWidth = width - (padding * 2);
    const chartHeight = height - (padding * 2);

    return (
      <div style={{ position: 'relative', height: '100%', backgroundColor: darkMode ? '#0f172a' : '#ffffff' }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((percent, i) => (
            <g key={i}>
              <line
                x1={padding}
                y1={padding + (chartHeight * percent)}
                x2={width - padding}
                y2={padding + (chartHeight * percent)}
                stroke={darkMode ? '#1e293b' : '#e2e8f0'}
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
              <text
                x={width - padding + 5}
                y={padding + (chartHeight * percent) + 4}
                textAnchor="start"
                fill={colors.textMuted}
                fontSize="11"
              >
                ${(minPrice + (priceRange * (1 - percent))).toLocaleString(undefined, { maximumFractionDigits: 2 })}
              </text>
            </g>
          ))}

          {/* Vertical grid lines */}
          {[0, 0.2, 0.4, 0.6, 0.8, 1].map((percent, i) => (
            <line
              key={`v${i}`}
              x1={padding + (chartWidth * percent)}
              y1={padding}
              x2={padding + (chartWidth * percent)}
              y2={height - padding}
              stroke={darkMode ? '#1e293b' : '#e2e8f0'}
              strokeWidth="1"
              vectorEffect="non-scaling-stroke"
            />
          ))}

          {/* Price line */}
          <polyline
            points={priceData.map((point, index) => {
              const x = padding + (index / (priceData.length - 1)) * chartWidth;
              const y = padding + chartHeight - ((point.price - minPrice) / priceRange) * chartHeight;
              return `${x},${y}`;
            }).join(' ')}
            fill="none"
            stroke={priceChange >= 0 ? '#10b981' : '#ef4444'}
            strokeWidth="2"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {/* Fill area under line */}
          <polygon
            points={
              `${padding},${height - padding} ` +
              priceData.map((point, index) => {
                const x = padding + (index / (priceData.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((point.price - minPrice) / priceRange) * chartHeight;
                return `${x},${y}`;
              }).join(' ') +
              ` ${width - padding},${height - padding}`
            }
            fill={`url(#priceGradient${priceChange >= 0 ? 'Green' : 'Red'})`}
            opacity="0.1"
          />

          {/* Gradient definitions */}
          <defs>
            <linearGradient id="priceGradientGreen" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="priceGradientRed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ef4444" stopOpacity="0.5" />
              <stop offset="100%" stopColor="#ef4444" stopOpacity="0" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    );
  };

  // Filter market data
  const filteredMarketData = marketData.filter(m =>
    m.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
    m.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const favoriteCoins = marketData.filter(m => favorites.includes(m.symbol));
  const displayCoins = activeTab === 'favorites' ? favoriteCoins : filteredMarketData;
  const currentCoin = marketData.find(m => m.symbol === selectedSymbol);

  return (
    <div style={{
      display: 'flex',
      gap: '0',
      height: 'calc(100vh - 180px)',
      backgroundColor: darkMode ? '#0f172a' : '#f8fafc'
    }}>
      {/* Left Sidebar - TradingView Style */}
      <div style={{
        width: '280px',
        backgroundColor: darkMode ? '#1e293b' : '#ffffff',
        borderRight: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Search */}
        <div style={{ padding: '1rem', borderBottom: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}` }}>
          <input
            type="text"
            placeholder="Search markets"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '0.625rem',
              backgroundColor: darkMode ? '#0f172a' : '#f1f5f9',
              border: `1px solid ${darkMode ? '#334155' : '#cbd5e1'}`,
              borderRadius: '0.375rem',
              color: colors.text,
              fontSize: '0.875rem',
              outline: 'none'
            }}
          />
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          borderBottom: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
          backgroundColor: darkMode ? '#1e293b' : '#ffffff'
        }}>
          <button
            onClick={() => setActiveTab('favorites')}
            style={{
              flex: 1,
              padding: '0.75rem',
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'favorites' ? `2px solid #3b82f6` : '2px solid transparent',
              color: activeTab === 'favorites' ? '#3b82f6' : colors.textMuted,
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            ★ Favorites ({favorites.length})
          </button>
          <button
            onClick={() => setActiveTab('all')}
            style={{
              flex: 1,
              padding: '0.75rem',
              backgroundColor: 'transparent',
              border: 'none',
              borderBottom: activeTab === 'all' ? `2px solid #3b82f6` : '2px solid transparent',
              color: activeTab === 'all' ? '#3b82f6' : colors.textMuted,
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            All Markets
          </button>
        </div>

        {/* Symbol List */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '0.5rem'
        }}>
          {displayCoins.length === 0 ? (
            <div style={{
              padding: '2rem 1rem',
              textAlign: 'center',
              color: colors.textMuted,
              fontSize: '0.875rem'
            }}>
              {activeTab === 'favorites'
                ? 'No favorites yet. Click ☆ to add symbols.'
                : 'No symbols found.'}
            </div>
          ) : (
            displayCoins.slice(0, 50).map((coin) =>
              renderSymbolItem(coin, favorites.includes(coin.symbol))
            )
          )}
        </div>
      </div>

      {/* Main Chart Area - TradingView Style */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', backgroundColor: darkMode ? '#0f172a' : '#ffffff' }}>
        {/* Top Toolbar */}
        <div style={{
          padding: '0.75rem 1rem',
          borderBottom: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          display: 'flex',
          alignItems: 'center',
          gap: '1rem',
          flexWrap: 'wrap'
        }}>
          {/* Symbol Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginRight: 'auto' }}>
            <div>
              <div style={{
                fontSize: '1.125rem',
                fontWeight: '700',
                color: colors.text,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                {selectedSymbol}/USD
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: '600',
                  padding: '0.125rem 0.375rem',
                  borderRadius: '0.25rem',
                  backgroundColor: darkMode ? '#1e293b' : '#f1f5f9',
                  color: colors.textMuted
                }}>
                  {timeframe}
                </span>
              </div>
            </div>

            {currentCoin && priceData && (
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem' }}>
                <span style={{ fontSize: '1.25rem', fontWeight: '700', color: colors.text }}>
                  ${priceData[priceData.length - 1].price.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </span>
                <span style={{
                  fontSize: '0.875rem',
                  fontWeight: '600',
                  color: currentCoin.change_24h >= 0 ? '#10b981' : '#ef4444'
                }}>
                  {currentCoin.change_24h >= 0 ? '+' : ''}{currentCoin.change_24h?.toFixed(2)}%
                </span>
              </div>
            )}
          </div>

          {/* Timeframe Selector */}
          <div style={{ display: 'flex', gap: '0.25rem' }}>
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                style={{
                  padding: '0.375rem 0.75rem',
                  backgroundColor: timeframe === tf
                    ? (darkMode ? '#1e293b' : '#e2e8f0')
                    : 'transparent',
                  color: timeframe === tf ? '#3b82f6' : colors.textMuted,
                  border: 'none',
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.8125rem',
                  fontWeight: '600',
                  transition: 'all 0.15s'
                }}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Indicators */}
          <div style={{ display: 'flex', gap: '0.5rem', paddingLeft: '0.5rem', borderLeft: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}` }}>
            {['Indicators', 'Compare', 'Alerts'].map((btn) => (
              <button
                key={btn}
                style={{
                  padding: '0.375rem 0.75rem',
                  backgroundColor: 'transparent',
                  color: colors.textMuted,
                  border: `1px solid ${darkMode ? '#334155' : '#cbd5e1'}`,
                  borderRadius: '0.25rem',
                  cursor: 'pointer',
                  fontSize: '0.8125rem',
                  fontWeight: '500',
                  transition: 'all 0.15s'
                }}
              >
                {btn}
              </button>
            ))}
          </div>
        </div>

        {/* Chart */}
        <div style={{ flex: 1, position: 'relative' }}>
          {renderPriceChart()}
        </div>

        {/* Volume Chart */}
        <div style={{
          height: '120px',
          borderTop: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
          padding: '0.75rem',
          backgroundColor: darkMode ? '#0f172a' : '#ffffff'
        }}>
          {priceData && (
            <div style={{ display: 'flex', alignItems: 'flex-end', height: '100%', gap: '1px' }}>
              {priceData.map((point, index) => {
                const maxVolume = Math.max(...priceData.map(p => p.volume));
                const height = (point.volume / maxVolume) * 100;
                const isUp = index > 0 && point.price > priceData[index - 1].price;
                return (
                  <div
                    key={index}
                    style={{
                      flex: 1,
                      height: `${height}%`,
                      backgroundColor: isUp ? '#10b98130' : '#ef444430',
                      borderTop: `2px solid ${isUp ? '#10b981' : '#ef4444'}`,
                      transition: 'height 0.2s'
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
