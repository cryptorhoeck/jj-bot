"""
JJ-Bot Native Windows GUI Application
Professional PyQt6 interface for cryptocurrency trading bot
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time
import json
import sqlite3

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QSystemTrayIcon, QMenu, QGroupBox, QGridLayout, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QHeaderView, QStatusBar,
    QToolBar, QMessageBox, QComboBox, QLineEdit, QFileDialog
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter, QPixmap, QImage
import requests

# Chart imports
try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    CHARTS_AVAILABLE = True
except ImportError:
    CHARTS_AVAILABLE = False
    print("Warning: matplotlib not available, charts disabled")

# Get installation directory
INSTALL_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(INSTALL_DIR))

# Import local modules
from glue.api import engine


class DataUpdater(QObject):
    """Background thread for fetching API data"""
    data_updated = pyqtSignal(dict)
    services_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.running = False
        self.api_base = "http://127.0.0.1:8000"

    def start(self):
        self.running = True
        threading.Thread(target=self._update_loop, daemon=True).start()

    def stop(self):
        self.running = False

    def _update_loop(self):
        """Fetch data from API every 2 seconds"""
        while self.running:
            try:
                # Fetch all data
                data = {
                    'summary': requests.get(f"{self.api_base}/api/trades/summary", timeout=1).json(),
                    'trades': requests.get(f"{self.api_base}/api/trades?limit=50", timeout=1).json(),
                    'market': requests.get(f"{self.api_base}/api/market/live", timeout=1).json(),
                    'analytics': requests.get(f"{self.api_base}/api/services/analytics/data", timeout=1).json(),
                }
                self.data_updated.emit(data)

                # Fetch services status
                try:
                    services = requests.get(f"{self.api_base}/api/services/status", timeout=1).json()
                    self.services_updated.emit(services)
                except:
                    pass

            except Exception as e:
                pass  # Silently continue

            time.sleep(2)


class ChartWidget(QWidget):
    """Matplotlib chart widget for PyQt6"""
    def __init__(self, parent=None):
        super().__init__(parent)
        if not CHARTS_AVAILABLE:
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Charts unavailable (matplotlib not installed)"))
            self.setLayout(layout)
            return

        self.figure = Figure(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def plot_pnl_over_time(self, trades_data):
        """Plot P&L over time"""
        if not CHARTS_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        trades = trades_data.get('trades', [])
        if not trades:
            ax.text(0.5, 0.5, 'No trade data available', ha='center', va='center')
            self.canvas.draw()
            return

        # Calculate cumulative P&L
        timestamps = []
        cumulative_pnl = []
        total = 0

        for trade in reversed(trades):  # Oldest first
            timestamps.append(datetime.fromisoformat(trade['timestamp']))
            total += trade.get('pnl', 0)
            cumulative_pnl.append(total)

        ax.plot(timestamps, cumulative_pnl, 'g-' if total >= 0 else 'r-', linewidth=2)
        ax.set_title('Cumulative P&L Over Time')
        ax.set_xlabel('Time')
        ax.set_ylabel('P&L ($)')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
        self.figure.autofmt_xdate()
        self.canvas.draw()

    def plot_win_loss_pie(self, analytics_data):
        """Plot win/loss pie chart"""
        if not CHARTS_AVAILABLE:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        data = analytics_data.get('data', {})
        win_rate = data.get('win_rate', 0)
        loss_rate = 100 - win_rate

        if win_rate == 0 and loss_rate == 100:
            ax.text(0.5, 0.5, 'No analytics data available', ha='center', va='center')
            self.canvas.draw()
            return

        sizes = [win_rate, loss_rate]
        labels = [f'Wins ({win_rate:.1f}%)', f'Losses ({loss_rate:.1f}%)']
        colors = ['#10b981', '#ef4444']
        explode = (0.1, 0)

        ax.pie(sizes, explode=explode, labels=labels, colors=colors,
               autopct='%1.1f%%', shadow=True, startangle=90)
        ax.set_title('Win/Loss Ratio')
        self.canvas.draw()


class DashboardTab(QWidget):
    """Dashboard overview with key metrics"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("📊 Trading Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Metrics grid
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QGridLayout()

        # Create metric labels
        self.total_trades_label = QLabel("0")
        self.win_rate_label = QLabel("0.0%")
        self.total_pnl_label = QLabel("$0.00")
        self.profit_factor_label = QLabel("0.00")
        self.active_services_label = QLabel("0/4")

        # Style metric values
        for label in [self.total_trades_label, self.win_rate_label, self.total_pnl_label,
                      self.profit_factor_label, self.active_services_label]:
            label.setStyleSheet("font-size: 24px; font-weight: bold; color: #10b981;")

        # Add to grid
        metrics_layout.addWidget(QLabel("Total Trades:"), 0, 0)
        metrics_layout.addWidget(self.total_trades_label, 0, 1)
        metrics_layout.addWidget(QLabel("Win Rate:"), 0, 2)
        metrics_layout.addWidget(self.win_rate_label, 0, 3)

        metrics_layout.addWidget(QLabel("Total P&L:"), 1, 0)
        metrics_layout.addWidget(self.total_pnl_label, 1, 1)
        metrics_layout.addWidget(QLabel("Profit Factor:"), 1, 2)
        metrics_layout.addWidget(self.profit_factor_label, 1, 3)

        metrics_layout.addWidget(QLabel("Active Services:"), 2, 0)
        metrics_layout.addWidget(self.active_services_label, 2, 1)

        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)

        # Charts section
        if CHARTS_AVAILABLE:
            charts_group = QGroupBox("Performance Charts")
            charts_layout = QHBoxLayout()

            self.pnl_chart = ChartWidget()
            self.winloss_chart = ChartWidget()

            charts_layout.addWidget(self.pnl_chart)
            charts_layout.addWidget(self.winloss_chart)

            charts_group.setLayout(charts_layout)
            layout.addWidget(charts_group)

        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(150)
        activity_layout.addWidget(self.activity_log)
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)

        layout.addStretch()
        self.setLayout(layout)

    def update_data(self, data):
        """Update dashboard with new data"""
        try:
            summary = data.get('summary', {})
            analytics = data.get('analytics', {}).get('data', {})

            # Update metrics
            self.total_trades_label.setText(str(summary.get('total_trades', 0)))

            win_rate = analytics.get('win_rate', 0.0)
            self.win_rate_label.setText(f"{win_rate:.1f}%")
            if win_rate >= 50:
                self.win_rate_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #10b981;")
            else:
                self.win_rate_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444;")

            total_pnl = summary.get('total_pnl', 0.0)
            self.total_pnl_label.setText(f"${total_pnl:.2f}")
            if total_pnl >= 0:
                self.total_pnl_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #10b981;")
            else:
                self.total_pnl_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #ef4444;")

            profit_factor = analytics.get('profit_factor', 0.0)
            self.profit_factor_label.setText(f"{profit_factor:.2f}")

            # Update charts
            if CHARTS_AVAILABLE:
                self.pnl_chart.plot_pnl_over_time(data.get('trades', {}))
                self.winloss_chart.plot_win_loss_pie(data.get('analytics', {}))

            # Add to activity log
            if summary.get('total_trades', 0) > 0:
                timestamp = datetime.now().strftime("%H:%M:%S")
                self.activity_log.append(f"[{timestamp}] Updated: {summary.get('total_trades', 0)} trades, P&L: ${total_pnl:.2f}")

        except Exception as e:
            print(f"Error updating dashboard: {e}")

    def update_services_count(self, services):
        """Update active services count"""
        try:
            active = sum(1 for s in services.get('services', {}).values() if s.get('status') == 'running')
            total = len(services.get('services', {}))
            self.active_services_label.setText(f"{active}/{total}")
        except:
            pass


class MarketDataTab(QWidget):
    """Market data with live prices"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("💰 Market Data")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Live ticker
        self.ticker_label = QLabel("Fetching live prices...")
        self.ticker_label.setStyleSheet("font-size: 14px; padding: 5px; background-color: #f3f4f6; border-radius: 3px;")
        layout.addWidget(self.ticker_label)

        # Market table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Symbol", "Price", "24h Change", "Last Update"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def update_data(self, data):
        """Update market data table"""
        try:
            market_data = data.get('market', {}).get('data', {})

            self.table.setRowCount(len(market_data))

            # Build ticker text
            ticker_parts = []

            for row, (symbol, price_data) in enumerate(market_data.items()):
                # Symbol
                self.table.setItem(row, 0, QTableWidgetItem(symbol.upper()))

                # Price
                price = price_data.get('usd', 0)
                price_item = QTableWidgetItem(f"${price:,.2f}")
                self.table.setItem(row, 1, price_item)

                # 24h Change
                change = price_data.get('usd_24h_change', 0)
                change_item = QTableWidgetItem(f"{change:+.2f}%")
                if change >= 0:
                    change_item.setForeground(QColor("#10b981"))
                    ticker_parts.append(f"{symbol.upper()}: ${price:,.2f} ▲{change:.2f}%")
                else:
                    change_item.setForeground(QColor("#ef4444"))
                    ticker_parts.append(f"{symbol.upper()}: ${price:,.2f} ▼{abs(change):.2f}%")
                self.table.setItem(row, 2, change_item)

                # Last Update
                timestamp = price_data.get('timestamp', datetime.now().isoformat())
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%H:%M:%S")
                self.table.setItem(row, 3, QTableWidgetItem(time_str))

            # Update ticker
            if ticker_parts:
                self.ticker_label.setText(" | ".join(ticker_parts))

        except Exception as e:
            print(f"Error updating market data: {e}")


class TradesTab(QWidget):
    """Trade history table"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("📈 Trade History")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Trades table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Time", "Symbol", "Type", "Price", "Size", "P&L"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def update_data(self, data):
        """Update trades table"""
        try:
            trades = data.get('trades', {}).get('trades', [])

            self.table.setRowCount(len(trades))

            for row, trade in enumerate(trades):
                # Time
                timestamp = trade.get('timestamp', '')
                time_str = datetime.fromisoformat(timestamp).strftime("%m/%d %H:%M")
                self.table.setItem(row, 0, QTableWidgetItem(time_str))

                # Symbol
                self.table.setItem(row, 1, QTableWidgetItem(trade.get('symbol', '')))

                # Type
                trade_type = trade.get('side', '').upper()
                type_item = QTableWidgetItem(trade_type)
                if trade_type == 'BUY':
                    type_item.setForeground(QColor("#10b981"))
                else:
                    type_item.setForeground(QColor("#ef4444"))
                self.table.setItem(row, 2, type_item)

                # Price
                price = trade.get('price', 0)
                self.table.setItem(row, 3, QTableWidgetItem(f"${price:.2f}"))

                # Size
                size = trade.get('size', 0)
                self.table.setItem(row, 4, QTableWidgetItem(f"{size:.4f}"))

                # P&L
                pnl = trade.get('pnl', 0)
                pnl_item = QTableWidgetItem(f"${pnl:.2f}")
                if pnl >= 0:
                    pnl_item.setForeground(QColor("#10b981"))
                else:
                    pnl_item.setForeground(QColor("#ef4444"))
                self.table.setItem(row, 5, pnl_item)

        except Exception as e:
            print(f"Error updating trades: {e}")


class AnalyticsTab(QWidget):
    """Analytics and performance statistics"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("📊 Analytics")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Analytics grid
        analytics_group = QGroupBox("Performance Metrics")
        analytics_layout = QGridLayout()

        # Create labels
        self.win_rate = QLabel("0.0%")
        self.profit_factor = QLabel("0.00")
        self.sharpe_ratio = QLabel("0.00")
        self.max_drawdown = QLabel("0.0%")
        self.avg_win = QLabel("$0.00")
        self.avg_loss = QLabel("$0.00")

        # Add to grid
        analytics_layout.addWidget(QLabel("Win Rate:"), 0, 0)
        analytics_layout.addWidget(self.win_rate, 0, 1)
        analytics_layout.addWidget(QLabel("Profit Factor:"), 0, 2)
        analytics_layout.addWidget(self.profit_factor, 0, 3)

        analytics_layout.addWidget(QLabel("Sharpe Ratio:"), 1, 0)
        analytics_layout.addWidget(self.sharpe_ratio, 1, 1)
        analytics_layout.addWidget(QLabel("Max Drawdown:"), 1, 2)
        analytics_layout.addWidget(self.max_drawdown, 1, 3)

        analytics_layout.addWidget(QLabel("Avg Win:"), 2, 0)
        analytics_layout.addWidget(self.avg_win, 2, 1)
        analytics_layout.addWidget(QLabel("Avg Loss:"), 2, 2)
        analytics_layout.addWidget(self.avg_loss, 2, 3)

        analytics_group.setLayout(analytics_layout)
        layout.addWidget(analytics_group)

        layout.addStretch()
        self.setLayout(layout)

    def update_data(self, data):
        """Update analytics"""
        try:
            analytics = data.get('analytics', {}).get('data', {})

            self.win_rate.setText(f"{analytics.get('win_rate', 0.0):.1f}%")
            self.profit_factor.setText(f"{analytics.get('profit_factor', 0.0):.2f}")
            self.sharpe_ratio.setText(f"{analytics.get('sharpe_ratio', 0.0):.2f}")
            self.max_drawdown.setText(f"{analytics.get('max_drawdown', 0.0):.1f}%")
            self.avg_win.setText(f"${analytics.get('avg_win', 0.0):.2f}")
            self.avg_loss.setText(f"${analytics.get('avg_loss', 0.0):.2f}")

        except Exception as e:
            print(f"Error updating analytics: {e}")


class SettingsTab(QWidget):
    """Settings and bot controls"""

    def __init__(self, parent=None):
        super().__init__()
        self.parent_window = parent
        layout = QVBoxLayout()

        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Simulator controls
        simulator_group = QGroupBox("📊 Trading Simulator")
        simulator_layout = QVBoxLayout()

        sim_desc = QLabel("Generate test trades to populate the dashboard with sample data")
        sim_desc.setStyleSheet("color: #6b7280; padding: 5px;")
        simulator_layout.addWidget(sim_desc)

        sim_controls = QHBoxLayout()
        sim_controls.addWidget(QLabel("Number of trades:"))

        self.trade_count_combo = QComboBox()
        self.trade_count_combo.addItems(["10", "50", "100", "250", "500"])
        self.trade_count_combo.setCurrentText("50")
        sim_controls.addWidget(self.trade_count_combo)

        self.generate_btn = QPushButton("🎲 Generate Test Trades")
        self.generate_btn.clicked.connect(self.generate_trades)
        self.generate_btn.setStyleSheet("padding: 8px; background-color: #10b981; color: white; font-weight: bold;")
        sim_controls.addWidget(self.generate_btn)

        sim_controls.addStretch()
        simulator_layout.addLayout(sim_controls)

        simulator_group.setLayout(simulator_layout)
        layout.addWidget(simulator_group)

        # Service controls
        services_group = QGroupBox("🔧 Services Control")
        services_layout = QVBoxLayout()

        self.service_status_labels = {}
        self.service_buttons = {}

        services = [
            ("market_feed", "Market Feed", "Fetches live cryptocurrency prices"),
            ("analytics", "Analytics", "Calculates trading performance metrics"),
            ("trading_bot", "Trading Bot", "Automated trading (paper trading mode)"),
            ("simulator", "Simulator", "Trade simulation engine")
        ]

        for service_id, service_name, description in services:
            service_row = QHBoxLayout()

            # Status indicator
            status_label = QLabel("●")
            status_label.setStyleSheet("color: #6b7280; font-size: 20px;")
            service_row.addWidget(status_label)
            self.service_status_labels[service_id] = status_label

            # Service info
            info_layout = QVBoxLayout()
            name_label = QLabel(service_name)
            name_label.setStyleSheet("font-weight: bold;")
            info_layout.addWidget(name_label)
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            info_layout.addWidget(desc_label)
            service_row.addLayout(info_layout)

            service_row.addStretch()

            # Control button
            btn = QPushButton("Start")
            btn.setMinimumWidth(80)
            btn.clicked.connect(lambda checked, sid=service_id: self.toggle_service(sid))
            service_row.addWidget(btn)
            self.service_buttons[service_id] = btn

            services_layout.addLayout(service_row)

        services_group.setLayout(services_layout)
        layout.addWidget(services_group)

        # Bot configuration
        config_group = QGroupBox("🤖 Trading Bot Configuration")
        config_layout = QGridLayout()

        config_layout.addWidget(QLabel("Max Open Positions:"), 0, 0)
        self.max_positions = QSpinBox()
        self.max_positions.setRange(1, 20)
        self.max_positions.setValue(5)
        config_layout.addWidget(self.max_positions, 0, 1)

        config_layout.addWidget(QLabel("Risk Per Trade (%):"), 1, 0)
        self.risk_per_trade = QDoubleSpinBox()
        self.risk_per_trade.setRange(0.1, 10.0)
        self.risk_per_trade.setValue(2.0)
        self.risk_per_trade.setSingleStep(0.1)
        config_layout.addWidget(self.risk_per_trade, 1, 1)

        config_layout.addWidget(QLabel("Min Signal Strength:"), 2, 0)
        self.min_signal = QDoubleSpinBox()
        self.min_signal.setRange(0.1, 1.0)
        self.min_signal.setValue(0.7)
        self.min_signal.setSingleStep(0.1)
        config_layout.addWidget(self.min_signal, 2, 1)

        self.paper_trading = QCheckBox("Paper Trading Mode (No Real Trades)")
        self.paper_trading.setChecked(True)
        self.paper_trading.setStyleSheet("color: #f59e0b; font-weight: bold;")
        config_layout.addWidget(self.paper_trading, 3, 0, 1, 2)

        save_config_btn = QPushButton("💾 Save Configuration")
        save_config_btn.clicked.connect(self.save_config)
        config_layout.addWidget(save_config_btn, 4, 0, 1, 2)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Database management
        db_group = QGroupBox("🗄️ Database Management")
        db_layout = QVBoxLayout()

        db_info = QLabel(f"Database: {INSTALL_DIR / 'data' / 'trades.db'}")
        db_info.setStyleSheet("color: #6b7280; font-size: 11px;")
        db_layout.addWidget(db_info)

        db_buttons = QHBoxLayout()

        clear_db_btn = QPushButton("🗑️ Clear Database")
        clear_db_btn.clicked.connect(self.clear_database)
        clear_db_btn.setStyleSheet("background-color: #ef4444; color: white;")
        db_buttons.addWidget(clear_db_btn)

        export_btn = QPushButton("📤 Export to CSV")
        export_btn.clicked.connect(self.export_data)
        db_buttons.addWidget(export_btn)

        db_buttons.addStretch()
        db_layout.addLayout(db_buttons)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        layout.addStretch()
        self.setLayout(layout)

    def generate_trades(self):
        """Generate test trades using simulator"""
        try:
            count = int(self.trade_count_combo.currentText())
            response = requests.post(f"http://127.0.0.1:8000/api/services/simulator/generate?num_trades={count}")

            if response.status_code == 200:
                QMessageBox.information(self, "Success", f"Generated {count} test trades successfully!")
            else:
                QMessageBox.warning(self, "Error", f"Failed to generate trades: {response.text}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating trades: {str(e)}")

    def toggle_service(self, service_id):
        """Start or stop a service"""
        try:
            btn = self.service_buttons[service_id]
            action = "stop" if btn.text() == "Stop" else "start"

            response = requests.post(f"http://127.0.0.1:8000/api/services/{service_id}/{action}")

            if response.status_code == 200:
                # Button will update on next status check
                pass
            else:
                QMessageBox.warning(self, "Error", f"Failed to {action} service: {response.text}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error controlling service: {str(e)}")

    def save_config(self):
        """Save bot configuration"""
        try:
            config = {
                "max_open_positions": self.max_positions.value(),
                "risk_per_trade": self.risk_per_trade.value() / 100,
                "min_signal_strength": self.min_signal.value(),
                "paper_trading": self.paper_trading.isChecked()
            }

            # Save to file
            config_file = INSTALL_DIR / "config.json"
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)

            QMessageBox.information(self, "Success", "Configuration saved successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving config: {str(e)}")

    def clear_database(self):
        """Clear all trades from database"""
        reply = QMessageBox.question(
            self, "Confirm",
            "Are you sure you want to clear all trades? This cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                db_path = INSTALL_DIR / "data" / "trades.db"
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM trades")
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Success", "Database cleared successfully!")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error clearing database: {str(e)}")

    def export_data(self):
        """Export trades to CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Trades", "", "CSV Files (*.csv)"
            )

            if filename:
                db_path = INSTALL_DIR / "data" / "trades.db"
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM trades")
                trades = cursor.fetchall()
                conn.close()

                with open(filename, 'w') as f:
                    f.write("timestamp,symbol,side,price,size,pnl\n")
                    for trade in trades:
                        f.write(f"{trade[0]},{trade[1]},{trade[2]},{trade[3]},{trade[4]},{trade[5]}\n")

                QMessageBox.information(self, "Success", f"Exported {len(trades)} trades to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error exporting data: {str(e)}")

    def update_services_status(self, services):
        """Update service status indicators"""
        try:
            for service_id, service_data in services.get('services', {}).items():
                if service_id in self.service_status_labels:
                    status = service_data.get('status', 'stopped')
                    label = self.service_status_labels[service_id]
                    btn = self.service_buttons[service_id]

                    if status == 'running':
                        label.setStyleSheet("color: #10b981; font-size: 20px;")
                        btn.setText("Stop")
                        btn.setStyleSheet("background-color: #ef4444; color: white;")
                    else:
                        label.setStyleSheet("color: #6b7280; font-size: 20px;")
                        btn.setText("Start")
                        btn.setStyleSheet("background-color: #10b981; color: white;")

        except Exception as e:
            print(f"Error updating service status: {e}")


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JJ-Bot Trading System")
        self.setMinimumSize(1200, 800)

        # Create tabs
        self.tabs = QTabWidget()

        self.dashboard_tab = DashboardTab()
        self.market_tab = MarketDataTab()
        self.trades_tab = TradesTab()
        self.analytics_tab = AnalyticsTab()
        self.settings_tab = SettingsTab(self)

        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.market_tab, "💰 Market")
        self.tabs.addTab(self.trades_tab, "📈 Trades")
        self.tabs.addTab(self.analytics_tab, "📊 Analytics")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        self.setCentralWidget(self.tabs)

        # Create toolbar (after tabs are created)
        self.create_toolbar()

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Waiting for data...")

        # Data updater
        self.updater = DataUpdater()
        self.updater.data_updated.connect(self.on_data_updated)
        self.updater.services_updated.connect(self.on_services_updated)

        # System tray
        self.setup_tray()

    def create_toolbar(self):
        """Create quick actions toolbar"""
        toolbar = QToolBar("Quick Actions")
        toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(toolbar)

        # Refresh action
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)

        toolbar.addSeparator()

        # Generate trades action
        generate_action = QAction("🎲 Generate Trades", self)
        generate_action.triggered.connect(self.quick_generate_trades)
        toolbar.addAction(generate_action)

        toolbar.addSeparator()

        # Export action
        export_action = QAction("📤 Export CSV", self)
        export_action.triggered.connect(self.settings_tab.export_data)
        toolbar.addAction(export_action)

        toolbar.addSeparator()

        # Clear database action
        clear_action = QAction("🗑️ Clear Data", self)
        clear_action.triggered.connect(self.settings_tab.clear_database)
        toolbar.addAction(clear_action)

    def refresh_data(self):
        """Force refresh data"""
        self.status_bar.showMessage("Refreshing data...")
        # Data will refresh automatically via updater

    def quick_generate_trades(self):
        """Quick generate 50 trades"""
        try:
            response = requests.post("http://127.0.0.1:8000/api/services/simulator/generate?num_trades=50")
            if response.status_code == 200:
                self.status_bar.showMessage("Generated 50 test trades!", 5000)
                QMessageBox.information(self, "Success", "Generated 50 test trades!")
            else:
                QMessageBox.warning(self, "Error", f"Failed to generate trades: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error: {str(e)}")

    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("JJ-Bot Trading System")

        # Create tray menu
        tray_menu = QMenu()

        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("Hide Window", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        tray_menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        """Handle tray icon clicks"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    def closeEvent(self, event):
        """Minimize to tray instead of closing"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "JJ-Bot",
            "Application minimized to tray",
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )

    def quit_app(self):
        """Actually quit the application"""
        self.updater.stop()
        QApplication.quit()

    def on_data_updated(self, data):
        """Handle data updates"""
        self.dashboard_tab.update_data(data)
        self.market_tab.update_data(data)
        self.trades_tab.update_data(data)
        self.analytics_tab.update_data(data)

        total_trades = data.get('summary', {}).get('total_trades', 0)
        self.status_bar.showMessage(f"Last update: {datetime.now().strftime('%H:%M:%S')} | Trades: {total_trades}")

    def on_services_updated(self, services):
        """Handle services status updates"""
        self.settings_tab.update_services_status(services)
        self.dashboard_tab.update_services_count(services)

    def start_updates(self):
        """Start data updates"""
        self.updater.start()


def main():
    """Main entry point"""

    # Initialize database
    engine.init_db()

    # Start API in background thread
    def start_api():
        import uvicorn
        from glue.api.main import app
        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    # Wait for API to start
    print("Starting API server...")
    time.sleep(3)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("JJ-Bot Trading System")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Create and show main window
    window = MainWindow()
    window.show()
    window.start_updates()

    print("JJ-Bot GUI started successfully!")
    print("Access the application from the window or system tray")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
