"""
Health Check HTTP Server
Provides health/status endpoint for monitoring
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from aiohttp import web

logger = logging.getLogger(__name__)


class HealthCheckServer:
    """
    Simple HTTP server for health checks and monitoring

    Endpoints:
        GET /health - Returns 200 if bot is healthy
        GET /status - Returns detailed bot status JSON
        GET /metrics - Returns Prometheus-style metrics

    Dead Man's Switch:
        If enabled, monitors heartbeat and triggers callback if bot becomes unresponsive.
        This can be used to close positions or send alerts when the bot stops responding.
    """

    def __init__(
        self,
        port: int = 8080,
        host: str = "0.0.0.0",
        status_callback: Optional[Callable[[], Dict[str, Any]]] = None,
        dead_mans_switch_timeout: float = 300.0,  # 5 minutes default
        dead_mans_switch_callback: Optional[Callable[[], Any]] = None,
        dead_mans_switch_enabled: bool = False
    ):
        self.port = port
        self.host = host
        self._status_callback = status_callback
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._start_time = datetime.now()
        self._last_heartbeat = datetime.now()
        self._healthy = True
        self._health_reason = "OK"

        # Dead man's switch
        self._dms_timeout = dead_mans_switch_timeout
        self._dms_callback = dead_mans_switch_callback
        self._dms_enabled = dead_mans_switch_enabled
        self._dms_triggered = False
        self._dms_task: Optional[asyncio.Task] = None

    def set_status_callback(self, callback: Callable[[], Dict[str, Any]]):
        """Set callback to get bot status"""
        self._status_callback = callback

    def set_dead_mans_switch(
        self,
        callback: Callable[[], Any],
        timeout_seconds: float = 300.0,
        enabled: bool = True
    ):
        """Configure the dead man's switch"""
        self._dms_callback = callback
        self._dms_timeout = timeout_seconds
        self._dms_enabled = enabled
        logger.info(f"Dead man's switch configured: timeout={timeout_seconds}s, enabled={enabled}")

    def update_heartbeat(self):
        """Update the heartbeat timestamp"""
        self._last_heartbeat = datetime.now()
        # Reset triggered flag on heartbeat (bot is alive again)
        if self._dms_triggered:
            self._dms_triggered = False
            logger.info("Dead man's switch reset - bot heartbeat restored")

    def set_health(self, healthy: bool, reason: str = ""):
        """Set health status"""
        self._healthy = healthy
        self._health_reason = reason if reason else ("OK" if healthy else "Unhealthy")

    async def _health_handler(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        heartbeat_age = (datetime.now() - self._last_heartbeat).total_seconds()

        # Consider unhealthy if no heartbeat for 5 minutes
        if heartbeat_age > 300:
            self._healthy = False
            self._health_reason = f"No heartbeat for {heartbeat_age:.0f}s"

        if self._healthy:
            return web.json_response({
                "status": "healthy",
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
                "last_heartbeat_seconds_ago": heartbeat_age
            })
        else:
            return web.json_response({
                "status": "unhealthy",
                "reason": self._health_reason,
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
                "last_heartbeat_seconds_ago": heartbeat_age
            }, status=503)

    async def _status_handler(self, request: web.Request) -> web.Response:
        """Detailed status endpoint"""
        status = {
            "healthy": self._healthy,
            "health_reason": self._health_reason,
            "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
            "last_heartbeat": self._last_heartbeat.isoformat(),
            "start_time": self._start_time.isoformat(),
        }

        # Add bot status if callback available
        if self._status_callback:
            try:
                bot_status = self._status_callback()
                status["bot"] = bot_status
            except Exception as e:
                status["bot_error"] = str(e)

        return web.json_response(status)

    async def _metrics_handler(self, request: web.Request) -> web.Response:
        """Prometheus-style metrics endpoint"""
        uptime = (datetime.now() - self._start_time).total_seconds()
        heartbeat_age = (datetime.now() - self._last_heartbeat).total_seconds()

        metrics = [
            f"# HELP jjbot_up Bot health status (1=healthy, 0=unhealthy)",
            f"# TYPE jjbot_up gauge",
            f"jjbot_up {1 if self._healthy else 0}",
            f"# HELP jjbot_uptime_seconds Bot uptime in seconds",
            f"# TYPE jjbot_uptime_seconds counter",
            f"jjbot_uptime_seconds {uptime:.2f}",
            f"# HELP jjbot_heartbeat_age_seconds Seconds since last heartbeat",
            f"# TYPE jjbot_heartbeat_age_seconds gauge",
            f"jjbot_heartbeat_age_seconds {heartbeat_age:.2f}",
        ]

        # Add bot-specific metrics if callback available
        if self._status_callback:
            try:
                bot_status = self._status_callback()
                if "equity" in bot_status:
                    metrics.extend([
                        f"# HELP jjbot_equity Current equity in USD",
                        f"# TYPE jjbot_equity gauge",
                        f"jjbot_equity {bot_status['equity']:.2f}",
                    ])
                if "total_pnl" in bot_status:
                    metrics.extend([
                        f"# HELP jjbot_total_pnl Total P&L in USD",
                        f"# TYPE jjbot_total_pnl gauge",
                        f"jjbot_total_pnl {bot_status['total_pnl']:.2f}",
                    ])
                if "total_trades" in bot_status:
                    metrics.extend([
                        f"# HELP jjbot_total_trades Total number of trades",
                        f"# TYPE jjbot_total_trades counter",
                        f"jjbot_total_trades {bot_status['total_trades']}",
                    ])
                if "open_positions" in bot_status:
                    metrics.extend([
                        f"# HELP jjbot_open_positions Number of open positions",
                        f"# TYPE jjbot_open_positions gauge",
                        f"jjbot_open_positions {bot_status['open_positions']}",
                    ])
                if "daily_pnl" in bot_status:
                    metrics.extend([
                        f"# HELP jjbot_daily_pnl Daily P&L in USD",
                        f"# TYPE jjbot_daily_pnl gauge",
                        f"jjbot_daily_pnl {bot_status['daily_pnl']:.2f}",
                    ])
            except Exception:
                pass

        return web.Response(
            text="\n".join(metrics),
            content_type="text/plain"
        )

    async def _dead_mans_switch_monitor(self):
        """Background task to monitor heartbeat and trigger dead man's switch if needed"""
        while True:
            try:
                await asyncio.sleep(10)  # Check every 10 seconds

                if not self._dms_enabled or self._dms_triggered:
                    continue

                heartbeat_age = (datetime.now() - self._last_heartbeat).total_seconds()

                if heartbeat_age > self._dms_timeout:
                    logger.warning("=" * 60)
                    logger.warning("[DEAD MAN'S SWITCH] Bot unresponsive!")
                    logger.warning(f"[DEAD MAN'S SWITCH] No heartbeat for {heartbeat_age:.0f} seconds")
                    logger.warning("=" * 60)

                    self._dms_triggered = True
                    self._healthy = False
                    self._health_reason = f"Dead man's switch triggered - no heartbeat for {heartbeat_age:.0f}s"

                    # Call the callback if set
                    if self._dms_callback:
                        try:
                            result = self._dms_callback()
                            # Handle async callbacks
                            if asyncio.iscoroutine(result):
                                await result
                            logger.info("[DEAD MAN'S SWITCH] Callback executed")
                        except Exception as e:
                            logger.error(f"[DEAD MAN'S SWITCH] Callback failed: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Dead man's switch monitor error: {e}")
                await asyncio.sleep(30)

    async def start(self) -> bool:
        """Start the health check server"""
        try:
            self._app = web.Application()
            self._app.router.add_get("/health", self._health_handler)
            self._app.router.add_get("/status", self._status_handler)
            self._app.router.add_get("/metrics", self._metrics_handler)
            self._app.router.add_get("/", self._health_handler)  # Root = health

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(self._runner, self.host, self.port)
            await self._site.start()

            # Start dead man's switch monitor if enabled
            if self._dms_enabled:
                self._dms_task = asyncio.create_task(self._dead_mans_switch_monitor())
                logger.info(f"Dead man's switch enabled with {self._dms_timeout}s timeout")

            logger.info(f"Health check server started on http://{'localhost' if self.host == '0.0.0.0' else self.host}:{self.port}")
            return True

        except OSError as e:
            if "Address already in use" in str(e):
                logger.warning(f"Health check port {self.port} already in use, skipping")
            else:
                logger.error(f"Failed to start health check server: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            return False

    async def stop(self):
        """Stop the health check server"""
        # Stop dead man's switch monitor
        if self._dms_task:
            self._dms_task.cancel()
            try:
                await self._dms_task
            except asyncio.CancelledError:
                pass

        if self._runner:
            await self._runner.cleanup()
            logger.info("Health check server stopped")


async def create_health_server(
    port: int = 8080,
    status_callback: Optional[Callable[[], Dict[str, Any]]] = None
) -> HealthCheckServer:
    """Factory function to create and start health check server"""
    server = HealthCheckServer(port=port, status_callback=status_callback)
    await server.start()
    return server
