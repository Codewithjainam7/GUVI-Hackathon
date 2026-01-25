"""
Observability - Metrics, Monitoring, and Error Tracking
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import functools

import structlog

logger = structlog.get_logger()


@dataclass
class MetricPoint:
    """Single metric data point"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class LatencyStats:
    """Latency statistics"""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    
    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0
    
    def record(self, latency_ms: float):
        self.count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)


class MetricsCollector:
    """
    Collects and exposes metrics for monitoring
    
    Metrics tracked:
    - Request latency (by endpoint)
    - Model usage (Gemini vs Local)
    - Token consumption
    - Scam detection rates
    - Error rates
    """
    
    def __init__(self):
        # Counters
        self._counters: Dict[str, int] = defaultdict(int)
        
        # Latency tracking
        self._latencies: Dict[str, LatencyStats] = defaultdict(LatencyStats)
        
        # Model usage
        self._model_calls: Dict[str, int] = defaultdict(int)
        self._model_tokens: Dict[str, Dict[str, int]] = defaultdict(lambda: {'input': 0, 'output': 0})
        
        # Detection stats
        self._detection_stats = {
            'total_analyzed': 0,
            'scam_detected': 0,
            'false_positive': 0,  # User-reported
            'true_positive': 0,   # User-confirmed
        }
        
        # Error tracking
        self._errors: Dict[str, int] = defaultdict(int)
        self._recent_errors: List[Dict[str, Any]] = []
        self._max_recent_errors = 100
        
        # Start time
        self._start_time = datetime.utcnow()
        
        logger.info("Metrics collector initialized")
    
    # ==================== Counters ====================
    
    def increment(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter"""
        key = self._make_key(name, tags)
        self._counters[key] += value
    
    def get_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> int:
        """Get counter value"""
        key = self._make_key(name, tags)
        return self._counters.get(key, 0)
    
    # ==================== Latency ====================
    
    def record_latency(self, name: str, latency_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record latency for an operation"""
        key = self._make_key(name, tags)
        self._latencies[key].record(latency_ms)
    
    def get_latency_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get latency statistics"""
        key = self._make_key(name, tags)
        stats = self._latencies.get(key, LatencyStats())
        return {
            'count': stats.count,
            'avg_ms': stats.avg_ms,
            'min_ms': stats.min_ms if stats.min_ms != float('inf') else 0,
            'max_ms': stats.max_ms
        }
    
    def timed(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Decorator to time a function"""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    latency_ms = (time.time() - start) * 1000
                    self.record_latency(name, latency_ms, tags)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    latency_ms = (time.time() - start) * 1000
                    self.record_latency(name, latency_ms, tags)
            
            if asyncio_iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        return decorator
    
    # ==================== Model Usage ====================
    
    def record_model_call(self, model: str, input_tokens: int, output_tokens: int):
        """Record LLM model usage"""
        self._model_calls[model] += 1
        self._model_tokens[model]['input'] += input_tokens
        self._model_tokens[model]['output'] += output_tokens
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model usage statistics"""
        return {
            'calls': dict(self._model_calls),
            'tokens': {
                model: {
                    'input': tokens['input'],
                    'output': tokens['output'],
                    'total': tokens['input'] + tokens['output']
                }
                for model, tokens in self._model_tokens.items()
            }
        }
    
    # ==================== Detection Stats ====================
    
    def record_detection(self, is_scam: bool, confidence: float):
        """Record a scam detection"""
        self._detection_stats['total_analyzed'] += 1
        if is_scam:
            self._detection_stats['scam_detected'] += 1
    
    def record_feedback(self, was_correct: bool):
        """Record user feedback on detection"""
        if was_correct:
            self._detection_stats['true_positive'] += 1
        else:
            self._detection_stats['false_positive'] += 1
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        total = self._detection_stats['total_analyzed']
        scams = self._detection_stats['scam_detected']
        
        return {
            'total_analyzed': total,
            'scam_detected': scams,
            'detection_rate': scams / total if total > 0 else 0,
            'true_positive': self._detection_stats['true_positive'],
            'false_positive': self._detection_stats['false_positive'],
            'accuracy': self._calculate_accuracy()
        }
    
    def _calculate_accuracy(self) -> float:
        """Calculate accuracy from feedback"""
        tp = self._detection_stats['true_positive']
        fp = self._detection_stats['false_positive']
        total = tp + fp
        return tp / total if total > 0 else 0
    
    # ==================== Errors ====================
    
    def record_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Record an error"""
        self._errors[error_type] += 1
        
        error_entry = {
            'type': error_type,
            'message': message,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self._recent_errors.append(error_entry)
        if len(self._recent_errors) > self._max_recent_errors:
            self._recent_errors.pop(0)
        
        logger.error("Error recorded", error_type=error_type, message=message)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            'counts': dict(self._errors),
            'total': sum(self._errors.values()),
            'recent': self._recent_errors[-10:]  # Last 10 errors
        }
    
    # ==================== Summary ====================
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics as a summary"""
        uptime = datetime.utcnow() - self._start_time
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'counters': dict(self._counters),
            'latencies': {
                name: self.get_latency_stats(name)
                for name in self._latencies.keys()
            },
            'models': self.get_model_stats(),
            'detection': self.get_detection_stats(),
            'errors': self.get_error_stats()
        }
    
    def _make_key(self, name: str, tags: Optional[Dict[str, str]] = None) -> str:
        """Create a unique key from name and tags"""
        if not tags:
            return name
        tag_str = ','.join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}[{tag_str}]"


def asyncio_iscoroutinefunction(func):
    """Check if function is async"""
    import asyncio
    return asyncio.iscoroutinefunction(func)


# Singleton instance
_metrics: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Get or create metrics collector singleton"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
