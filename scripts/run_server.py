#!/usr/bin/env python3
"""
JJ-Bot Server Launcher
Supports HTTP and HTTPS modes with automatic certificate generation
"""

import os
import sys
import argparse
import logging

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="JJ-Bot API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--https", action="store_true", help="Enable HTTPS with SSL/TLS")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate file")
    parser.add_argument("--ssl-key", help="Path to SSL private key file")
    parser.add_argument("--generate-cert", action="store_true", help="Generate self-signed certificate")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    parser.add_argument("--workers", type=int, default=1, help="Number of worker processes")
    parser.add_argument("--log-level", default="info", choices=["debug", "info", "warning", "error"])

    args = parser.parse_args()

    # Import after path setup
    import uvicorn
    from config.ssl_config import ssl_config, generate_self_signed_cert, certificates_exist

    print("=" * 60)
    print("  JJ-Bot Professional Trading Platform")
    print("=" * 60)

    # SSL/HTTPS configuration
    ssl_kwargs = {}

    if args.https:
        if args.ssl_cert and args.ssl_key:
            # Use provided certificates
            ssl_kwargs = {
                "ssl_certfile": args.ssl_cert,
                "ssl_keyfile": args.ssl_key
            }
            print(f"[HTTPS] Using provided certificates")
        elif args.generate_cert or not certificates_exist():
            # Generate self-signed certificate
            print("[HTTPS] Generating self-signed certificate...")
            try:
                generate_self_signed_cert(common_name=args.host)
                ssl_kwargs = ssl_config.get_uvicorn_ssl_kwargs()
                print("[HTTPS] Self-signed certificate generated")
                print("        WARNING: Browser will show security warnings")
            except Exception as e:
                print(f"[ERROR] Failed to generate certificate: {e}")
                print("        Falling back to HTTP mode")
                args.https = False
        else:
            ssl_kwargs = ssl_config.get_uvicorn_ssl_kwargs()
            print("[HTTPS] Using existing certificates")

    # Server configuration
    protocol = "https" if args.https else "http"
    print(f"\n[SERVER] Starting on {protocol}://{args.host}:{args.port}")
    print(f"[DOCS]   Swagger UI: {protocol}://{args.host}:{args.port}/docs")
    print(f"[DASH]   Dashboard: http://localhost:5173")
    print("")

    if args.https:
        print("[SECURITY] HTTPS enabled - Communications encrypted")
    else:
        print("[WARNING] Running in HTTP mode - Not secure for production!")
        print("          Use --https flag for encrypted connections")

    print("=" * 60)
    print("")

    # Run server
    uvicorn.run(
        "glue.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
        access_log=args.log_level == "debug",
        **ssl_kwargs
    )


if __name__ == "__main__":
    main()
