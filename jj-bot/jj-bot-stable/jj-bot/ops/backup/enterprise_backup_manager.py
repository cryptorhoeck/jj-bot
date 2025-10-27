import os
import shutil
import tarfile
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

class EnterpriseBackupManager:
    """Enterprise-grade backup and restore system"""
    
    def __init__(self):
        self.project_root = Path.home() / "jj-bot"
        self.backup_root = self.project_root.parent / "jj-bot-enterprise-backups"
        self.backup_root.mkdir(exist_ok=True)
        
        # Backup configuration
        self.config = self.load_backup_config()
        
        # Setup logging
        self.setup_logging()
        
        # Backup types
        self.backup_types = {
            'full': 'Complete system backup',
            'incremental': 'Changed files only',
            'database': 'Database and trades only',
            'config': 'Configuration files only',
            'code': 'Source code only'
        }
        
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_dir = self.project_root / "ops" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "backup.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_backup_config(self):
        """Load backup configuration"""
        config_file = self.project_root / "ops" / "backup_config.json"
        
        default_config = {
            "retention": {
                "hourly": 24,      # Keep 24 hourly backups
                "daily": 30,       # Keep 30 daily backups  
                "weekly": 12,      # Keep 12 weekly backups
                "monthly": 12      # Keep 12 monthly backups
            },
            "schedule": {
                "hourly": "0 * * * *",      # Every hour
                "daily": "0 2 * * *",       # 2 AM daily
                "weekly": "0 3 * * 0",      # 3 AM Sunday
                "monthly": "0 4 1 * *"      # 4 AM 1st of month
            },
            "compression": True,
            "encryption": False,
            "verify_backups": True,
            "cleanup_old_backups": True,
            "backup_locations": {
                "local": str(self.backup_root),
                "remote": None  # Could add S3, FTP, etc.
            },
            "exclude_patterns": [
                "*.pyc", "__pycache__", ".git", "node_modules", 
                ".venv", "*.log", "dist", "build"
            ],
            "include_database": True,
            "include_logs": False,
            "max_backup_size_gb": 10
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                self.logger.error(f"Error loading backup config: {e}")
                return default_config
        else:
            self.save_backup_config(default_config)
            return default_config
    
    def save_backup_config(self, config=None):
        """Save backup configuration"""
        if config:
            self.config = config
            
        config_file = self.project_root / "ops" / "backup_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def create_backup(self, backup_type: str = 'full', description: str = None) -> Dict:
        """Create a new backup"""
        try:
            self.logger.info(f"Starting {backup_type} backup...")
            
            # Generate backup metadata
            timestamp = datetime.now()
            backup_id = timestamp.strftime('%Y%m%d_%H%M%S')
            backup_name = f"jj-bot-{backup_type}-{backup_id}"
            
            # Create backup directory
            backup_dir = self.backup_root / backup_name
            backup_dir.mkdir(exist_ok=True)
            
            # Backup metadata
            metadata = {
                'id': backup_id,
                'name': backup_name,
                'type': backup_type,
                'description': description or f"Automated {backup_type} backup",
                'timestamp': timestamp.isoformat(),
                'size_bytes': 0,
                'files_count': 0,
                'checksum': None,
                'status': 'in_progress',
                'duration_seconds': 0,
                'version': self.get_system_version()
            }
            
            start_time = datetime.now()
            
            # Perform backup based on type
            if backup_type == 'full':
                files_backed_up = self._backup_full_system(backup_dir)
            elif backup_type == 'incremental':
                files_backed_up = self._backup_incremental(backup_dir)
            elif backup_type == 'database':
                files_backed_up = self._backup_database_only(backup_dir)
            elif backup_type == 'config':
                files_backed_up = self._backup_config_only(backup_dir)
            elif backup_type == 'code':
                files_backed_up = self._backup_code_only(backup_dir)
            else:
                raise ValueError(f"Unknown backup type: {backup_type}")
            
            # Calculate backup size and checksum
            total_size = self._calculate_directory_size(backup_dir)
            checksum = self._calculate_directory_checksum(backup_dir)
            
            # Update metadata
            end_time = datetime.now()
            metadata.update({
                'size_bytes': total_size,
                'size_human': self._format_bytes(total_size),
                'files_count': files_backed_up,
                'checksum': checksum,
                'status': 'completed',
                'duration_seconds': (end_time - start_time).total_seconds()
            })
            
            # Save metadata
            metadata_file = backup_dir / 'backup_metadata.json'
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create compressed archive if enabled
            if self.config.get('compression', True):
                archive_path = self._create_compressed_archive(backup_dir)
                metadata['archive_path'] = str(archive_path)
                metadata['compressed'] = True
                
                # Update metadata file in archive
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Verify backup if enabled
            if self.config.get('verify_backups', True):
                verification_result = self._verify_backup(backup_dir, metadata)
                metadata['verified'] = verification_result
            
            # Cleanup old backups if enabled
            if self.config.get('cleanup_old_backups', True):
                self._cleanup_old_backups(backup_type)
            
            self.logger.info(f"Backup completed: {backup_name}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            metadata['status'] = 'failed'
            metadata['error'] = str(e)
            return metadata
    
    def _backup_full_system(self, backup_dir: Path) -> int:
        """Backup entire system"""
        files_count = 0
        exclude_patterns = self.config.get('exclude_patterns', [])
        
        # Copy project files
        for item in self.project_root.iterdir():
            if item.name in ['.venv', '__pycache__', '.git']:
                continue
                
            if item.is_file():
                if not any(item.match(pattern) for pattern in exclude_patterns):
                    shutil.copy2(item, backup_dir / item.name)
                    files_count += 1
            elif item.is_dir():
                dest_dir = backup_dir / item.name
                files_count += self._copy_directory(item, dest_dir, exclude_patterns)
        
        # Backup database separately
        if self.config.get('include_database', True):
            self._backup_database(backup_dir)
            files_count += 1
        
        return files_count
    
    def _backup_incremental(self, backup_dir: Path) -> int:
        """Backup only changed files since last backup"""
        # Find last backup
        last_backup = self._get_last_backup('incremental')
        last_backup_time = datetime.now() - timedelta(hours=1)  # Default 1 hour
        
        if last_backup:
            last_backup_time = datetime.fromisoformat(last_backup['timestamp'])
        
        files_count = 0
        
        # Only backup files modified since last backup
        for item in self.project_root.rglob('*'):
            if item.is_file():
                if item.stat().st_mtime > last_backup_time.timestamp():
                    relative_path = item.relative_to(self.project_root)
                    dest_file = backup_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
                    files_count += 1
        
        return files_count
    
    def _backup_database_only(self, backup_dir: Path) -> int:
        """Backup only database and trade data"""
        db_backup_dir = backup_dir / "database"
        db_backup_dir.mkdir(exist_ok=True)
        
        files_count = 0
        
        # Backup SQLite database
        db_path = self.project_root / "data" / "trades.db"
        if db_path.exists():
            shutil.copy2(db_path, db_backup_dir / "trades.db")
            files_count += 1
            
            # Export database to SQL
            self._export_database_to_sql(db_path, db_backup_dir / "trades_export.sql")
            files_count += 1
        
        # Backup any other data files
        data_dir = self.project_root / "data"
        if data_dir.exists():
            for item in data_dir.iterdir():
                if item.is_file() and item.suffix in ['.json', '.csv', '.txt']:
                    shutil.copy2(item, db_backup_dir / item.name)
                    files_count += 1
        
        return files_count
    
    def _backup_config_only(self, backup_dir: Path) -> int:
        """Backup only configuration files"""
        config_backup_dir = backup_dir / "config"
        config_backup_dir.mkdir(exist_ok=True)
        
        files_count = 0
        config_files = [
            "config.json",
            "requirements.txt",
            "ops/backup_config.json",
            "data/notification_config.json",
            "data/strategy_config.json",
            "data/risk_config.json"
        ]
        
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                dest_path = config_backup_dir / file_path.name
                shutil.copy2(file_path, dest_path)
                files_count += 1
        
        return files_count
    
    def _backup_code_only(self, backup_dir: Path) -> int:
        """Backup only source code files"""
        code_backup_dir = backup_dir / "code"
        code_backup_dir.mkdir(exist_ok=True)
        
        files_count = 0
        code_extensions = ['.py', '.jsx', '.js', '.html', '.css', '.json', '.md']
        
        for item in self.project_root.rglob('*'):
            if item.is_file() and item.suffix in code_extensions:
                if 'node_modules' not in str(item) and '.venv' not in str(item):
                    relative_path = item.relative_to(self.project_root)
                    dest_file = code_backup_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
                    files_count += 1
        
        return files_count
    
    def _copy_directory(self, src: Path, dest: Path, exclude_patterns: List[str]) -> int:
        """Recursively copy directory with exclusions"""
        files_count = 0
        dest.mkdir(parents=True, exist_ok=True)
        
        for item in src.iterdir():
            if any(item.match(pattern) for pattern in exclude_patterns):
                continue
                
            if item.is_file():
                shutil.copy2(item, dest / item.name)
                files_count += 1
            elif item.is_dir():
                files_count += self._copy_directory(item, dest / item.name, exclude_patterns)
        
        return files_count
    
    def _backup_database(self, backup_dir: Path):
        """Create database backup"""
        db_path = self.project_root / "data" / "trades.db"
        if db_path.exists():
            dest_path = backup_dir / "trades.db"
            shutil.copy2(db_path, dest_path)
    
    def _export_database_to_sql(self, db_path: Path, output_path: Path):
        """Export database to SQL file"""
        try:
            with sqlite3.connect(db_path) as conn:
                with open(output_path, 'w') as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
        except Exception as e:
            self.logger.error(f"Error exporting database: {e}")
    
    def _create_compressed_archive(self, backup_dir: Path) -> Path:
        """Create compressed tar.gz archive"""
        archive_path = backup_dir.with_suffix('.tar.gz')
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(backup_dir, arcname=backup_dir.name)
        
        # Remove uncompressed directory
        shutil.rmtree(backup_dir)
        
        return archive_path
    
    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        
        if path.is_file():
            return path.stat().st_size
        
        for item in path.rglob('*'):
            if item.is_file():
                total_size += item.stat().st_size
        
        return total_size
    
    def _calculate_directory_checksum(self, path: Path) -> str:
        """Calculate MD5 checksum of directory contents"""
        hasher = hashlib.md5()
        
        if path.is_file():
            with open(path, 'rb') as f:
                hasher.update(f.read())
        else:
            for item in sorted(path.rglob('*')):
                if item.is_file():
                    with open(item, 'rb') as f:
                        hasher.update(f.read())
        
        return hasher.hexdigest()
    
    def _verify_backup(self, backup_dir: Path, metadata: Dict) -> bool:
        """Verify backup integrity"""
        try:
            # Verify file count
            actual_files = len([f for f in backup_dir.rglob('*') if f.is_file()])
            expected_files = metadata['files_count']
            
            if actual_files != expected_files:
                self.logger.warning(f"File count mismatch: {actual_files} vs {expected_files}")
                return False
            
            # Verify checksum
            actual_checksum = self._calculate_directory_checksum(backup_dir)
            expected_checksum = metadata['checksum']
            
            if actual_checksum != expected_checksum:
                self.logger.warning(f"Checksum mismatch: {actual_checksum} vs {expected_checksum}")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Backup verification failed: {e}")
            return False
    
    def _cleanup_old_backups(self, backup_type: str):
        """Remove old backups based on retention policy"""
        retention = self.config['retention']
        
        # Get all backups of this type
        backups = self.list_backups(backup_type=backup_type)
        
        # Determine retention limit
        if backup_type in retention:
            limit = retention[backup_type]
        else:
            limit = retention.get('daily', 30)  # Default to daily retention
        
        # Remove excess backups
        if len(backups) > limit:
            backups_to_remove = backups[limit:]  # Keep newest, remove oldest
            
            for backup in backups_to_remove:
                try:
                    backup_path = self.backup_root / backup['name']
                    if backup_path.exists():
                        if backup_path.is_dir():
                            shutil.rmtree(backup_path)
                        else:
                            backup_path.unlink()
                        
                        self.logger.info(f"Removed old backup: {backup['name']}")
                except Exception as e:
                    self.logger.error(f"Error removing backup {backup['name']}: {e}")
    
    def list_backups(self, backup_type: str = None) -> List[Dict]:
        """List all available backups"""
        backups = []
        
        for backup_path in self.backup_root.iterdir():
            if backup_path.name.startswith('jj-bot-'):
                # Try to load metadata
                metadata_file = backup_path / 'backup_metadata.json'
                if backup_path.is_dir() and metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            
                        if backup_type is None or metadata.get('type') == backup_type:
                            backups.append(metadata)
                    except Exception as e:
                        self.logger.error(f"Error reading backup metadata for {backup_path.name}: {e}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return backups
    
    def get_backup_info(self, backup_id: str) -> Optional[Dict]:
        """Get detailed information about a specific backup"""
        backups = self.list_backups()
        
        for backup in backups:
            if backup['id'] == backup_id:
                return backup
        
        return None
    
    def _get_last_backup(self, backup_type: str) -> Optional[Dict]:
        """Get the most recent backup of specified type"""
        backups = self.list_backups(backup_type=backup_type)
        return backups[0] if backups else None
    
    def get_system_version(self) -> str:
        """Get current system version"""
        try:
            version_file = self.project_root / "VERSION"
            if version_file.exists():
                return version_file.read_text().strip()
            else:
                return datetime.now().strftime("%Y.%m.%d")
        except:
            return "unknown"
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    def get_backup_statistics(self) -> Dict:
        """Get comprehensive backup statistics"""
        backups = self.list_backups()
        
        total_size = sum(backup.get('size_bytes', 0) for backup in backups)
        backup_types = {}
        
        for backup in backups:
            backup_type = backup.get('type', 'unknown')
            if backup_type not in backup_types:
                backup_types[backup_type] = {'count': 0, 'size': 0}
            
            backup_types[backup_type]['count'] += 1
            backup_types[backup_type]['size'] += backup.get('size_bytes', 0)
        
        return {
            'total_backups': len(backups),
            'total_size_bytes': total_size,
            'total_size_human': self._format_bytes(total_size),
            'backup_types': backup_types,
            'oldest_backup': backups[-1]['timestamp'] if backups else None,
            'newest_backup': backups[0]['timestamp'] if backups else None,
            'storage_location': str(self.backup_root)
        }

# Global backup manager instance
backup_manager = EnterpriseBackupManager()
