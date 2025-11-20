"""
Error Recovery and Graceful Degradation Module

Provides error handling, logging, and state recovery mechanisms
"""

import os
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Callable, Optional
from functools import wraps

# Error log directory
PROJECT_ROOT = Path(__file__).parent.parent
ERROR_LOG_DIR = PROJECT_ROOT / "logs"
ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)

ERROR_LOG_FILE = ERROR_LOG_DIR / "errors.log"
STATE_FILE = PROJECT_ROOT / "data" / "service_state.json"


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """
    Log an error to file with full context

    Args:
        error: Exception that occurred
        context: Additional context information
    """
    timestamp = datetime.now().isoformat()

    error_entry = {
        "timestamp": timestamp,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
        "context": context or {}
    }

    # Write to log file
    with open(ERROR_LOG_FILE, "a") as f:
        f.write(json.dumps(error_entry) + "\n")

    # Also print to console
    print(f"❌ ERROR [{timestamp}]: {type(error).__name__}: {error}")
    if context:
        print(f"   Context: {context}")


def with_error_recovery(fallback_value: Any = None, log_context: Optional[Dict] = None):
    """
    Decorator for error recovery with graceful degradation

    Args:
        fallback_value: Value to return if function fails
        log_context: Additional context to log with errors

    Example:
        @with_error_recovery(fallback_value=[], log_context={"function": "get_data"})
        def get_data():
            # ... may fail
            return data
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                context = {
                    "function": func.__name__,
                    "args": str(args)[:100],  # Limit length
                    "kwargs": str(kwargs)[:100]
                }
                if log_context:
                    context.update(log_context)

                log_error(e, context)

                # Return fallback value for graceful degradation
                return fallback_value

        return wrapper
    return decorator


def save_service_state(service_name: str, state: Dict[str, Any]):
    """
    Save service state for recovery after crash

    Args:
        service_name: Name of the service
        state: State dictionary to save
    """
    try:
        # Load existing states
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                all_states = json.load(f)
        else:
            all_states = {}

        # Update state for this service
        all_states[service_name] = {
            "timestamp": datetime.now().isoformat(),
            "state": state
        }

        # Save back to file
        with open(STATE_FILE, 'w') as f:
            json.dump(all_states, f, indent=2)

    except Exception as e:
        print(f"⚠️ Failed to save service state: {e}")


def load_service_state(service_name: str) -> Optional[Dict[str, Any]]:
    """
    Load saved service state for recovery

    Args:
        service_name: Name of the service

    Returns:
        Saved state dictionary or None if not found
    """
    try:
        if not STATE_FILE.exists():
            return None

        with open(STATE_FILE, 'r') as f:
            all_states = json.load(f)

        service_data = all_states.get(service_name)
        if service_data:
            return service_data.get("state")

    except Exception as e:
        print(f"⚠️ Failed to load service state: {e}")

    return None


def clear_service_state(service_name: str):
    """
    Clear saved state for a service

    Args:
        service_name: Name of the service
    """
    try:
        if not STATE_FILE.exists():
            return

        with open(STATE_FILE, 'r') as f:
            all_states = json.load(f)

        if service_name in all_states:
            del all_states[service_name]

            with open(STATE_FILE, 'w') as f:
                json.dump(all_states, f, indent=2)

    except Exception as e:
        print(f"⚠️ Failed to clear service state: {e}")


def get_recent_errors(limit: int = 50) -> list:
    """
    Get recent errors from log file

    Args:
        limit: Maximum number of errors to return

    Returns:
        List of error dictionaries
    """
    try:
        if not ERROR_LOG_FILE.exists():
            return []

        errors = []
        with open(ERROR_LOG_FILE, 'r') as f:
            for line in f:
                try:
                    error = json.loads(line.strip())
                    errors.append(error)
                except json.JSONDecodeError:
                    continue

        # Return most recent errors
        return errors[-limit:]

    except Exception as e:
        print(f"⚠️ Failed to load errors: {e}")
        return []


class CircuitBreaker:
    """
    Circuit breaker pattern for external service calls

    Prevents cascading failures by stopping requests to failing services
    """

    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        """
        Initialize circuit breaker

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout_seconds: Seconds to wait before trying again
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Call function through circuit breaker

        Args:
            func: Function to call
            *args, **kwargs: Function arguments

        Returns:
            Function result or raises CircuitBreakerError if open

        Raises:
            CircuitBreakerError: If circuit is open
        """
        # Check if circuit is open
        if self.state == "open":
            time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()

            if time_since_failure < self.timeout_seconds:
                raise CircuitBreakerError(f"Circuit breaker open (wait {self.timeout_seconds - time_since_failure:.0f}s)")

            # Try half-open state
            self.state = "half-open"

        try:
            result = func(*args, **kwargs)

            # Success - reset circuit
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0

            return result

        except Exception as e:
            # Failure - increment count
            self.failure_count += 1
            self.last_failure_time = datetime.now()

            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                print(f"⚠️ Circuit breaker opened after {self.failure_count} failures")

            raise e


class CircuitBreakerError(Exception):
    """Circuit breaker is open"""
    pass
