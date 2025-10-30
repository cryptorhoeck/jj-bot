"""
JJ-Bot Native Windows GUI Application
Professional PyQt6 interface for cryptocurrency trading bot
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QTableWidget, QTableWidgetItem, QPushButton,
    QSystemTrayIcon, QMenu, QGroupBox, QGridLayout, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QHeaderView, QStatusBar
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt6.QtGui import QIcon, QAction, QColor, QPainter
import requests

# Get installation directory
INSTALL_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(INSTALL_DIR))

# Import local modules
from glue.api import engine


class DataUpdater(QObject):
    """Background thread for fetching API data"""
    data_updated = pyqtSignal(dict)

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
            except Exception as e:
                print(f"Error fetching data: {e}")

            time.sleep(2)


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

        # Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(200)
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

            # Add to activity log
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.activity_log.append(f"[{timestamp}] Updated: {summary.get('total_trades', 0)} trades, P&L: ${total_pnl:.2f}")

        except Exception as e:
            print(f"Error updating dashboard: {e}")


class MarketDataTab(QWidget):
    """Market data with live prices"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("💰 Market Data")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

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
                else:
                    change_item.setForeground(QColor("#ef4444"))
                self.table.setItem(row, 2, change_item)

                # Last Update
                timestamp = price_data.get('timestamp', datetime.now().isoformat())
                time_str = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).strftime("%H:%M:%S")
                self.table.setItem(row, 3, QTableWidgetItem(time_str))

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

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()

        # Title
        title = QLabel("⚙️ Settings")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        layout.addWidget(title)

        # Bot controls
        bot_group = QGroupBox("Trading Bot Controls")
        bot_layout = QVBoxLayout()

        self.bot_enabled = QCheckBox("Enable Trading Bot (Paper Trading)")
        self.bot_enabled.setChecked(False)
        bot_layout.addWidget(self.bot_enabled)

        warning = QLabel("⚠️ Bot is in PAPER TRADING mode. No real trades will be executed.")
        warning.setStyleSheet("color: #f59e0b; padding: 10px;")
        bot_layout.addWidget(warning)

        bot_group.setLayout(bot_layout)
        layout.addWidget(bot_group)

        # Services status
        services_group = QGroupBox("Services Status")
        services_layout = QVBoxLayout()

        self.services_status = QTextEdit()
        self.services_status.setReadOnly(True)
        self.services_status.setMaximumHeight(150)
        services_layout.addWidget(self.services_status)

        services_group.setLayout(services_layout)
        layout.addWidget(services_group)

        layout.addStretch()
        self.setLayout(layout)

    def update_data(self, data):
        """Update settings"""
        # Could update service status here
        pass


class MainWindow(QMainWindow):
    """Main application window"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("JJ-Bot Trading System")
        self.setMinimumSize(1000, 700)

        # Create tabs
        self.tabs = QTabWidget()

        self.dashboard_tab = DashboardTab()
        self.market_tab = MarketDataTab()
        self.trades_tab = TradesTab()
        self.analytics_tab = AnalyticsTab()
        self.settings_tab = SettingsTab()

        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.market_tab, "Market Data")
        self.tabs.addTab(self.trades_tab, "Trades")
        self.tabs.addTab(self.analytics_tab, "Analytics")
        self.tabs.addTab(self.settings_tab, "Settings")

        self.setCentralWidget(self.tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Data updater
        self.updater = DataUpdater()
        self.updater.data_updated.connect(self.on_data_updated)

        # System tray
        self.setup_tray()

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
        self.settings_tab.update_data(data)

        self.status_bar.showMessage(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

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
    time.sleep(2)

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("JJ-Bot Trading System")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    # Create and show main window
    window = MainWindow()
    window.show()
    window.start_updates()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
