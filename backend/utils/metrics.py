"""
Performance metrics collection for LLM streaming and non-streaming calls.

Tracks TTFB (Time to First Byte), TPS (Tokens Per Second), and token usage
(input/output/total) using provider-reported usage_metadata.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Optional, Any, Dict


@dataclass
class StreamMetrics:
    """Collected metrics for a single LLM call or aggregated debate session."""
    ttfb_ms: Optional[float] = None
    tps: Optional[float] = None
    total_tokens: Optional[int] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ttfb_ms": self.ttfb_ms,
            "tps": self.tps,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model_id": self.model_id,
        }


class MetricsCollector:
    """Collect timing and token usage during a single streaming LLM call."""

    def __init__(self):
        self._start_time: Optional[float] = None
        self._first_chunk_time: Optional[float] = None
        self._last_chunk_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._text_chars: int = 0
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._total_tokens: int = 0
        self._usage_seen: bool = False

    def start(self):
        """Record the start time of the request."""
        self._start_time = time.time()

    def _accumulate_usage(self, usage: Dict[str, Any]):
        """Add usage from one chunk/response to running totals."""
        if not usage:
            return
        inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
        out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
        tot = usage.get("total_tokens") or (inp + out)
        self._input_tokens += inp
        self._output_tokens += out
        self._total_tokens += tot
        self._usage_seen = True

    def on_chunk(self, text: str, chunk: Any):
        """Process a streamed chunk: record TTFB and scan for usage_metadata."""
        if text:
            self._text_chars += len(text)
            now = time.time()
            if self._first_chunk_time is None:
                self._first_chunk_time = now
            self._last_chunk_time = now

        # usage_metadata appears on the chunk carrying finish_reason='stop'
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            self._accumulate_usage(chunk.usage_metadata)
        elif hasattr(chunk, "response_metadata") and chunk.response_metadata:
            # Some providers nest usage differently; only fall back if usage_metadata absent
            rm = chunk.response_metadata
            if isinstance(rm, dict) and "token_usage" in rm:
                self._accumulate_usage(rm["token_usage"])

    def finish(self, model_id: Optional[str] = None) -> StreamMetrics:
        """Compute final metrics after streaming completes."""
        if self._end_time is None:
            self._end_time = time.time()

        ttfb_ms = None
        if self._first_chunk_time is not None and self._start_time is not None:
            ttfb_ms = round((self._first_chunk_time - self._start_time) * 1000, 1)

        total_tokens = self._total_tokens if self._usage_seen else None
        input_tokens = self._input_tokens if self._usage_seen else None
        output_tokens = self._output_tokens if self._usage_seen else None

        # Compute TPS using generation time (first chunk → last chunk),
        # which excludes TTFB and HTTP backpressure from the consumer.
        tps = None
        gen_elapsed = None
        if self._first_chunk_time is not None and self._last_chunk_time is not None:
            gen_elapsed = self._last_chunk_time - self._first_chunk_time

        if output_tokens is not None and output_tokens > 0 and gen_elapsed is not None and gen_elapsed > 0:
            tps = round(output_tokens / gen_elapsed, 1)
        elif self._text_chars > 0 and gen_elapsed is not None and gen_elapsed > 0:
            # Fallback: ~2 chars per token (works for both English and CJK)
            estimated_tokens = self._text_chars / 2
            tps = round(estimated_tokens / gen_elapsed, 1)

        return StreamMetrics(
            ttfb_ms=ttfb_ms,
            tps=tps,
            total_tokens=total_tokens,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model_id=model_id,
        )

    def to_delimited_json(self, model_id: Optional[str] = None) -> str:
        """Return a delimited JSON string suitable for appending to streamed text.

        Calls finish() internally if not already called; safe to call after finish().
        """
        result = self.finish(model_id=model_id)
        json_str = json.dumps(result.to_dict(), ensure_ascii=False)
        return f"\n\n<!--METRICS_JSON{json_str}METRICS_JSON-->"


def strip_metrics_metadata(text: str) -> str:
    """Remove the metrics metadata delimiter from response text."""
    import re
    return re.sub(r"\n?\n?<!--METRICS_JSON.+?METRICS_JSON-->", "", text, flags=re.DOTALL)


class DebateMetricsAccumulator:
    """Accumulate metrics across multiple non-streaming LLM calls in a debate."""

    def __init__(self):
        self._total_input_tokens: int = 0
        self._total_output_tokens: int = 0
        self._total_tokens: int = 0
        self._total_elapsed: float = 0.0
        self._has_any_call: bool = False

    def add_step(self, response: Any, start_time: float, end_time: float):
        """Record timing and token usage from one ainvoke call."""
        if not self._has_any_call:
            self._has_any_call = True

        self._total_elapsed += (end_time - start_time)

        # Extract usage_metadata from the response object
        usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            usage = response.usage_metadata
        elif hasattr(response, "response_metadata") and response.response_metadata:
            rm = response.response_metadata
            if isinstance(rm, dict) and "token_usage" in rm:
                usage = rm["token_usage"]

        if usage:
            inp = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
            out = usage.get("output_tokens") or usage.get("completion_tokens") or 0
            tot = usage.get("total_tokens") or (inp + out)
            self._total_input_tokens += inp
            self._total_output_tokens += out
            self._total_tokens += tot

    def get_totals(self, model_id: Optional[str] = None) -> StreamMetrics:
        """Return aggregated metrics for the entire debate session."""
        tps = None
        if self._total_output_tokens > 0 and self._total_elapsed > 0:
            tps = round(self._total_output_tokens / self._total_elapsed, 1)

        return StreamMetrics(
            ttfb_ms=None,
            tps=tps,
            total_tokens=self._total_tokens if self._total_tokens > 0 else None,
            input_tokens=self._total_input_tokens if self._total_input_tokens > 0 else None,
            output_tokens=self._total_output_tokens if self._total_output_tokens > 0 else None,
            model_id=model_id,
        )
