import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from "recharts";

function DeveloperDashboard() {
  const [activeSection, setActiveSection] = useState('overview');
  const [adminData, setAdminData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [logs, setLogs] = useState({});
  const [configs, setConfigs] = useState({});
  const [dbStats, setDbStats] = useState(null);

  const sections = [
    { id: 'overview', name: '📊 Overview', icon: '📊' },
    { id: 'backups', name: '💾 Backups', icon: '💾' },
    { id: 'restore', name: '🔄 Restore', icon: '🔄' },
    { id: 'database', name: '🗄️ Database', icon: '🗄️' },
    { id: 'configs', name: '⚙️ Configs', icon: '⚙️' },
    { id: 'logs', name: '📜 Logs', icon: '📜' },
    { id: 'services', name: '🔧 Services', icon: '🔧' },
    { id: 'testing', name: '🧪 Testing', icon: '🧪' }
  ];

  const fetchAdminData = async () => {
    try {
      const response = await fetch("/api/admin/dashboard");
      if (response.ok) {
        const data = await response.json();
        setAdminData(data);
      }
      setLoading(false);
    } catch (error) {
      console.error("Error fetching admin data:", error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
    const interval = setInterval(fetchAdminData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, []);

  const createBackup = async (type, description) => {
    try {
      const response = await fetch("/api/admin/backup/create", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, description })
      });
      
      const result = await response.json();
      if (result.success) {
        alert(`Backup created successfully: ${result.backup.name}`);
        fetchAdminData(); // Refresh data
      } else {
        alert(`Backup failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Backup error: ${error.message}`);
    }
  };

  const restoreBackup = async (backupId, options) => {
    if (!confirm(`Are you sure you want to restore from backup ${backupId}? This will stop services and modify the system.`)) {
      return;
    }

    try {
      const response = await fetch("/api/admin/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backup_id: backupId, options })
      });
      
      const result = await response.json();
      if (result.success) {
        alert(`Restore completed successfully. Status: ${result.restore.status}`);
        fetchAdminData();
      } else {
        alert(`Restore failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Restore error: ${error.message}`);
    }
  };

  const fetchLogs = async (logType) => {
    try {
      const response = await fetch(`/api/admin/logs/${logType}`);
      if (response.ok) {
        const data = await response.json();
        setLogs(prev => ({ ...prev, [logType]: data }));
      }
    } catch (error) {
      console.error(`Error fetching ${logType} logs:`, error);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2>🛠️ Loading Developer Dashboard...</h2>
      </div>
    );
  }

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', minHeight: '100vh', background: '#f5f7fa' }}>
      {/* Header */}
      <header style={{ 
        background: 'linear-gradient(135deg, #2d3748 0%, #4a5568 100%)', 
        color: 'white', 
        padding: '20px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ margin: '0', fontSize: '28px' }}>🛠️ JJ Gorilla Developer Dashboard</h1>
            <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>Enterprise System Administration & Management</p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '14px', opacity: 0.9 }}>
              System Status: <span style={{ color: '#48bb78' }}>HEALTHY</span>
            </div>
            <div style={{ fontSize: '12px', opacity: 0.7 }}>
              Last Update: {adminData?.timestamp ? new Date(adminData.timestamp).toLocaleTimeString() : 'Unknown'}
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav style={{ background: 'white', borderBottom: '1px solid #e2e8f0', padding: '0 20px' }}>
        <div style={{ display: 'flex', overflowX: 'auto' }}>
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              style={{
                padding: '15px 20px',
                border: 'none',
                background: activeSection === section.id ? '#4a5568' : 'transparent',
                color: activeSection === section.id ? 'white' : '#64748b',
                cursor: 'pointer',
                borderRadius: '0',
                borderBottom: activeSection === section.id ? '3px solid #4a5568' : '3px solid transparent',
                fontSize: '14px',
                fontWeight: '500',
                whiteSpace: 'nowrap'
              }}
            >
              {section.name}
            </button>
          ))}
        </div>
      </nav>

      {/* Content */}
      <main style={{ padding: '20px' }}>
        {activeSection === 'overview' && <OverviewSection adminData={adminData} />}
        {activeSection === 'backups' && <BackupsSection adminData={adminData} createBackup={createBackup} />}
        {activeSection === 'restore' && <RestoreSection adminData={adminData} restoreBackup={restoreBackup} />}
        {activeSection === 'database' && <DatabaseSection dbStats={dbStats} setDbStats={setDbStats} />}
        {activeSection === 'configs' && <ConfigsSection configs={configs} setConfigs={setConfigs} />}
        {activeSection === 'logs' && <LogsSection logs={logs} fetchLogs={fetchLogs} />}
        {activeSection === 'services' && <ServicesSection adminData={adminData} />}
        {activeSection === 'testing' && <TestingSection />}
      </main>
    </div>
  );
}

// Section Components
function OverviewSection({ adminData }) {
  return (
    <div>
      <h2>📊 System Overview</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        
        {/* System Health */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>🏥 System Health</h3>
          {adminData?.system_metrics && (
            <div style={{ marginTop: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>CPU Usage:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.system_metrics.system.cpu_percent.toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>Memory Usage:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.system_metrics.system.memory_percent.toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>Disk Usage:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.system_metrics.system.disk_percent.toFixed(1)}%</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Uptime:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.system_metrics.jj_bot.uptime_formatted}</span>
              </div>
            </div>
          )}
        </div>

        {/* Backup Statistics */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>💾 Backup Statistics</h3>
          {adminData?.backup_stats && (
            <div style={{ marginTop: '15px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>Total Backups:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.backup_stats.total_backups}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span>Total Size:</span>
                <span style={{ fontWeight: 'bold' }}>{adminData.backup_stats.total_size_human}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Storage Location:</span>
                <span style={{ fontSize: '12px', wordBreak: 'break-all' }}>{adminData.backup_stats.storage_location}</span>
              </div>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>🕒 Recent Activity</h3>
          <div style={{ marginTop: '15px' }}>
            {adminData?.recent_backups?.slice(0, 5).map((backup, i) => (
              <div key={i} style={{ marginBottom: '8px', fontSize: '14px' }}>
                <span style={{ fontWeight: 'bold' }}>{backup.type.toUpperCase()}</span> backup
                <div style={{ color: '#666', fontSize: '12px' }}>
                  {new Date(backup.timestamp).toLocaleString()} - {backup.size_human}
                </div>
              </div>
            )) || <p style={{ color: '#666' }}>No recent activity</p>}
          </div>
        </div>

        {/* Service Status */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>🔧 Service Status</h3>
          {adminData?.system_status && (
            <div style={{ marginTop: '15px' }}>
              {Object.entries(adminData.system_status).map(([service, status]) => (
                <div key={service} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ textTransform: 'capitalize' }}>{service.replace('_', ' ')}:</span>
                  <span style={{ 
                    padding: '2px 8px', 
                    borderRadius: '12px', 
                    fontSize: '12px',
                    background: status === 'running' || status === 'active' || status === 'connected' || status === 'configured' ? '#48bb78' : '#f56565',
                    color: 'white'
                  }}>
                    {status.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function BackupsSection({ adminData, createBackup }) {
  return (
    <div>
      <h2>💾 Backup Management</h2>
      
      {/* Create Backup Controls */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h3>Create New Backup</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '10px', marginTop: '15px' }}>
          <button onClick={() => createBackup('full', 'Manual full backup')} style={buttonStyle}>
            📦 Full Backup
          </button>
          <button onClick={() => createBackup('incremental', 'Manual incremental backup')} style={buttonStyle}>
            📝 Incremental
          </button>
          <button onClick={() => createBackup('database', 'Manual database backup')} style={buttonStyle}>
            🗄️ Database Only
          </button>
          <button onClick={() => createBackup('config', 'Manual config backup')} style={buttonStyle}>
            ⚙️ Config Only
          </button>
          <button onClick={() => createBackup('code', 'Manual code backup')} style={buttonStyle}>
            💻 Code Only
          </button>
        </div>
      </div>

      {/* Recent Backups */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <h3>Recent Backups</h3>
        {adminData?.recent_backups?.length > 0 ? (
          <div style={{ overflowX: 'auto', marginTop: '15px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={tableHeaderStyle}>Type</th>
                  <th style={tableHeaderStyle}>Timestamp</th>
                  <th style={tableHeaderStyle}>Size</th>
                  <th style={tableHeaderStyle}>Files</th>
                  <th style={tableHeaderStyle}>Status</th>
                  <th style={tableHeaderStyle}>Description</th>
                </tr>
              </thead>
              <tbody>
                {adminData.recent_backups.map((backup, i) => (
                  <tr key={i}>
                    <td style={tableCellStyle}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '12px', 
                        background: getBackupTypeColor(backup.type),
                        color: 'white',
                        fontSize: '12px'
                      }}>
                        {backup.type.toUpperCase()}
                      </span>
                    </td>
                    <td style={tableCellStyle}>{new Date(backup.timestamp).toLocaleString()}</td>
                    <td style={tableCellStyle}>{backup.size_human}</td>
                    <td style={tableCellStyle}>{backup.files_count}</td>
                    <td style={tableCellStyle}>
                      <span style={{ color: backup.status === 'completed' ? 'green' : 'red' }}>
                        {backup.status}
                      </span>
                    </td>
                    <td style={tableCellStyle}>{backup.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#666', marginTop: '15px' }}>No backups available</p>
        )}
      </div>
    </div>
  );
}

function RestoreSection({ adminData, restoreBackup }) {
  const [selectedBackup, setSelectedBackup] = useState('');
  const [restoreOptions, setRestoreOptions] = useState({
    restore_database: true,
    restore_config: true,
    restore_code: true,
    backup_current: true,
    verify_restore: true
  });

  return (
    <div>
      <h2>🔄 System Restore</h2>
      
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h3>⚠️ Restore from Backup</h3>
        <p style={{ color: '#e53e3e', marginBottom: '20px' }}>
          <strong>Warning:</strong> Restoring will stop services and modify your system. A backup of the current state will be created first.
        </p>
        
        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Select Backup:</label>
          <select 
            value={selectedBackup} 
            onChange={(e) => setSelectedBackup(e.target.value)}
            style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
          >
            <option value="">Choose a backup...</option>
            {adminData?.recent_backups?.map((backup) => (
              <option key={backup.id} value={backup.id}>
                {backup.type.toUpperCase()} - {new Date(backup.timestamp).toLocaleString()} - {backup.size_human}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '10px', fontWeight: 'bold' }}>Restore Options:</label>
          {Object.entries(restoreOptions).map(([option, checked]) => (
            <label key={option} style={{ display: 'block', marginBottom: '5px' }}>
              <input 
                type="checkbox" 
                checked={checked}
                onChange={(e) => setRestoreOptions(prev => ({ ...prev, [option]: e.target.checked }))}
                style={{ marginRight: '8px' }}
              />
              {option.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
            </label>
          ))}
        </div>

        <button 
          onClick={() => selectedBackup && restoreBackup(selectedBackup, restoreOptions)}
          disabled={!selectedBackup}
          style={{
            ...buttonStyle,
            background: selectedBackup ? '#e53e3e' : '#ccc',
            color: 'white'
          }}
        >
          🔄 Restore System
        </button>
      </div>

      {/* Restore History */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <h3>📋 Restore History</h3>
        {adminData?.restore_history?.length > 0 ? (
          <div style={{ marginTop: '15px' }}>
            {adminData.restore_history.map((restore, i) => (
              <div key={i} style={{ padding: '10px', border: '1px solid #e2e8f0', borderRadius: '8px', marginBottom: '10px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 'bold' }}>Restore from {restore.backup_id}</span>
                  <span style={{ 
                    padding: '4px 8px', 
                    borderRadius: '12px', 
                    background: restore.status === 'completed' ? '#48bb78' : '#e53e3e',
                    color: 'white',
                    fontSize: '12px'
                  }}>
                    {restore.status.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: '14px', color: '#666', marginTop: '5px' }}>
                  {new Date(restore.timestamp).toLocaleString()}
                  {restore.duration && ` - ${restore.duration.toFixed(1)}s`}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: '#666', marginTop: '15px' }}>No restore history available</p>
        )}
      </div>
    </div>
  );
}

function DatabaseSection({ dbStats, setDbStats }) {
  useEffect(() => {
    fetchDbStats();
  }, []);

  const fetchDbStats = async () => {
    try {
      const response = await fetch("/api/admin/database/stats");
      if (response.ok) {
        const data = await response.json();
        setDbStats(data);
      }
    } catch (error) {
      console.error("Error fetching database stats:", error);
    }
  };

  const backupDatabase = async () => {
    try {
      const response = await fetch("/api/admin/database/backup", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        alert("Database backup created successfully!");
      } else {
        alert(`Database backup failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Database backup error: ${error.message}`);
    }
  };

  const exportDatabase = async () => {
    try {
      const response = await fetch("/api/admin/database/export", { method: "POST" });
      const result = await response.json();
      if (result.success) {
        alert(`Database exported to: ${result.export_path}`);
      } else {
        alert(`Database export failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Database export error: ${error.message}`);
    }
  };

  return (
    <div>
      <h2>🗄️ Database Management</h2>
      
      {/* Database Actions */}
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h3>Database Actions</h3>
        <div style={{ display: 'flex', gap: '10px', marginTop: '15px' }}>
          <button onClick={backupDatabase} style={buttonStyle}>
            💾 Backup Database
          </button>
          <button onClick={exportDatabase} style={buttonStyle}>
            📤 Export to SQL
          </button>
          <button onClick={fetchDbStats} style={buttonStyle}>
            🔄 Refresh Stats
          </button>
        </div>
      </div>

      {/* Database Statistics */}
      {dbStats?.success && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>📊 Database Statistics</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginTop: '15px' }}>
            
            <div>
              <h4>General Information</h4>
              <div style={{ fontSize: '14px' }}>
                <div style={{ marginBottom: '5px' }}>
                  <strong>File Size:</strong> {dbStats.stats.file_size_human}
                </div>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Tables:</strong> {dbStats.stats.tables?.join(', ')}
                </div>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Total Trades:</strong> {dbStats.stats.total_trades}
                </div>
              </div>
            </div>

            <div>
              <h4>P&L Statistics</h4>
              <div style={{ fontSize: '14px' }}>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Total P&L:</strong> ${dbStats.stats.pnl_stats?.total?.toFixed(2)}
                </div>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Average P&L:</strong> ${dbStats.stats.pnl_stats?.average?.toFixed(2)}
                </div>
              </div>
            </div>

            <div>
              <h4>Signal Distribution</h4>
              <div style={{ fontSize: '14px' }}>
                {Object.entries(dbStats.stats.signal_distribution || {}).map(([signal, count]) => (
                  <div key={signal} style={{ marginBottom: '5px' }}>
                    <strong>{signal}:</strong> {count} trades
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4>Date Range</h4>
              <div style={{ fontSize: '14px' }}>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Earliest:</strong> {dbStats.stats.date_range?.earliest}
                </div>
                <div style={{ marginBottom: '5px' }}>
                  <strong>Latest:</strong> {dbStats.stats.date_range?.latest}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigsSection({ configs, setConfigs }) {
  const [selectedConfig, setSelectedConfig] = useState('');
  const [editingConfig, setEditingConfig] = useState(false);
  const [configContent, setConfigContent] = useState('');

  useEffect(() => {
    fetchConfigs();
  }, []);

  const fetchConfigs = async () => {
    try {
      const response = await fetch("/api/admin/config/list");
      if (response.ok) {
        const data = await response.json();
        setConfigs(data);
      }
    } catch (error) {
      console.error("Error fetching configs:", error);
    }
  };

  const editConfig = (configFile) => {
    setSelectedConfig(configFile);
    const content = configs.configs?.[configFile];
    setConfigContent(typeof content === 'object' ? JSON.stringify(content, null, 2) : content || '');
    setEditingConfig(true);
  };

  const saveConfig = async () => {
    try {
      let contentToSave = configContent;
      
      // Try to parse as JSON if it's a .json file
      if (selectedConfig.endsWith('.json')) {
        try {
          contentToSave = JSON.parse(configContent);
        } catch (e) {
          alert("Invalid JSON format. Please fix the syntax.");
          return;
        }
      }

      const response = await fetch("/api/admin/config/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file: selectedConfig, content: contentToSave })
      });
      
      const result = await response.json();
      if (result.success) {
        alert("Configuration saved successfully!");
        setEditingConfig(false);
        fetchConfigs();
      } else {
        alert(`Save failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Save error: ${error.message}`);
    }
  };

  return (
    <div>
      <h2>⚙️ Configuration Management</h2>
      
      {editingConfig ? (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
            <h3>Editing: {selectedConfig}</h3>
            <div>
              <button onClick={saveConfig} style={{ ...buttonStyle, marginRight: '10px' }}>
                💾 Save
              </button>
              <button onClick={() => setEditingConfig(false)} style={buttonStyle}>
                ❌ Cancel
              </button>
            </div>
          </div>
          <textarea
            value={configContent}
            onChange={(e) => setConfigContent(e.target.value)}
            style={{
              width: '100%',
              height: '400px',
              fontFamily: 'monospace',
              fontSize: '14px',
              padding: '10px',
              border: '1px solid #ccc',
              borderRadius: '4px'
            }}
            placeholder="Configuration content..."
          />
        </div>
      ) : (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>Configuration Files</h3>
          <div style={{ marginTop: '15px' }}>
            {configs.success && Object.entries(configs.configs || {}).map(([configFile, content]) => (
              <div key={configFile} style={{ 
                padding: '15px', 
                border: '1px solid #e2e8f0', 
                borderRadius: '8px', 
                marginBottom: '10px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
              }}>
                <div>
                  <div style={{ fontWeight: 'bold' }}>{configFile}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>
                    {content === null ? 'File not found' : 
                     typeof content === 'object' ? 'JSON Configuration' : 
                     'Text Configuration'}
                  </div>
                </div>
                <button 
                  onClick={() => editConfig(configFile)}
                  disabled={content === null}
                  style={{
                    ...buttonStyle,
                    background: content === null ? '#ccc' : buttonStyle.background
                  }}
                >
                  ✏️ Edit
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LogsSection({ logs, fetchLogs }) {
  const [selectedLogType, setSelectedLogType] = useState('api');
  
  const logTypes = [
    { id: 'api', name: 'API Logs' },
    { id: 'backup', name: 'Backup Logs' },
    { id: 'restore', name: 'Restore Logs' },
    { id: 'system', name: 'System Logs' }
  ];

  useEffect(() => {
    fetchLogs(selectedLogType);
  }, [selectedLogType]);

  return (
    <div>
      <h2>📜 System Logs</h2>
      
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            {logTypes.map(logType => (
              <button
                key={logType.id}
                onClick={() => setSelectedLogType(logType.id)}
                style={{
                  ...buttonStyle,
                  marginRight: '10px',
                  background: selectedLogType === logType.id ? '#4a5568' : '#e2e8f0',
                  color: selectedLogType === logType.id ? 'white' : '#4a5568'
                }}
              >
                {logType.name}
              </button>
            ))}
          </div>
          <button onClick={() => fetchLogs(selectedLogType)} style={buttonStyle}>
            🔄 Refresh
          </button>
        </div>

        <div style={{
          background: '#1a202c',
          color: '#e2e8f0',
          padding: '15px',
          borderRadius: '8px',
          fontFamily: 'monospace',
          fontSize: '12px',
          height: '400px',
          overflowY: 'auto'
        }}>
          {logs[selectedLogType]?.success ? (
            logs[selectedLogType].logs.length > 0 ? (
              logs[selectedLogType].logs.map((line, i) => (
                <div key={i} style={{ marginBottom: '2px' }}>
                  {line}
                </div>
              ))
            ) : (
              <div style={{ color: '#a0aec0' }}>No logs available</div>
            )
          ) : (
            <div style={{ color: '#fed7d7' }}>
              {logs[selectedLogType]?.error || 'Loading logs...'}
            </div>
          )}
        </div>

        {logs[selectedLogType]?.success && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
            Showing {logs[selectedLogType].showing_lines} of {logs[selectedLogType].total_lines} lines
          </div>
        )}
      </div>
    </div>
  );
}

function ServicesSection({ adminData }) {
  const restartService = async (service) => {
    if (!confirm(`Are you sure you want to restart ${service}? This may cause temporary downtime.`)) {
      return;
    }

    try {
      const response = await fetch("/api/admin/service/restart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ service })
      });
      
      const result = await response.json();
      if (result.success) {
        alert(result.message);
      } else {
        alert(`Restart failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Restart error: ${error.message}`);
    }
  };

  return (
    <div>
      <h2>🔧 Service Management</h2>
      
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h3>Service Controls</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginTop: '15px' }}>
          <button onClick={() => restartService('api')} style={buttonStyle}>
            🔄 Restart API Server
          </button>
          <button onClick={() => restartService('all')} style={{ ...buttonStyle, background: '#e53e3e' }}>
            🔄 Restart All Services
          </button>
        </div>
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
        <h3>Service Status</h3>
        {adminData?.system_status && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px', marginTop: '15px' }}>
            {Object.entries(adminData.system_status).map(([service, status]) => (
              <div key={service} style={{ padding: '15px', border: '1px solid #e2e8f0', borderRadius: '8px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '10px', textTransform: 'capitalize' }}>
                  {service.replace('_', ' ')}
                </div>
                <div style={{ 
                  padding: '8px 12px', 
                  borderRadius: '20px', 
                  textAlign: 'center',
                  background: status === 'running' || status === 'active' || status === 'connected' || status === 'configured' ? '#48bb78' : '#f56565',
                  color: 'white',
                  fontSize: '14px',
                  fontWeight: 'bold'
                }}>
                  {status.toUpperCase()}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function TestingSection() {
  const [testResults, setTestResults] = useState(null);
  const [testing, setTesting] = useState(false);

  const runEndpointTests = async () => {
    setTesting(true);
    try {
      const response = await fetch("/api/admin/test/endpoints");
      if (response.ok) {
        const data = await response.json();
        setTestResults(data);
      }
    } catch (error) {
      console.error("Error running tests:", error);
    }
    setTesting(false);
  };

  return (
    <div>
      <h2>🧪 System Testing</h2>
      
      <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)', marginBottom: '20px' }}>
        <h3>API Endpoint Testing</h3>
        <button 
          onClick={runEndpointTests}
          disabled={testing}
          style={{
            ...buttonStyle,
            background: testing ? '#ccc' : buttonStyle.background
          }}
        >
          {testing ? '🔄 Testing...' : '🧪 Test All Endpoints'}
        </button>
      </div>

      {testResults && (
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 2px 10px rgba(0,0,0,0.1)' }}>
          <h3>Test Results</h3>
          
          {/* Summary */}
          <div style={{ marginBottom: '20px', padding: '15px', background: '#f8f9fa', borderRadius: '8px' }}>
            <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
              Success Rate: {testResults.summary?.success_rate?.toFixed(1)}%
            </div>
            <div>
              {testResults.summary?.successful_endpoints} / {testResults.summary?.total_endpoints} endpoints passed
            </div>
          </div>

          {/* Detailed Results */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f8f9fa' }}>
                  <th style={tableHeaderStyle}>Endpoint</th>
                  <th style={tableHeaderStyle}>Status</th>
                  <th style={tableHeaderStyle}>Response Time</th>
                  <th style={tableHeaderStyle}>Content Size</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(testResults.results || {}).map(([endpoint, result]) => (
                  <tr key={endpoint}>
                    <td style={tableCellStyle}>{endpoint}</td>
                    <td style={tableCellStyle}>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '12px', 
                        background: result.success ? '#48bb78' : '#f56565',
                        color: 'white',
                        fontSize: '12px'
                      }}>
                        {result.success ? `${result.status} OK` : 'FAILED'}
                      </span>
                    </td>
                    <td style={tableCellStyle}>
                      {result.response_time_ms ? `${result.response_time_ms.toFixed(0)}ms` : 'N/A'}
                    </td>
                    <td style={tableCellStyle}>
                      {result.content_length ? `${result.content_length} bytes` : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

// Helper functions and styles
const buttonStyle = {
  padding: '10px 15px',
  border: 'none',
  borderRadius: '6px',
  background: '#4a5568',
  color: 'white',
  cursor: 'pointer',
  fontSize: '14px',
  fontWeight: '500'
};

const tableHeaderStyle = {
  padding: '12px',
  textAlign: 'left',
  border: '1px solid #dee2e6',
  fontWeight: 'bold'
};

const tableCellStyle = {
  padding: '12px',
  border: '1px solid #dee2e6'
};

function getBackupTypeColor(type) {
  const colors = {
    'full': '#4a5568',
    'incremental': '#3182ce',
    'database': '#38a169',
    'config': '#d69e2e',
    'code': '#805ad5'
  };
  return colors[type] || '#718096';
}

export default DeveloperDashboard;
