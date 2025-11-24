"""
Performance monitoring and profiling utilities.
"""
import functools
import logging
import time
import tracemalloc
from contextlib import contextmanager
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

# Global performance metrics
_performance_metrics: Dict[str, list] = {}


def track_performance(func: Callable) -> Callable:
    """
    Decorator to track function execution time and memory usage.
    
    Args:
        func: Function to track
        
    Returns:
        Wrapped function with performance tracking
    """
    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.perf_counter()
        start_memory = None
        peak_memory = None
        
        # Track memory if tracemalloc is active
        if tracemalloc.is_tracing():
            start_memory = tracemalloc.take_snapshot()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Calculate memory delta if tracking
            if start_memory and tracemalloc.is_tracing():
                end_memory = tracemalloc.take_snapshot()
                top_stats = end_memory.compare_to(start_memory, 'lineno')
                if top_stats:
                    peak_memory = top_stats[0].size_diff / (1024 * 1024)  # MB
            
            # Store metrics
            if func_name not in _performance_metrics:
                _performance_metrics[func_name] = []
            _performance_metrics[func_name].append({
                'execution_time': execution_time,
                'peak_memory_mb': peak_memory,
            })
            
            # Log slow operations (>1 second)
            if execution_time > 1.0:
                logger.warning(
                    f"Slow operation detected: {func_name} took {execution_time:.2f}s"
                )
    
    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = f"{func.__module__}.{func.__name__}"
        start_time = time.perf_counter()
        start_memory = None
        peak_memory = None
        
        # Track memory if tracemalloc is active
        if tracemalloc.is_tracing():
            start_memory = tracemalloc.take_snapshot()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Calculate memory delta if tracking
            if start_memory and tracemalloc.is_tracing():
                end_memory = tracemalloc.take_snapshot()
                top_stats = end_memory.compare_to(start_memory, 'lineno')
                if top_stats:
                    peak_memory = top_stats[0].size_diff / (1024 * 1024)  # MB
            
            # Store metrics
            if func_name not in _performance_metrics:
                _performance_metrics[func_name] = []
            _performance_metrics[func_name].append({
                'execution_time': execution_time,
                'peak_memory_mb': peak_memory,
            })
            
            # Log slow operations (>1 second)
            if execution_time > 1.0:
                logger.warning(
                    f"Slow operation detected: {func_name} took {execution_time:.2f}s"
                )
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return sync_wrapper


@contextmanager
def measure_time(operation_name: str):
    """
    Context manager to measure execution time.
    
    Args:
        operation_name: Name of the operation being measured
        
    Yields:
        None
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        execution_time = time.perf_counter() - start_time
        logger.debug(f"{operation_name} took {execution_time:.3f}s")


@contextmanager
def measure_memory(operation_name: str):
    """
    Context manager to measure memory usage.
    
    Args:
        operation_name: Name of the operation being measured
        
    Yields:
        None
    """
    if not tracemalloc.is_tracing():
        tracemalloc.start()
    
    start_snapshot = tracemalloc.take_snapshot()
    try:
        yield
    finally:
        end_snapshot = tracemalloc.take_snapshot()
        top_stats = end_snapshot.compare_to(start_snapshot, 'lineno')
        
        if top_stats:
            total_memory = sum(stat.size_diff for stat in top_stats)
            logger.debug(
                f"{operation_name} used {total_memory / (1024 * 1024):.2f}MB"
            )


def get_performance_stats() -> Dict[str, Dict[str, float]]:
    """
    Get aggregated performance statistics.
    
    Returns:
        Dictionary of function names to their performance stats
    """
    stats = {}
    for func_name, metrics in _performance_metrics.items():
        if not metrics:
            continue
        
        execution_times = [m['execution_time'] for m in metrics if m['execution_time']]
        memory_usage = [
            m['peak_memory_mb'] for m in metrics 
            if m.get('peak_memory_mb') is not None
        ]
        
        stats[func_name] = {
            'count': len(metrics),
            'avg_time': sum(execution_times) / len(execution_times) if execution_times else 0,
            'min_time': min(execution_times) if execution_times else 0,
            'max_time': max(execution_times) if execution_times else 0,
            'total_time': sum(execution_times),
            'avg_memory_mb': sum(memory_usage) / len(memory_usage) if memory_usage else None,
            'max_memory_mb': max(memory_usage) if memory_usage else None,
        }
    
    return stats


def reset_performance_stats() -> None:
    """Reset all performance statistics."""
    global _performance_metrics
    _performance_metrics = {}

