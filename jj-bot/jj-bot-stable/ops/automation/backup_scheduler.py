import asyncio
import schedule
import time
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
from pathlib import Path
import json

class EnterpriseBackupScheduler:
    """Automated backup scheduling system"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.logger = self.setup_logging()
        self.config = self.load_scheduler_config()
        self.is_running = False
        
    def setup_logging(self):
        """Setup logging for scheduler"""
        log_dir = Path.home() / "jj-bot" / "ops" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "scheduler.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def load_scheduler_config(self):
        """Load scheduler configuration"""
        config_file = Path.home() / "jj-bot" / "ops" / "scheduler_config.json"
        
        default_config = {
            "enabled": True,
            "schedules": {
                "hourly_backup": {
                    "enabled": True,
                    "cron": "0 * * * *",  # Every hour
                    "backup_type": "incremental",
                    "description": "Hourly incremental backup"
                },
                "daily_backup": {
                    "enabled": True,
                    "cron": "0 2 * * *",  # 2 AM daily
                    "backup_type": "full",
                    "description": "Daily full backup"
                },
                "weekly_backup": {
                    "enabled": True,
                    "cron": "0 3 * * 0",  # 3 AM Sunday
                    "backup_type": "full",
                    "description": "Weekly full backup"
                },
                "database_backup": {
                    "enabled": True,
                    "cron": "0 */6 * * *",  # Every 6 hours
                    "backup_type": "database",
                    "description": "Database backup every 6 hours"
                }
            },
            "notifications": {
                "on_success": True,
                "on_failure": True,
                "on_cleanup": False
            },
            "cleanup": {
                "enabled": True,
                "cron": "0 4 * * *",  # 4 AM daily
                "retention_days": 30
            }
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                self.logger.error(f"Error loading scheduler config: {e}")
                return default_config
        else:
            self.save_scheduler_config(default_config)
            return default_config
    
    def save_scheduler_config(self, config=None):
        """Save scheduler configuration"""
        if config:
            self.config = config
            
        config_file = Path.home() / "jj-bot" / "ops" / "scheduler_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    async def create_scheduled_backup(self, backup_type: str, description: str):
        """Create a scheduled backup"""
        try:
            self.logger.info(f"Starting scheduled {backup_type} backup: {description}")
            
            # Import backup manager
            import sys
            sys.path.append(str(Path.home() / "jj-bot"))
            from ops.backup.enterprise_backup_manager import backup_manager
            
            # Create backup
            result = backup_manager.create_backup(backup_type, f"Scheduled: {description}")
            
            if result['status'] == 'completed':
                self.logger.info(f"Scheduled backup completed: {result['name']} ({result['size_human']})")
                
                # Send success notification if enabled
                if self.config['notifications']['on_success']:
                    await self.send_backup_notification("success", result)
                    
            else:
                self.logger.error(f"Scheduled backup failed: {result.get('error', 'Unknown error')}")
                
                # Send failure notification if enabled
                if self.config['notifications']['on_failure']:
                    await self.send_backup_notification("failure", result)
                    
        except Exception as e:
            self.logger.error(f"Error in scheduled backup: {e}")
            
            # Send failure notification
            if self.config['notifications']['on_failure']:
                await self.send_backup_notification("error", {"error": str(e), "backup_type": backup_type})
    
    async def cleanup_old_backups(self):
        """Clean up old backups"""
        try:
            self.logger.info("Starting scheduled backup cleanup")
            
            import sys
            sys.path.append(str(Path.home() / "jj-bot"))
            from ops.backup.enterprise_backup_manager import backup_manager
            
            # Get all backups
            all_backups = backup_manager.list_backups()
            retention_days = self.config['cleanup']['retention_days']
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            cleaned_count = 0
            for backup in all_backups:
                backup_date = datetime.fromisoformat(backup['timestamp'])
                if backup_date < cutoff_date:
                    # Remove old backup
                    backup_path = backup_manager.backup_root / backup['name']
                    if backup_path.exists():
                        if backup_path.is_dir():
                            import shutil
                            shutil.rmtree(backup_path)
                        else:
                            backup_path.unlink()
                        cleaned_count += 1
                        self.logger.info(f"Removed old backup: {backup['name']}")
            
            self.logger.info(f"Cleanup completed: {cleaned_count} old backups removed")
            
            if self.config['notifications']['on_cleanup'] and cleaned_count > 0:
                await self.send_cleanup_notification(cleaned_count, retention_days)
                
        except Exception as e:
            self.logger.error(f"Error in backup cleanup: {e}")
    
    async def send_backup_notification(self, status: str, backup_info: dict):
        """Send backup notification"""
        try:
            import sys
            sys.path.append(str(Path.home() / "jj-bot"))
            from hands.notifications.notification_manager import notification_manager
            
            if status == "success":
                message = f"✅ Scheduled backup completed successfully!\n\nBackup: {backup_info['name']}\nSize: {backup_info['size_human']}\nType: {backup_info['type'].upper()}"
                await notification_manager.send_alert("backup_success", message, backup_info)
            
            elif status == "failure":
                message = f"❌ Scheduled backup failed!\n\nError: {backup_info.get('error', 'Unknown error')}\nType: {backup_info.get('type', 'Unknown')}"
                await notification_manager.send_alert("backup_failure", message, backup_info)
            
            elif status == "error":
                message = f"❌ Backup system error!\n\nError: {backup_info['error']}\nType: {backup_info['backup_type']}"
                await notification_manager.send_alert("system_errors", message, backup_info)
                
        except Exception as e:
            self.logger.error(f"Error sending backup notification: {e}")
    
    async def send_cleanup_notification(self, cleaned_count: int, retention_days: int):
        """Send cleanup notification"""
        try:
            import sys
            sys.path.append(str(Path.home() / "jj-bot"))
            from hands.notifications.notification_manager import notification_manager
            
            message = f"🧹 Backup cleanup completed!\n\nRemoved: {cleaned_count} old backups\nRetention: {retention_days} days"
            await notification_manager.send_alert("backup_cleanup", message, {"cleaned_count": cleaned_count})
            
        except Exception as e:
            self.logger.error(f"Error sending cleanup notification: {e}")
    
    def start_scheduler(self):
        """Start the backup scheduler"""
        if not self.config['enabled']:
            self.logger.info("Scheduler is disabled in configuration")
            return
        
        self.logger.info("Starting Enterprise Backup Scheduler...")
        
        # Add backup jobs
        for job_name, job_config in self.config['schedules'].items():
            if job_config['enabled']:
                self.scheduler.add_job(
                    self.create_scheduled_backup,
                    CronTrigger.from_crontab(job_config['cron']),
                    args=[job_config['backup_type'], job_config['description']],
                    id=job_name,
                    name=job_config['description']
                )
                self.logger.info(f"Scheduled job: {job_name} ({job_config['cron']})")
        
        # Add cleanup job
        if self.config['cleanup']['enabled']:
            self.scheduler.add_job(
                self.cleanup_old_backups,
                CronTrigger.from_crontab(self.config['cleanup']['cron']),
                id='backup_cleanup',
                name='Backup Cleanup'
            )
            self.logger.info(f"Scheduled cleanup job: {self.config['cleanup']['cron']}")
        
        # Start scheduler
        self.scheduler.start()
        self.is_running = True
        self.logger.info("Enterprise Backup Scheduler started successfully")
    
    def stop_scheduler(self):
        """Stop the backup scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("Enterprise Backup Scheduler stopped")
    
    def get_job_status(self):
        """Get status of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'enabled': True
            })
        
        return {
            'scheduler_running': self.is_running,
            'total_jobs': len(jobs),
            'jobs': jobs
        }
    
    async def run_scheduler_service(self):
        """Run scheduler as a service"""
        self.start_scheduler()
        
        try:
            while self.is_running:
                await asyncio.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler service interrupted")
        finally:
            self.stop_scheduler()

# Global scheduler instance
backup_scheduler = EnterpriseBackupScheduler()
