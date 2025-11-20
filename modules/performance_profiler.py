"""
Performance Profiling Module

Provides timing decorators, query profiling, and performance metrics
"""

import time
import functools
from typing import Dict, Callable, Any
from collections import defaultdict
from datetime import datetime


class PerformanceProfiler:
    """
    Global performance profiler for tracking function execution times
    """

    def __init__(self):
        self.timings = defaultdict(list)
        self.call_counts = defaultdict(int)
        self.enabled = True

    def profile(self, func: Callable) -> Callable:
        """
        Decorator to profile function execution time

        Usage:
            @profiler.profile
            def my_function():
                # ... code ...
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.enabled:
                return func(*args, **kwargs)

            func_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = (time.time() - start_time) * 1000  # Convert to ms
                self.timings[func_name].append(elapsed)
                self.call_counts[func_name] += 1

                # Log slow functions (>100ms)
                if elapsed > 100:
                    print(f"⏱️ SLOW: {func_name} took {elapsed:.2f}ms")

        return wrapper

    def get_stats(self, limit: int = 20) -> Dict[str, Any]:
        """
        Get performance statistics

        Args:
            limit: Number of top functions to return

        Returns:
            Dictionary of performance metrics
        """
        stats = []

        for func_name, times in self.timings.items():
            if not times:
                continue

            stats.append({
                "function": func_name,
                "call_count": self.call_counts[func_name],
                "total_time_ms": sum(times),
                "avg_time_ms": sum(times) / len(times),
                "min_time_ms": min(times),
                "max_time_ms": max(times),
                "last_time_ms": times[-1] if times else 0
            })

        # Sort by total time descending
        stats.sort(key=lambda x: x["total_time_ms"], reverse=True)

        return {
            "stats": stats[:limit],
            "total_functions_profiled": len(stats),
            "timestamp": datetime.now().isoformat()
        }

    def reset(self):
        """Reset all profiling data"""
        self.timings.clear()
        self.call_counts.clear()

    def enable(self):
        """Enable profiling"""
        self.enabled = True

    def disable(self):
        """Disable profiling"""
        self.enabled = False


# Global profiler instance
profiler = PerformanceProfiler()


def time_query(query_name: str):
    """
    Decorator to time database queries

    Args:
        query_name: Name/description of the query

    Usage:
        @time_query("get_all_trades")
        def get_trades():
            # ... database query ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000

                # Log slow queries (>50ms)
                if elapsed_ms > 50:
                    print(f"🐌 SLOW QUERY: {query_name} took {elapsed_ms:.2f}ms")

                # Record to profiler
                profiler.timings[f"query.{query_name}"].append(elapsed_ms)
                profiler.call_counts[f"query.{query_name}"] += 1

        return wrapper
    return decorator


class QueryProfiler:
    """
    Database query profiler with optimization suggestions
    """

    def __init__(self):
        self.slow_queries = []
        self.query_counts = defaultdict(int)
        self.slow_threshold_ms = 50

    def log_query(self, query: str, elapsed_ms: float, result_count: int = 0):
        """
        Log a database query

        Args:
            query: SQL query string
            elapsed_ms: Execution time in milliseconds
            result_count: Number of rows returned
        """
        self.query_counts[query] += 1

        if elapsed_ms > self.slow_threshold_ms:
            self.slow_queries.append({
                "query": query[:200],  # Truncate long queries
                "elapsed_ms": elapsed_ms,
                "result_count": result_count,
                "timestamp": datetime.now().isoformat()
            })

            # Keep only last 100 slow queries
            if len(self.slow_queries) > 100:
                self.slow_queries = self.slow_queries[-100:]

    def get_slow_queries(self, limit: int = 10) -> list:
        """
        Get recent slow queries

        Args:
            limit: Number of queries to return

        Returns:
            List of slow query dictionaries
        """
        # Sort by elapsed time descending
        sorted_queries = sorted(
            self.slow_queries,
            key=lambda x: x["elapsed_ms"],
            reverse=True
        )
        return sorted_queries[:limit]

    def suggest_optimizations(self) -> list:
        """
        Analyze queries and suggest optimizations

        Returns:
            List of optimization suggestions
        """
        suggestions = []

        # Check for queries without WHERE clause
        for query_entry in self.slow_queries:
            query = query_entry["query"].upper()

            if "SELECT" in query and "WHERE" not in query and query_entry["result_count"] > 100:
                suggestions.append({
                    "query": query_entry["query"][:100],
                    "suggestion": "Add WHERE clause to filter results",
                    "reason": f"Full table scan returning {query_entry['result_count']} rows"
                })

            if "ORDER BY" in query and "INDEX" not in query:
                suggestions.append({
                    "query": query_entry["query"][:100],
                    "suggestion": "Add index on ORDER BY column",
                    "reason": "Sorting without index is slow"
                })

        return suggestions[:10]  # Return top 10 suggestions


# Global query profiler
query_profiler = QueryProfiler()


def benchmark(iterations: int = 100):
    """
    Decorator to benchmark a function over multiple iterations

    Args:
        iterations: Number of times to run the function

    Usage:
        @benchmark(iterations=1000)
        def my_fast_function():
            # ... code ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            times = []

            print(f"🏁 Benchmarking {func.__name__} ({iterations} iterations)...")

            for i in range(iterations):
                start = time.time()
                result = func(*args, **kwargs)
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            print(f"✅ {func.__name__} benchmark complete:")
            print(f"   Avg: {avg_time:.2f}ms | Min: {min_time:.2f}ms | Max: {max_time:.2f}ms")

            return result  # Return last result

        return wrapper
    return decorator
