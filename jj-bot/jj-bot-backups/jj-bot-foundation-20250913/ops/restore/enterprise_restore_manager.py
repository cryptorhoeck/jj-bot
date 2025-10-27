import os
import shutil
import tarfile
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

class EnterpriseRestoreManager:
    """Enterprise-grade restore system"""
    
    def __init__(self):
        self.project_root = Path.home() / "jj-bot"
        self.backup_root = self.project_root.parent / "jj-bot-enterprise-backups"
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for restore operations"""
        log_dir = self.project_root / "ops" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "restore.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def list_available_backups(self) -> List[Dict]:
        """List all available backups for restore"""
        from ops.backup.enterprise_backup_manager import backup_manager
        return backup_manager.list_backups()
    
    def restore_from_backup(self, backup_id: str, restore_options: Dict = None) -> Dict:
        """Restore system from a specific backup"""
        try:
            self.logger.info(f"Starting restore from backup: {backup_id}")
            
            # Get backup information
            from ops.backup.enterprise_backup_manager import backup_manager
            backup_info = backup_manager.get_backup_info(backup_id)
            
            if not backup_info:
                raise ValueError(f"Backup not found: {backup_id}")
            
            # Default restore options
            if restore_options is None:
                restore_options = {
                    'restore_database': True,
                    'restore_config': True,
                    'restore_code': True,
                    'restore_logs': False,
                    'backup_current': True,
                    'verify_restore': True
                }
            
            restore_metadata = {
                'restore_id': datetime.now().strftime('%Y%m%d_%H%M%S'),
                'backup_id': backup_id,
                'backup_info': backup_info,
                'restore_options': restore_options,
                'timestamp': datetime.now().isoformat(),
                'status': 'in_progress',
                'steps_completed': [],
                'errors': []
            }
            
            # Step 1: Create backup of current system (if requested)
            if restore_options.get('backup_current', True):
                self.logger.info("Creating backup of current system before restore...")
                current_backup = backup_manager.create_backup(
                    backup_type='full',
                    description=f"Pre-restore backup before restoring {backup_id}"
                )
                restore_metadata['current_backup'] = current_backup
                restore_metadata['steps_completed'].append('current_backup')
            
            # Step 2: Stop running services
            self.logger.info("Stopping services...")
            self._stop_services()
            restore_metadata['steps_completed'].append('stop_services')
            
            # Step 3: Extract/prepare backup
            backup_path = self._prepare_backup_for_restore(backup_info)
            restore_metadata['steps_completed'].append('prepare_backup')
            
            # Step 4: Restore files based on options
            if restore_options.get('restore_code', True):
                self.logger.info("Restoring code files...")
                self._restore_code_files(backup_path)
                restore_metadata['steps_completed'].append('restore_code')
            
            if restore_options.get('restore_config', True):
                self.logger.info("Restoring configuration files...")
                self._restore_config_files(backup_path)
                restore_metadata['steps_completed'].append('restore_config')
            
            if restore_options.get('restore_database', True):
                self.logger.info("Restoring database...")
                self._restore_database(backup_path)
                restore_metadata['steps_completed'].append('restore_database')
            
            # Step 5: Verify restore (if requested)
            if restore_options.get('verify_restore', True):
                self.logger.info("Verifying restore...")
                verification_result = self._verify_restore(backup_info, restore_options)
                restore_metadata['verification'] = verification_result
                restore_metadata['steps_completed'].append('verify_restore')
            
            # Step 6: Restart services
            self.logger.info("Restarting services...")
            self._restart_services()
            restore_metadata['steps_completed'].append('restart_services')
            
            restore_metadata['status'] = 'completed'
            restore_metadata['duration'] = (datetime.now() - datetime.fromisoformat(restore_metadata['timestamp'])).total_seconds()
            
            # Save restore log
            self._save_restore_log(restore_metadata)
            
            self.logger.info(f"Restore completed successfully: {backup_id}")
            return restore_metadata
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            restore_metadata['status'] = 'failed'
            restore_metadata['error'] = str(e)
            restore_metadata['errors'].append(str(e))
            
            # Attempt to restart services even if restore failed
            try:
                self._restart_services()
            except:
                pass
            
            return restore_metadata
    
    def _prepare_backup_for_restore(self, backup_info: Dict) -> Path:
        """Prepare backup for restore (extract if compressed)"""
        backup_name = backup_info['name']
        backup_path = self.backup_root / backup_name
        
        # If it's a compressed archive, extract it
        archive_path = self.backup_root / f"{backup_name}.tar.gz"
        if archive_path.exists() and not backup_path.exists():
            self.logger.info(f"Extracting compressed backup: {archive_path}")
            
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=self.backup_root)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup path not found: {backup_path}")
        
        return backup_path
    
    def _restore_code_files(self, backup_path: Path):
        """Restore source code files"""
        exclude_patterns = ['data', 'ops/logs', '.venv', '__pycache__', 'node_modules']
        
        for item in backup_path.iterdir():
            if item.name in exclude_patterns:
                continue
                
            dest_path = self.project_root / item.name
            
            if item.is_file():
                shutil.copy2(item, dest_path)
            elif item.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(item, dest_path)
    
    def _restore_config_files(self, backup_path: Path):
        """Restore configuration files"""
        config_files = [
            'config.json',
            'requirements.txt'
        ]
        
        for config_file in config_files:
            src_path = backup_path / config_file
            if src_path.exists():
                dest_path = self.project_root / config_file
                shutil.copy2(src_path, dest_path)
        
        # Restore ops configs if they exist
        ops_backup = backup_path / 'ops'
        if ops_backup.exists():
            for config_file in ops_backup.rglob('*.json'):
                relative_path = config_file.relative_to(ops_backup)
                dest_path = self.project_root / 'ops' / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(config_file, dest_path)
        
        # Restore data configs if they exist
        data_backup = backup_path / 'data'
        if data_backup.exists():
            data_dir = self.project_root / 'data'
            data_dir.mkdir(exist_ok=True)
            
            for config_file in data_backup.glob('*.json'):
                dest_path = data_dir / config_file.name
                shutil.copy2(config_file, dest_path)
    
    def _restore_database(self, backup_path: Path):
        """Restore database files"""
        # Restore main database
        src_db = backup_path / 'trades.db'
        if src_db.exists():
            dest_db = self.project_root / 'data' / 'trades.db'
            dest_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_db, dest_db)
        
        # Check for database in subdirectory (from database-only backups)
        db_subdir = backup_path / 'database'
        if db_subdir.exists():
            src_db = db_subdir / 'trades.db'
            if src_db.exists():
                dest_db = self.project_root / 'data' / 'trades.db'
                dest_db.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_db, dest_db)
    
    def _verify_restore(self, backup_info: Dict, restore_options: Dict) -> Dict:
        """Verify that restore was successful"""
        verification = {
            'timestamp': datetime.now().isoformat(),
            'passed': True,
            'checks': {}
        }
        
        try:
            # Check if key files exist
            key_files = ['glue/api/main.py', 'jj', 'config.json']
            for file_path in key_files:
                file_exists = (self.project_root / file_path).exists()
                verification['checks'][f'file_{file_path}'] = file_exists
                if not file_exists:
                    verification['passed'] = False
            
            # Check database if restored
            if restore_options.get('restore_database', True):
                db_path = self.project_root / 'data' / 'trades.db'
                db_exists = db_path.exists()
                verification['checks']['database_exists'] = db_exists
                
                if db_exists:
                    # Try to connect and query
                    try:
                        with sqlite3.connect(db_path) as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM trades")
                            trade_count = cursor.fetchone()[0]
                            verification['checks']['database_accessible'] = True
                            verification['checks']['trade_count'] = trade_count
                    except Exception as e:
                        verification['checks']['database_accessible'] = False
                        verification['checks']['database_error'] = str(e)
                        verification['passed'] = False
                else:
                    verification['passed'] = False
            
            # Check configuration files
            config_files = ['config.json', 'requirements.txt']
            for config_file in config_files:
                config_exists = (self.project_root / config_file).exists()
                verification['checks'][f'config_{config_file}'] = config_exists
                if not config_exists:
                    verification['passed'] = False
        
        except Exception as e:
            verification['passed'] = False
            verification['error'] = str(e)
        
        return verification
    
    def _stop_services(self):
        """Stop running JJ-Bot services"""
        try:
            # Kill any uvicorn processes
            os.system("pkill -f 'uvicorn.*main:app' 2>/dev/null || true")
            
            # Kill any JJ-Bot related processes
            os.system("pkill -f 'jj_master_control' 2>/dev/null || true")
            os.system("pkill -f 'sim_trader' 2>/dev/null || true")
            os.system("pkill -f 'live_trader' 2>/dev/null || true")
            
            # Wait a moment for processes to stop
            import time
            time.sleep(2)
            
        except Exception as e:
            self.logger.warning(f"Error stopping services: {e}")
    
    def _restart_services(self):
        """Restart JJ-Bot services"""
        try:
            # Change to project directory
            os.chdir(self.project_root)
            
            # Activate virtual environment and restart API
            restart_cmd = f"""
            cd {self.project_root}
            source .venv/bin/activate
            nohup uvicorn glue.api.main:app --host 0.0.0.0 --port 8000 --reload > ops/logs/glue.log 2>&1 &
            """
            
            os.system(restart_cmd)
            
            # Wait for services to start
            import time
            time.sleep(3)
            
        except Exception as e:
            self.logger.error(f"Error restarting services: {e}")
    
    def _save_restore_log(self, restore_metadata: Dict):
        """Save restore operation log"""
        log_dir = self.project_root / "ops" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = log_dir / f"restore_{restore_metadata['restore_id']}.json"
        
        with open(log_file, 'w') as f:
            json.dump(restore_metadata, f, indent=2)
    
    def get_restore_history(self) -> List[Dict]:
        """Get history of all restore operations"""
        log_dir = self.project_root / "ops" / "logs"
        restore_logs = []
        
        if log_dir.exists():
            for log_file in log_dir.glob("restore_*.json"):
                try:
                    with open(log_file, 'r') as f:
                        restore_log = json.load(f)
                        restore_logs.append(restore_log)
                except Exception as e:
                    self.logger.error(f"Error reading restore log {log_file}: {e}")
        
        # Sort by timestamp (newest first)
        restore_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return restore_logs
    
    def quick_restore_database(self, backup_id: str) -> Dict:
        """Quick restore of just the database from a backup"""
        return self.restore_from_backup(backup_id, {
            'restore_database': True,
            'restore_config': False,
            'restore_code': False,
            'restore_logs': False,
            'backup_current': True,
            'verify_restore': True
        })
    
    def quick_restore_config(self, backup_id: str) -> Dict:
        """Quick restore of just configuration from a backup"""
        return self.restore_from_backup(backup_id, {
            'restore_database': False,
            'restore_config': True,
            'restore_code': False,
            'restore_logs': False,
            'backup_current': True,
            'verify_restore': True
        })

# Global restore manager instance
restore_manager = EnterpriseRestoreManager()
