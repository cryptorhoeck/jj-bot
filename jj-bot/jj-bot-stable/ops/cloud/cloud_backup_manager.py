import boto3
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging

class CloudBackupManager:
    """Enterprise cloud backup to AWS S3"""
    
    def __init__(self):
        self.logger = self.setup_logging()
        self.config = self.load_cloud_config()
        self.s3_client = None
        
    def setup_logging(self):
        """Setup cloud backup logging"""
        log_dir = Path.home() / "jj-bot" / "ops" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "cloud_backup.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    def load_cloud_config(self) -> Dict:
        """Load cloud backup configuration"""
        config_file = Path.home() / "jj-bot" / "ops" / "cloud_config.json"
        
        default_config = {
            "enabled": False,
            "provider": "aws_s3",
            "aws": {
                "region": "us-east-1",
                "bucket_name": "",
                "access_key_id": "",
                "secret_access_key": "",
                "encryption": True
            },
            "backup_schedule": {
                "daily_full": True,
                "weekly_archive": True,
                "retention_days": 90
            },
            "compression": True,
            "notifications": True
        }
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    return {**default_config, **config}
            except Exception as e:
                self.logger.error(f"Error loading cloud config: {e}")
                return default_config
        else:
            self.save_cloud_config(default_config)
            return default_config
    
    def save_cloud_config(self, config: Dict = None):
        """Save cloud configuration"""
        if config:
            self.config = config
            
        config_file = Path.home() / "jj-bot" / "ops" / "cloud_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def initialize_s3_client(self) -> bool:
        """Initialize AWS S3 client"""
        try:
            if not self.config["enabled"]:
                return False
                
            aws_config = self.config["aws"]
            
            self.s3_client = boto3.client(
                's3',
                region_name=aws_config["region"],
                aws_access_key_id=aws_config["access_key_id"],
                aws_secret_access_key=aws_config["secret_access_key"]
            )
            
            # Test connection
            self.s3_client.head_bucket(Bucket=aws_config["bucket_name"])
            self.logger.info(f"S3 client initialized successfully for bucket: {aws_config['bucket_name']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize S3 client: {e}")
            return False
    
    def upload_backup_to_cloud(self, backup_path: Path, backup_metadata: Dict) -> Dict:
        """Upload backup to cloud storage"""
        try:
            if not self.initialize_s3_client():
                return {"success": False, "error": "S3 client initialization failed"}
            
            bucket_name = self.config["aws"]["bucket_name"]
            
            # Create cloud key
            timestamp = datetime.now().strftime("%Y/%m/%d")
            cloud_key = f"jj-bot-backups/{timestamp}/{backup_path.name}"
            
            # Upload file
            self.logger.info(f"Uploading {backup_path.name} to S3...")
            
            extra_args = {}
            if self.config["aws"]["encryption"]:
                extra_args["ServerSideEncryption"] = "AES256"
            
            self.s3_client.upload_file(
                str(backup_path),
                bucket_name,
                cloud_key,
                ExtraArgs=extra_args
            )
            
            # Upload metadata
            metadata_key = f"{cloud_key}.metadata.json"
            metadata_content = json.dumps(backup_metadata, indent=2)
            
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=metadata_key,
                Body=metadata_content,
                ContentType="application/json",
                **extra_args
            )
            
            # Get object info
            response = self.s3_client.head_object(Bucket=bucket_name, Key=cloud_key)
            
            result = {
                "success": True,
                "cloud_key": cloud_key,
                "bucket": bucket_name,
                "size": response["ContentLength"],
                "etag": response["ETag"],
                "last_modified": response["LastModified"].isoformat(),
                "encrypted": self.config["aws"]["encryption"]
            }
            
            self.logger.info(f"Backup uploaded successfully: {cloud_key}")
            return result
            
        except Exception as e:
            self.logger.error(f"Cloud upload failed: {e}")
            return {"success": False, "error": str(e)}
    
    def list_cloud_backups(self) -> List[Dict]:
        """List all cloud backups"""
        try:
            if not self.initialize_s3_client():
                return []
            
            bucket_name = self.config["aws"]["bucket_name"]
            backups = []
            
            # List objects in backup prefix
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="jj-bot-backups/"
            )
            
            for obj in response.get("Contents", []):
                if not obj["Key"].endswith(".metadata.json"):
                    backups.append({
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "size_human": self._format_bytes(obj["Size"]),
                        "last_modified": obj["LastModified"].isoformat(),
                        "etag": obj["ETag"]
                    })
            
            # Sort by last modified (newest first)
            backups.sort(key=lambda x: x["last_modified"], reverse=True)
            return backups
            
        except Exception as e:
            self.logger.error(f"Error listing cloud backups: {e}")
            return []
    
    def download_backup_from_cloud(self, cloud_key: str, local_path: Path) -> bool:
        """Download backup from cloud storage"""
        try:
            if not self.initialize_s3_client():
                return False
            
            bucket_name = self.config["aws"]["bucket_name"]
            
            self.logger.info(f"Downloading {cloud_key} from S3...")
            
            self.s3_client.download_file(
                bucket_name,
                cloud_key,
                str(local_path)
            )
            
            self.logger.info(f"Backup downloaded successfully: {local_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Cloud download failed: {e}")
            return False
    
    def cleanup_old_cloud_backups(self, retention_days: int = None) -> Dict:
        """Clean up old cloud backups"""
        try:
            if not self.initialize_s3_client():
                return {"success": False, "error": "S3 client initialization failed"}
            
            if retention_days is None:
                retention_days = self.config["backup_schedule"]["retention_days"]
            
            bucket_name = self.config["aws"]["bucket_name"]
            cutoff_date = datetime.now().timestamp() - (retention_days * 24 * 3600)
            
            # List all backups
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix="jj-bot-backups/"
            )
            
            deleted_count = 0
            for obj in response.get("Contents", []):
                if obj["LastModified"].timestamp() < cutoff_date:
                    # Delete object
                    self.s3_client.delete_object(
                        Bucket=bucket_name,
                        Key=obj["Key"]
                    )
                    deleted_count += 1
                    self.logger.info(f"Deleted old cloud backup: {obj['Key']}")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "retention_days": retention_days
            }
            
        except Exception as e:
            self.logger.error(f"Cloud cleanup failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_bytes(self, bytes_size: int) -> str:
        """Format bytes to human readable string"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} TB"
    
    def get_cloud_stats(self) -> Dict:
        """Get cloud backup statistics"""
        try:
            if not self.config["enabled"]:
                return {"enabled": False}
            
            backups = self.list_cloud_backups()
            total_size = sum(backup["size"] for backup in backups)
            
            return {
                "enabled": True,
                "provider": self.config["provider"],
                "bucket": self.config["aws"]["bucket_name"],
                "total_backups": len(backups),
                "total_size_bytes": total_size,
                "total_size_human": self._format_bytes(total_size),
                "retention_days": self.config["backup_schedule"]["retention_days"],
                "encryption_enabled": self.config["aws"]["encryption"]
            }
            
        except Exception as e:
            return {"enabled": False, "error": str(e)}

# Global cloud backup manager
cloud_backup_manager = CloudBackupManager()
