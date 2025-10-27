import React, { useState, useEffect } from 'react';
import { Activity, TrendingUp, DollarSign, AlertCircle, Play, Square, Download, Trash2, Power, PowerOff } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './App.css';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState({
    total_trades: 0,
    total_pnl: 0,
    win_rate: 0,
    avg_pnl: 0
  });
  const [marketPrices, setMarketPrices] = useState({});
  const [config, setConfig] = useState({});
  const [simulatorRunning, setSimulatorRunning] = useState(false);
  const [servicesRunning, setServicesRunning] = useState(true);

  // Fetch data functions
  const fetchTrades = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/trades?limit=50`);
      const data = await response.json();
      setTrades(data.trades || []);
    } catch (error) {
      console.error('Error fetching trades:', error);
    }
  };

  const fetchSummary = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/summary`);
      const data = await response.json();
      setSummary(data);
    } catch (error) {
      console.error('Error fetching summary:', error);
    }
  };

  const fetchMarketPrices = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/market/prices`);
      const data = await response.json();
      setMarketPrices(data);
    } catch (error) {
      console.error('Error fetching market prices:', error);
    }
  };

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/config`);
      const data = await response.json();
      setConfig(data);
    } catch (error) {
      console.error('Error fetching config:', error);
    }
  };

  const checkSimulatorStatus = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/simulator/status`);
      const data = await response.json();
      setSimulatorRunning(data.running);
    } catch (error) {
      console.error('Error checking simulator status:', error);
    }
  };

  // Control functions
  const toggleSimulator = async () => {
    try {
      const endpoint = simulatorRunning ? '/api/simulator/stop' : '/api/simulator/start';
      const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      const data = await response.json();
      console.log('Simulator response:', data);
      setSimulatorRunning(!simulatorRunning);
      
      // Refresh trades after starting
      if (!simulatorRunning) {
        setTimeout(fetchTrades, 2000);
      }
    } catch (error) {
      console.error('Error toggling simulator:', error);
    }
  };

  const startLiveTrading = async () => {
    if (confirm('Start LIVE trading? (Currently in DEMO mode)')) {
      try {
        const response = await fetch(`${API_BASE}/api/live/start`, { method: 'POST' });
        const data = await response.json();
        alert(data.message);
      } catch (error) {
        console.error('Error starting live trading:', error);
      }
    }
  };

  const toggleServices = async () => {
    try {
      const endpoint = servicesRunning ? '/api/services/stop' : '/api/services/start';
      const response = await fetch(`${API_BASE}${endpoint}`, { method: 'POST' });
      const data = await response.json();
      console.log('Services response:', data);
      setServicesRunning(!servicesRunning);
    } catch (error) {
      console.error('Error toggling services:', error);
    }
  };

  const exportCSV = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/data/export`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `trades_${new Date().toISOString()}.csv`;
      a.click();
    } catch (error) {
      console.error('Error exporting CSV:', error);
    }
  };

  const clearDatabase = async () => {
    if (confirm('Are you sure you want to clear all trade data?')) {
      try {
        const response = await fetch(`${API_BASE}/api/data/clear`, { method: 'POST' });
        const data = await response.json();
        alert(data.message);
        fetchTrades();
        fetchSummary();
      } catch (error) {
        console.error('Error clearing database:', error);
      }
    }
  };

  // Auto-refresh
  useEffect(() => {
    fetchTrades();
    fetchSummary();
    fetchMarketPrices();
    fetchConfig();
    checkSimulatorStatus();

    const interval = setInterval(() => {
      fetchTrades();
      fetchSummary();
      fetchMarketPrices();
      checkSimulatorStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Chart data
  const chartData = trades.slice(0, 20).reverse().map((trade, index) => ({
    index,
    pnl: trade.pnl,
    cumulative: trades.slice(0, index + 1).reduce((sum, t) => sum + t.pnl, 0)
  }));

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <h1 className="text-3xl font-bold text-gray-900">JJ-Bot Trading Dashboard</h1>
            <div className="flex items-center space-x-4">
              <span className={`px-3 py-1 rounded-full text-sm ${simulatorRunning ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                Simulator: {simulatorRunning ? 'Running' : 'Stopped'}
              </span>
              <span className={`px-3 py-1 rounded-full text-sm ${servicesRunning ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                Services: {servicesRunning ? 'Running' : 'Stopped'}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 mb-8">
          <nav className="-mb-px flex space-x-8">
            {['overview', 'trades', 'control', 'market', 'config'].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`py-2 px-1 border-b-2 font-medium text-sm capitalize ${
                  activeTab === tab
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab}
              </button>
            ))}
          </nav>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4 mb-8">
              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <Activity className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">Total Trades</dt>
                        <dd className="text-lg font-medium text-gray-900">{summary.total_trades}</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <DollarSign className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">Total P&L</dt>
                        <dd className={`text-lg font-medium ${summary.total_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${summary.total_pnl?.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <TrendingUp className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">Win Rate</dt>
                        <dd className="text-lg font-medium text-gray-900">{summary.win_rate?.toFixed(1)}%</dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>

              <div className="bg-white overflow-hidden shadow rounded-lg">
                <div className="p-5">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <AlertCircle className="h-6 w-6 text-gray-400" />
                    </div>
                    <div className="ml-5 w-0 flex-1">
                      <dl>
                        <dt className="text-sm font-medium text-gray-500 truncate">Avg P&L</dt>
                        <dd className={`text-lg font-medium ${summary.avg_pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${summary.avg_pnl?.toFixed(2)}
                        </dd>
                      </dl>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* P&L Chart */}
            {trades.length > 0 && (
              <div className="bg-white shadow rounded-lg p-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">P&L Performance</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="index" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="pnl" stroke="#8884d8" name="Trade P&L" />
                    <Line type="monotone" dataKey="cumulative" stroke="#82ca9d" name="Cumulative P&L" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Control Tab - UPDATED */}
        {activeTab === 'control' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-6">🎮 Control Panel</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Trade Simulator */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3">Trade Simulator</h3>
                <button
                  onClick={toggleSimulator}
                  className={`w-full flex items-center justify-center px-4 py-2 rounded-md text-white ${
                    simulatorRunning 
                      ? 'bg-red-600 hover:bg-red-700' 
                      : 'bg-green-600 hover:bg-green-700'
                  }`}
                >
                  {simulatorRunning ? (
                    <>
                      <Square className="mr-2 h-4 w-4" />
                      Stop Simulator
                    </>
                  ) : (
                    <>
                      <Play className="mr-2 h-4 w-4" />
                      Start Simulator
                    </>
                  )}
                </button>
              </div>

              {/* Live Trading */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3">Live Trading (DEMO)</h3>
                <button
                  onClick={startLiveTrading}
                  className="w-full flex items-center justify-center px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-md text-white"
                >
                  <AlertCircle className="mr-2 h-4 w-4" />
                  Start Live Trading
                </button>
              </div>

              {/* System Control */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3">System Control</h3>
                <button
                  onClick={toggleServices}
                  className={`w-full flex items-center justify-center px-4 py-2 rounded-md text-white ${
                    servicesRunning 
                      ? 'bg-red-600 hover:bg-red-700' 
                      : 'bg-blue-600 hover:bg-blue-700'
                  }`}
                >
                  {servicesRunning ? (
                    <>
                      <PowerOff className="mr-2 h-4 w-4" />
                      Stop All Services
                    </>
                  ) : (
                    <>
                      <Power className="mr-2 h-4 w-4" />
                      Start All Services
                    </>
                  )}
                </button>
              </div>

              {/* Data Management */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-3">Data Management</h3>
                <div className="space-y-2">
                  <button
                    onClick={exportCSV}
                    className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-white"
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Export CSV
                  </button>
                  <button
                    onClick={clearDatabase}
                    className="w-full flex items-center justify-center px-4 py-2 bg-gray-600 hover:bg-gray-700 rounded-md text-white"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Clear Database
                  </button>
                </div>
              </div>
            </div>

            {/* Recent Trades Preview */}
            <div className="mt-8">
              <h3 className="font-semibold mb-3">Recent Trades</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">P&L</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {trades.slice(0, 5).map((trade, index) => (
                      <tr key={index}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {new Date(trade.timestamp).toLocaleTimeString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{trade.symbol}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{trade.signal}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.last_price}</td>
                        <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                          trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          ${trade.pnl?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Trades Tab */}
        {activeTab === 'trades' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Recent Trades</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Symbol</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signal</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Price</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">VWAP</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">P&L</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {trades.map((trade, index) => (
                    <tr key={index}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(trade.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{trade.symbol}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{trade.signal}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.last_price}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${trade.vwap}</td>
                      <td className={`px-6 py-4 whitespace-nowrap text-sm font-medium ${
                        trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                        ${trade.pnl?.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Market Tab */}
        {activeTab === 'market' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Market Prices</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(marketPrices).map(([symbol, data]) => (
                <div key={symbol} className="border rounded-lg p-4">
                  <h3 className="font-semibold">{symbol}</h3>
                  <p className="text-2xl font-bold">${data.price}</p>
                  <p className={`text-sm ${data.change_24h >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {data.change_24h >= 0 ? '+' : ''}{data.change_24h?.toFixed(2)}%
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Config Tab */}
        {activeTab === 'config' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold mb-4">Configuration</h2>
            <pre className="bg-gray-100 p-4 rounded overflow-x-auto">
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
