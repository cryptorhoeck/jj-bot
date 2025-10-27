import asyncio
import psutil
import time
from datetime import datetime, timedelta
import json
from pathlib import Path
import logging

class SystemMonitor:
    """Comprehensive system monitoring for JJ-Bot"""
    
    def __init__(self):
        self.log_file = Path.home() / "jj-bot" / "ops" / "logs" / "system_monitor.log"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.start_time = datetime.now()
        self.metrics_history = []
        
    def get_system_metrics(self):
        """Get comprehensive system metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network
            network = psutil.net_io_counters()
            
            # Process info
            current_process = psutil.Process()
            process_memory = current_process.memory_info()
            
            # JJ-Bot specific metrics
            uptime = datetime.now() - self.start_time
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'system': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_used_gb': memory.used / (1024**3),
                    'memory_total_gb': memory.total / (1024**3),
                    'disk_percent': disk.percent,
                    'disk_free_gb': disk.free / (1024**3)
                },
                'network': {
                    'bytes_sent': network.bytes_sent,
                    'bytes_recv': network.bytes_recv,
                    'packets_sent': network.packets_sent,
                    'packets_recv': network.packets_recv
                },
                'process': {
                    'memory_mb': process_memory.rss / (1024**2),
                    'cpu_percent': current_process.cpu_percent(),
                    'threads': current_process.num_threads(),
                    'connections': len(current_process.connections())
                },
                'jj_bot': {
                    'uptime_seconds': uptime.total_seconds(),
                    'uptime_formatted': str(uptime).split('.')[0]
                }
            }
            
            # Add to history
            self.metrics_history.append(metrics)
            
            # Keep only last 100 entries
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]
                
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return None
    
    def check_health(self):
        """Check system health and return warnings"""
        metrics = self.get_system_metrics()
        if not metrics:
            return ['Failed to get system metrics']
        
        warnings = []
        
        # Check resource usage
        if metrics['system']['cpu_percent'] > 80:
            warnings.append(f"High CPU usage: {metrics['system']['cpu_percent']:.1f}%")
        
        if metrics['system']['memory_percent'] > 85:
            warnings.append(f"High memory usage: {metrics['system']['memory_percent']:.1f}%")
        
        if metrics['system']['disk_percent'] > 90:
            warnings.append(f"Low disk space: {metrics['system']['disk_percent']:.1f}% used")
        
        if metrics['process']['memory_mb'] > 500:
            warnings.append(f"JJ-Bot using high memory: {metrics['process']['memory_mb']:.1f}MB")
        
        # Check if system is responsive
        if metrics['system']['cpu_percent'] > 95:
            warnings.append("System may be overloaded")
        
        return warnings
    
    def get_performance_summary(self):
        """Get performance summary over time"""
        if len(self.metrics_history) < 2:
            return None
        
        recent_metrics = self.metrics_history[-10:]  # Last 10 readings
        
        avg_cpu = sum(m['system']['cpu_percent'] for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m['system']['memory_percent'] for m in recent_metrics) / len(recent_metrics)
        
        return {
            'avg_cpu_10min': avg_cpu,
            'avg_memory_10min': avg_memory,
            'current_uptime': recent_metrics[-1]['jj_bot']['uptime_formatted'],
            'total_readings': len(self.metrics_history),
            'monitoring_since': self.start_time.isoformat()
        }
    
    async def start_monitoring(self, interval=60):
        """Start continuous system monitoring"""
        self.logger.info("System monitoring started")
        print("🖥️ System monitoring started")
        
        while True:
            try:
                metrics = self.get_system_metrics()
                warnings = self.check_health()
                
                if warnings:
                    for warning in warnings:
                        self.logger.warning(warning)
                        print(f"⚠️ {warning}")
                
                # Log metrics periodically
                if len(self.metrics_history) % 10 == 0:  # Every 10 minutes
                    self.logger.info(f"System metrics: CPU {metrics['system']['cpu_percent']:.1f}%, "
                                   f"Memory {metrics['system']['memory_percent']:.1f}%, "
                                   f"JJ-Bot Memory {metrics['process']['memory_mb']:.1f}MB")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(interval)

# Global system monitor
system_monitor = SystemMonitor()
