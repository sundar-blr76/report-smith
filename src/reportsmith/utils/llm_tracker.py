"""
LLM Usage Tracker and Cost Estimator

Tracks all LLM API calls across the query processing pipeline and estimates costs.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from reportsmith.logger import get_logger

logger = get_logger(__name__)


# Pricing per 1M tokens (as of Nov 2024)
LLM_PRICING = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "text-embedding-3-small": {"input": 0.020, "output": 0.020},
    "text-embedding-3-large": {"input": 0.130, "output": 0.130},
    "text-embedding-ada-002": {"input": 0.100, "output": 0.100},
    # Gemini (FREE for flash models!)
    "gemini-2.5-flash": {"input": 0.00, "output": 0.00},  # FREE!
    "gemini-1.5-flash": {"input": 0.00, "output": 0.00},  # FREE!
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
    # Anthropic
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}


@dataclass
class LLMCall:
    """Represents a single LLM API call"""

    stage: str  # "intent", "sql_enrichment", "semantic_filter", etc.
    provider: str  # "openai", "gemini", "anthropic"
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    prompt_chars: int  # For debugging/logging
    response_chars: int
    request_payload: Optional[str] = None
    response_payload: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def estimate_cost(self) -> float:
        """Estimate cost in USD based on token usage and model pricing"""
        pricing = LLM_PRICING.get(self.model, {"input": 0.0, "output": 0.0})

        input_cost = (self.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "stage": self.stage,
            "provider": self.provider,
            "model": self.model,
            "tokens": {
                "prompt": self.prompt_tokens,
                "completion": self.completion_tokens,
                "total": self.total_tokens,
            },
            "latency_ms": round(self.latency_ms, 2),
            "cost_usd": round(self.estimate_cost(), 6),
            "chars": {"prompt": self.prompt_chars, "response": self.response_chars},
        }


class LLMTracker:
    """Tracks all LLM calls in a query processing session"""

    def __init__(self):
        self.calls: List[LLMCall] = []

    def track_call(
        self,
        stage: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        prompt_chars: int = 0,
        response_chars: int = 0,
        request_payload: Optional[str] = None,
        response_payload: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMCall:
        """
        Track an LLM API call

        Args:
            stage: Which stage made the call (e.g., "intent", "sql_enrichment")
            provider: LLM provider ("openai", "gemini", "anthropic")
            model: Model name
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            latency_ms: Response time in milliseconds
            prompt_chars: Character count of prompt (for logging)
            response_chars: Character count of response
            request_payload: Full request payload (optional, for debugging)
            response_payload: Full response payload (optional, for debugging)
            metadata: Additional metadata

        Returns:
            LLMCall object
        """
        total_tokens = prompt_tokens + completion_tokens

        call = LLMCall(
            stage=stage,
            provider=provider,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            latency_ms=latency_ms,
            prompt_chars=prompt_chars,
            response_chars=response_chars,
            request_payload=request_payload,
            response_payload=response_payload,
            metadata=metadata or {},
        )

        self.calls.append(call)

        # Log the call with cost
        cost = call.estimate_cost()
        logger.info(
            f"💰 [llm-tracker] {stage} | {provider}/{model} | "
            f"tokens: {prompt_tokens}+{completion_tokens}={total_tokens} | "
            f"latency: {latency_ms:.1f}ms | "
            f"cost: ${cost:.6f}"
        )

        return call

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of all LLM calls with cost breakdown

        Returns:
            Dictionary with summary statistics
        """
        if not self.calls:
            return {
                "total_calls": 0,
                "total_tokens": 0,
                "total_cost_usd": 0.0,
                "total_latency_ms": 0.0,
                "by_stage": {},
                "by_provider": {},
                "calls": [],
            }

        total_tokens = sum(c.total_tokens for c in self.calls)
        total_cost = sum(c.estimate_cost() for c in self.calls)
        total_latency = sum(c.latency_ms for c in self.calls)

        # Group by stage
        by_stage = {}
        for call in self.calls:
            if call.stage not in by_stage:
                by_stage[call.stage] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "latency_ms": 0.0,
                }
            by_stage[call.stage]["calls"] += 1
            by_stage[call.stage]["tokens"] += call.total_tokens
            by_stage[call.stage]["cost_usd"] += call.estimate_cost()
            by_stage[call.stage]["latency_ms"] += call.latency_ms

        # Group by provider
        by_provider = {}
        for call in self.calls:
            if call.provider not in by_provider:
                by_provider[call.provider] = {
                    "calls": 0,
                    "tokens": 0,
                    "cost_usd": 0.0,
                    "models": set(),
                }
            by_provider[call.provider]["calls"] += 1
            by_provider[call.provider]["tokens"] += call.total_tokens
            by_provider[call.provider]["cost_usd"] += call.estimate_cost()
            by_provider[call.provider]["models"].add(call.model)

        # Convert sets to lists for JSON serialization
        for provider_data in by_provider.values():
            provider_data["models"] = list(provider_data["models"])

        # Round values
        for stage_data in by_stage.values():
            stage_data["cost_usd"] = round(stage_data["cost_usd"], 6)
            stage_data["latency_ms"] = round(stage_data["latency_ms"], 2)

        for provider_data in by_provider.values():
            provider_data["cost_usd"] = round(provider_data["cost_usd"], 6)

        return {
            "total_calls": len(self.calls),
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost, 6),
            "total_latency_ms": round(total_latency, 2),
            "by_stage": by_stage,
            "by_provider": by_provider,
            "calls": [call.to_dict() for call in self.calls],
        }

    def format_summary(self) -> str:
        """
        Format summary as human-readable string

        Returns:
            Formatted summary text
        """
        summary = self.get_summary()

        if summary["total_calls"] == 0:
            return "No LLM calls tracked"

        lines = [
            "=" * 80,
            "LLM USAGE SUMMARY",
            "=" * 80,
            f"Total Calls:    {summary['total_calls']}",
            f"Total Tokens:   {summary['total_tokens']:,}",
            f"Total Cost:     ${summary['total_cost_usd']:.6f}",
            f"Total Latency:  {summary['total_latency_ms']:.1f}ms",
            "",
            "BY STAGE:",
        ]

        for stage, data in summary["by_stage"].items():
            lines.append(
                f"  {stage:20s}: {data['calls']:2d} calls, "
                f"{data['tokens']:6,} tokens, "
                f"${data['cost_usd']:.6f}, "
                f"{data['latency_ms']:.1f}ms"
            )

        lines.extend(["", "BY PROVIDER:"])
        for provider, data in summary["by_provider"].items():
            models = ", ".join(data["models"])
            lines.append(
                f"  {provider:10s}: {data['calls']:2d} calls, "
                f"{data['tokens']:6,} tokens, "
                f"${data['cost_usd']:.6f} ({models})"
            )

        lines.append("=" * 80)
        return "\n".join(lines)
