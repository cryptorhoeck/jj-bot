"""
SSL/TLS Configuration for JJ-Bot
Provides HTTPS support with self-signed or custom certificates
"""

import os
import ssl
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SSL_DIR = PROJECT_ROOT / "config" / "ssl"
CERT_FILE = SSL_DIR / "server.crt"
KEY_FILE = SSL_DIR / "server.key"


def ensure_ssl_directory():
    """Create SSL directory if it doesn't exist"""
    SSL_DIR.mkdir(parents=True, exist_ok=True)


def generate_self_signed_cert(
    common_name: str = "localhost",
    days_valid: int = 365,
    key_size: int = 2048
) -> Tuple[Path, Path]:
    """
    Generate a self-signed SSL certificate using OpenSSL

    Args:
        common_name: Domain name for the certificate (default: localhost)
        days_valid: Number of days the certificate is valid
        key_size: RSA key size in bits

    Returns:
        Tuple of (cert_path, key_path)
    """
    ensure_ssl_directory()

    # Check if OpenSSL is available
    try:
        subprocess.run(["openssl", "version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("OpenSSL not found. Please install OpenSSL to generate certificates.")
        raise RuntimeError("OpenSSL not available")

    # Generate private key
    key_cmd = [
        "openssl", "genrsa",
        "-out", str(KEY_FILE),
        str(key_size)
    ]

    # Generate self-signed certificate
    cert_cmd = [
        "openssl", "req", "-new", "-x509",
        "-key", str(KEY_FILE),
        "-out", str(CERT_FILE),
        "-days", str(days_valid),
        "-subj", f"/CN={common_name}/O=JJ-Bot/C=US",
        "-addext", f"subjectAltName=DNS:{common_name},DNS:127.0.0.1,IP:127.0.0.1"
    ]

    try:
        logger.info("Generating RSA private key...")
        subprocess.run(key_cmd, check=True, capture_output=True)

        logger.info("Generating self-signed certificate...")
        subprocess.run(cert_cmd, check=True, capture_output=True)

        # Set proper permissions on key file
        os.chmod(KEY_FILE, 0o600)

        logger.info(f"SSL certificate generated successfully:")
        logger.info(f"  Certificate: {CERT_FILE}")
        logger.info(f"  Private Key: {KEY_FILE}")
        logger.info(f"  Valid for: {days_valid} days")

        return CERT_FILE, KEY_FILE

    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to generate certificate: {e.stderr.decode() if e.stderr else str(e)}")
        raise


def certificates_exist() -> bool:
    """Check if SSL certificates exist"""
    return CERT_FILE.exists() and KEY_FILE.exists()


def get_certificate_info() -> Optional[dict]:
    """Get information about the current SSL certificate"""
    if not certificates_exist():
        return None

    try:
        cmd = [
            "openssl", "x509",
            "-in", str(CERT_FILE),
            "-noout",
            "-subject", "-issuer", "-dates", "-serial"
        ]
        result = subprocess.run(cmd, capture_output=True, check=True)
        output = result.stdout.decode()

        info = {}
        for line in output.strip().split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                info[key.strip()] = value.strip()

        return {
            "certificate_path": str(CERT_FILE),
            "key_path": str(KEY_FILE),
            "details": info,
            "exists": True
        }
    except Exception as e:
        logger.warning(f"Could not read certificate info: {e}")
        return {"exists": True, "error": str(e)}


def create_ssl_context() -> Optional[ssl.SSLContext]:
    """
    Create SSL context for HTTPS server

    Returns:
        SSLContext configured for server use, or None if certs don't exist
    """
    if not certificates_exist():
        logger.warning("SSL certificates not found. Run generate_self_signed_cert() first.")
        return None

    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(str(CERT_FILE), str(KEY_FILE))

        # Security settings
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:DHE+AESGCM:ECDHE+CHACHA20:DHE+CHACHA20')

        return context
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        return None


class SSLConfig:
    """SSL Configuration manager"""

    def __init__(self):
        self.enabled = False
        self.cert_file = CERT_FILE
        self.key_file = KEY_FILE
        self.auto_generate = True

    def setup(self, auto_generate: bool = True) -> bool:
        """
        Setup SSL certificates

        Args:
            auto_generate: Generate self-signed cert if none exists

        Returns:
            True if SSL is ready to use
        """
        if certificates_exist():
            self.enabled = True
            logger.info("SSL certificates found and ready")
            return True

        if auto_generate:
            try:
                generate_self_signed_cert()
                self.enabled = True
                return True
            except Exception as e:
                logger.error(f"Failed to setup SSL: {e}")
                return False

        logger.warning("SSL certificates not found and auto-generate is disabled")
        return False

    def get_uvicorn_ssl_kwargs(self) -> dict:
        """Get SSL arguments for uvicorn"""
        if not self.enabled or not certificates_exist():
            return {}

        return {
            "ssl_keyfile": str(KEY_FILE),
            "ssl_certfile": str(CERT_FILE)
        }

    def get_status(self) -> dict:
        """Get SSL status"""
        cert_info = get_certificate_info()
        return {
            "enabled": self.enabled,
            "certificates_exist": certificates_exist(),
            "cert_file": str(CERT_FILE),
            "key_file": str(KEY_FILE),
            "certificate_info": cert_info
        }


# Global SSL config instance
ssl_config = SSLConfig()


# CLI commands for certificate management
def main():
    """CLI for SSL certificate management"""
    import argparse

    parser = argparse.ArgumentParser(description="JJ-Bot SSL Certificate Manager")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate self-signed certificate")
    gen_parser.add_argument("--cn", default="localhost", help="Common Name (domain)")
    gen_parser.add_argument("--days", type=int, default=365, help="Validity in days")
    gen_parser.add_argument("--key-size", type=int, default=2048, help="RSA key size")

    # Info command
    subparsers.add_parser("info", help="Show certificate information")

    # Status command
    subparsers.add_parser("status", help="Check SSL status")

    args = parser.parse_args()

    if args.command == "generate":
        print(f"Generating self-signed certificate for '{args.cn}'...")
        try:
            cert, key = generate_self_signed_cert(args.cn, args.days, args.key_size)
            print(f"Certificate: {cert}")
            print(f"Private Key: {key}")
            print(f"Valid for {args.days} days")
            print("\nWARNING: Self-signed certificates will show browser warnings.")
            print("For production, use certificates from a trusted CA (e.g., Let's Encrypt).")
        except Exception as e:
            print(f"Error: {e}")
            return 1

    elif args.command == "info":
        info = get_certificate_info()
        if info:
            print("Certificate Information:")
            for key, value in info.items():
                print(f"  {key}: {value}")
        else:
            print("No certificate found. Run 'generate' first.")

    elif args.command == "status":
        status = ssl_config.get_status()
        print("SSL Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    exit(main())
