import React, { useState, useEffect, useCallback } from 'react';

export function MarketChart({ colors, darkMode, API_BASE }) {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC');
  const [timeframe, setTimeframe] = useState('1h');
  const [marketData, setMarketData] = useState([]);
  const [priceData, setPriceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [favorites, setFavorites] = useState(() => {
    // Load favorites from localStorage
    const saved = localStorage.getItem('marketFavorites');
    return saved ? JSON.parse(saved) : ['BTC', 'ETH', 'SOL', 'BNB'];
  });
  const [activeTab, setActiveTab] = useState('favorites');
  const [showMA, setShowMA] = useState(true);
  const [showRSI, setShowRSI] = useState(false);
  const [indicators, setIndicators] = useState({ ma20: [], ma50: [], rsi: [] });
  const [showIndicatorsMenu, setShowIndicatorsMenu] = useState(false);

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d', '1w'];

  // Timeframe to data points mapping
  const getTimeframeConfig = (tf) => {
    const configs = {
      '1m': { points: 60, interval: 60000 },      // 1 hour of 1-min data
      '5m': { points: 72, interval: 300000 },     // 6 hours of 5-min data
      '15m': { points: 96, interval: 900000 },    // 24 hours of 15-min data
      '1h': { points: 168, interval: 3600000 },   // 1 week of 1-hour data
      '4h': { points: 180, interval: 14400000 },  // 1 month of 4-hour data
      '1d': { points: 90, interval: 86400000 },   // 3 months of daily data
      '1w': { points: 52, interval: 604800000 }   // 1 year of weekly data
    };
    return configs[tf] || configs['1h'];
  };

  // Save favorites to localStorage whenever they change
  useEffect(() => {
    localStorage.setItem('marketFavorites', JSON.stringify(favorites));
  }, [favorites]);

  // Fetch market overview data
  const fetchMarketData = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/live`);
      if (response.ok) {
        const result = await response.json();

        // Convert API format to component format
        // API returns: { status: "success", data: { btc: { symbol: "BTC", usd: 45000, ... }, ... } }
        // We need: [{ symbol: "BTC", name: "Bitcoin", price: 45000, change_24h: 2.5, ... }, ...]
        if (result.data) {
          const coins = Object.values(result.data).map(coin => ({
            symbol: coin.symbol,
            name: coin.symbol, // Use symbol as name for now
            price: coin.usd || 0,
            change_24h: coin.usd_24h_change || 0,
            market_cap: coin.usd_market_cap || 0,
            volume_24h: coin.usd_24h_vol || 0
          }));
          setMarketData(coins);
        }
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

  // Calculate moving average
  const calculateMA = (data, period) => {
    const ma = [];
    for (let i = 0; i < data.length; i++) {
      if (i < period - 1) {
        ma.push(null);
      } else {
        const sum = data.slice(i - period + 1, i + 1).reduce((acc, val) => acc + val.price, 0);
        ma.push(sum / period);
      }
    }
    return ma;
  };

  // Calculate RSI
  const calculateRSI = (data, period = 14) => {
    const rsi = [];
    const changes = [];

    for (let i = 1; i < data.length; i++) {
      changes.push(data[i].price - data[i - 1].price);
    }

    for (let i = 0; i < changes.length; i++) {
      if (i < period) {
        rsi.push(null);
      } else {
        const gains = changes.slice(i - period + 1, i + 1).filter(c => c > 0);
        const losses = changes.slice(i - period + 1, i + 1).filter(c => c < 0).map(c => Math.abs(c));

        const avgGain = gains.length > 0 ? gains.reduce((a, b) => a + b, 0) / period : 0;
        const avgLoss = losses.length > 0 ? losses.reduce((a, b) => a + b, 0) / period : 0;

        if (avgLoss === 0) {
          rsi.push(100);
        } else {
          const rs = avgGain / avgLoss;
          rsi.push(100 - (100 / (1 + rs)));
        }
      }
    }

    return rsi;
  };

  // Generate realistic price data based on real current price and timeframe
  const generatePriceData = useCallback((basePrice, config) => {
    const data = [];
    let currentPrice = basePrice;
    const now = Date.now();

    // Create realistic volatility based on timeframe
    const volatility = {
      '1m': 0.001, '5m': 0.003, '15m': 0.005,
      '1h': 0.01, '4h': 0.02, '1d': 0.03, '1w': 0.05
    }[timeframe] || 0.01;

    for (let i = 0; i < config.points; i++) {
      const timestamp = now - (config.points - i) * config.interval;

      // Add trend and noise
      const trend = Math.sin(i / config.points * Math.PI * 2) * basePrice * 0.02;
      const noise = (Math.random() - 0.5) * basePrice * volatility;
      currentPrice += (trend + noise) / config.points;

      // Keep price within reasonable range
      currentPrice = Math.max(basePrice * 0.85, Math.min(basePrice * 1.15, currentPrice));

      const high = currentPrice * (1 + Math.random() * volatility);
      const low = currentPrice * (1 - Math.random() * volatility);

      data.push({
        timestamp,
        price: currentPrice,
        high,
        low,
        open: i > 0 ? data[i - 1].price : currentPrice,
        close: currentPrice,
        volume: Math.random() * 1000000 * (1 + Math.abs(noise) / basePrice)
      });
    }

    return data;
  }, [timeframe]);

  // Fetch price data for selected symbol and timeframe
  const fetchPriceData = useCallback(async () => {
    setLoading(true);
    try {
      const coin = marketData.find(m => m.symbol === selectedSymbol);
      if (!coin) {
        setLoading(false);
        return;
      }

      const config = getTimeframeConfig(timeframe);
      const data = generatePriceData(coin.price, config);
      setPriceData(data);

      // Calculate indicators
      const ma20 = calculateMA(data, 20);
      const ma50 = calculateMA(data, 50);
      const rsi = calculateRSI(data, 14);

      setIndicators({ ma20, ma50, rsi });
    } catch (error) {
      console.error('Error fetching price data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedSymbol, timeframe, marketData, generatePriceData]);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 30000); // Update every 30s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedSymbol && marketData.length > 0) {
      fetchPriceData();
    }
  }, [selectedSymbol, timeframe, marketData, fetchPriceData]);

  // Auto-refresh price data every 30 seconds
  useEffect(() => {
    if (!priceData) return;

    const interval = setInterval(() => {
      fetchPriceData();
    }, 30000);

    return () => clearInterval(interval);
  }, [priceData, fetchPriceData]);

  // Close indicators menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      if (showIndicatorsMenu) {
        setShowIndicatorsMenu(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [showIndicatorsMenu]);

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

  // Render RSI chart
  const renderRSIChart = () => {
    if (!priceData || priceData.length === 0 || indicators.rsi.length === 0) {
      return null;
    }

    const width = 1000;
    const height = 100;
    const padding = 60;
    const chartWidth = width - (padding * 2);
    const chartHeight = height - 20;

    return (
      <div style={{
        height: '120px',
        borderTop: `1px solid ${darkMode ? '#1e293b' : '#e2e8f0'}`,
        backgroundColor: darkMode ? '#0f172a' : '#ffffff',
        position: 'relative'
      }}>
        <div style={{
          position: 'absolute',
          top: '0.5rem',
          left: '1rem',
          fontSize: '0.75rem',
          fontWeight: '600',
          color: colors.textMuted
        }}>
          RSI(14)
        </div>

        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="xMidYMid meet">
          {/* Overbought line (70) */}
          <line
            x1={padding}
            y1={10 + (chartHeight * 0.3)}
            x2={width - padding}
            y2={10 + (chartHeight * 0.3)}
            stroke="#ef4444"
            strokeWidth="1"
            strokeDasharray="3,3"
            vectorEffect="non-scaling-stroke"
            opacity="0.5"
          />

          {/* Midline (50) */}
          <line
            x1={padding}
            y1={10 + (chartHeight * 0.5)}
            x2={width - padding}
            y2={10 + (chartHeight * 0.5)}
            stroke={darkMode ? '#475569' : '#cbd5e1'}
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />

          {/* Oversold line (30) */}
          <line
            x1={padding}
            y1={10 + (chartHeight * 0.7)}
            x2={width - padding}
            y2={10 + (chartHeight * 0.7)}
            stroke="#10b981"
            strokeWidth="1"
            strokeDasharray="3,3"
            vectorEffect="non-scaling-stroke"
            opacity="0.5"
          />

          {/* RSI line */}
          <polyline
            points={indicators.rsi.map((value, index) => {
              if (value === null) return null;
              const x = padding + (index / (indicators.rsi.length - 1)) * chartWidth;
              const y = 10 + chartHeight - ((value / 100) * chartHeight);
              return `${x},${y}`;
            }).filter(p => p !== null).join(' ')}
            fill="none"
            stroke="#8b5cf6"
            strokeWidth="2"
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {/* Y-axis labels */}
          <text x={width - padding + 5} y={10 + (chartHeight * 0.3) + 4} textAnchor="start" fill={colors.textMuted} fontSize="10">70</text>
          <text x={width - padding + 5} y={10 + (chartHeight * 0.5) + 4} textAnchor="start" fill={colors.textMuted} fontSize="10">50</text>
          <text x={width - padding + 5} y={10 + (chartHeight * 0.7) + 4} textAnchor="start" fill={colors.textMuted} fontSize="10">30</text>
        </svg>
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

          {/* MA20 overlay */}
          {showMA && indicators.ma20.length > 0 && (
            <polyline
              points={indicators.ma20.map((value, index) => {
                if (value === null) return null;
                const x = padding + (index / (priceData.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((value - minPrice) / priceRange) * chartHeight;
                return `${x},${y}`;
              }).filter(p => p !== null).join(' ')}
              fill="none"
              stroke="#3b82f6"
              strokeWidth="1.5"
              strokeDasharray="3,3"
              vectorEffect="non-scaling-stroke"
            />
          )}

          {/* MA50 overlay */}
          {showMA && indicators.ma50.length > 0 && (
            <polyline
              points={indicators.ma50.map((value, index) => {
                if (value === null) return null;
                const x = padding + (index / (priceData.length - 1)) * chartWidth;
                const y = padding + chartHeight - ((value - minPrice) / priceRange) * chartHeight;
                return `${x},${y}`;
              }).filter(p => p !== null).join(' ')}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="1.5"
              strokeDasharray="5,5"
              vectorEffect="non-scaling-stroke"
            />
          )}

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

        {/* Indicator Legend */}
        {showMA && (
          <div style={{
            position: 'absolute',
            top: '1rem',
            left: '1rem',
            display: 'flex',
            gap: '1rem',
            backgroundColor: darkMode ? '#1e293b90' : '#ffffff90',
            backdropFilter: 'blur(4px)',
            padding: '0.5rem 0.75rem',
            borderRadius: '0.375rem',
            fontSize: '0.75rem',
            fontWeight: '600'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <div style={{ width: '16px', height: '2px', backgroundColor: '#3b82f6', borderStyle: 'dashed' }} />
              <span style={{ color: '#3b82f6' }}>MA20</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <div style={{ width: '16px', height: '2px', backgroundColor: '#f59e0b', borderStyle: 'dashed' }} />
              <span style={{ color: '#f59e0b' }}>MA50</span>
            </div>
          </div>
        )}
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
          <div style={{ display: 'flex', gap: '0.5rem', paddingLeft: '0.5rem', borderLeft: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`, position: 'relative' }}>
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowIndicatorsMenu(!showIndicatorsMenu);
              }}
              style={{
                padding: '0.375rem 0.75rem',
                backgroundColor: showIndicatorsMenu || showMA || showRSI ? (darkMode ? '#1e293b' : '#e2e8f0') : 'transparent',
                color: showMA || showRSI ? '#3b82f6' : colors.textMuted,
                border: `1px solid ${darkMode ? '#334155' : '#cbd5e1'}`,
                borderRadius: '0.25rem',
                cursor: 'pointer',
                fontSize: '0.8125rem',
                fontWeight: '500',
                transition: 'all 0.15s'
              }}
            >
              Indicators {(showMA || showRSI) && '✓'}
            </button>

            {/* Indicators Menu */}
            {showIndicatorsMenu && (
              <div
                onClick={(e) => e.stopPropagation()}
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: '0',
                  marginTop: '0.5rem',
                  backgroundColor: darkMode ? '#1e293b' : '#ffffff',
                  border: `1px solid ${darkMode ? '#334155' : '#e2e8f0'}`,
                  borderRadius: '0.375rem',
                  boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
                  zIndex: 1000,
                  minWidth: '200px',
                  padding: '0.5rem'
                }}
              >
                <div
                  onClick={() => setShowMA(!showMA)}
                  style={{
                    padding: '0.625rem',
                    cursor: 'pointer',
                    borderRadius: '0.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'background-color 0.15s',
                    backgroundColor: 'transparent'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#f1f5f9'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <span style={{ fontSize: '0.875rem', color: colors.text }}>Moving Averages</span>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '0.25rem',
                    border: `2px solid ${showMA ? '#3b82f6' : colors.textMuted}`,
                    backgroundColor: showMA ? '#3b82f6' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    color: '#ffffff',
                    fontWeight: '700'
                  }}>
                    {showMA && '✓'}
                  </div>
                </div>

                <div
                  onClick={() => setShowRSI(!showRSI)}
                  style={{
                    padding: '0.625rem',
                    cursor: 'pointer',
                    borderRadius: '0.25rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'background-color 0.15s',
                    backgroundColor: 'transparent'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#334155' : '#f1f5f9'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <span style={{ fontSize: '0.875rem', color: colors.text }}>RSI (14)</span>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '0.25rem',
                    border: `2px solid ${showRSI ? '#3b82f6' : colors.textMuted}`,
                    backgroundColor: showRSI ? '#3b82f6' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.75rem',
                    color: '#ffffff',
                    fontWeight: '700'
                  }}>
                    {showRSI && '✓'}
                  </div>
                </div>
              </div>
            )}

            <button
              style={{
                padding: '0.375rem 0.75rem',
                backgroundColor: 'transparent',
                color: colors.textMuted,
                border: `1px solid ${darkMode ? '#334155' : '#cbd5e1'}`,
                borderRadius: '0.25rem',
                cursor: 'pointer',
                fontSize: '0.8125rem',
                fontWeight: '500',
                transition: 'all 0.15s',
                opacity: 0.5
              }}
              title="Coming soon"
            >
              Compare
            </button>
            <button
              style={{
                padding: '0.375rem 0.75rem',
                backgroundColor: 'transparent',
                color: colors.textMuted,
                border: `1px solid ${darkMode ? '#334155' : '#cbd5e1'}`,
                borderRadius: '0.25rem',
                cursor: 'pointer',
                fontSize: '0.8125rem',
                fontWeight: '500',
                transition: 'all 0.15s',
                opacity: 0.5
              }}
              title="Coming soon"
            >
              Alerts
            </button>
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

        {/* RSI Chart - conditionally rendered */}
        {showRSI && renderRSIChart()}
      </div>
    </div>
  );
}
