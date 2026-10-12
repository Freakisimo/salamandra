import os
import logging
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.adk.workflow._retry_config import RetryConfig

load_dotenv()

logger = logging.getLogger("salamandra.models")

TIER_LIGHT = "light"
TIER_BALANCED = "balanced"
TIER_DEEP = "deep"

DEFAULT_MODEL_CHAINS: Dict[str, List[str]] = {
    TIER_LIGHT: [
        os.getenv("MODEL_TIER_LIGHT_PRIMARY", "gemini-2.5-flash"),
        "gemini-2.0-flash",
        "gemini-1.5-flash"
    ],
    TIER_BALANCED: [
        os.getenv("MODEL_TIER_BALANCED_PRIMARY", "gemini-2.5-flash"),
        "gemini-2.0-flash",
        "gemini-2.5-pro"
    ],
    TIER_DEEP: [
        os.getenv("MODEL_TIER_DEEP_PRIMARY", "gemini-2.5-flash"),
        "gemini-2.0-flash",
        "gemini-2.5-pro"
    ]
}


class ModelLifecycleResolver:
    """
    Manages LLM model lifecycle, tier assignments, rate-limit resilience,
    and automatic fallbacks when models are deprecated, encounter 429 quota exhaustion,
    or suffer endpoint failures.
    """
    def __init__(self):
        self._disabled_models = set()
        self._tier_chains: Dict[str, List[str]] = {}
        self._load_configuration()

    def _load_configuration(self):
        for tier, default_list in DEFAULT_MODEL_CHAINS.items():
            primary = os.getenv(f"MODEL_TIER_{tier.upper()}_PRIMARY")
            fallbacks_raw = os.getenv(f"MODEL_TIER_{tier.upper()}_FALLBACKS")
            
            chain = []
            if primary:
                chain.append(primary.strip())
            for item in default_list:
                if item not in chain:
                    chain.append(item)
                    
            if fallbacks_raw:
                for f in fallbacks_raw.split(","):
                    f = f.strip()
                    if f and f not in chain:
                        chain.append(f)
            self._tier_chains[tier] = chain

    def get_active_model(self, tier: str) -> str:
        """Returns the first non-disabled model in the tier chain."""
        chain = self._tier_chains.get(tier.lower(), self._tier_chains[TIER_BALANCED])
        for model in chain:
            if model not in self._disabled_models:
                return model
        # Fallback to ultimate safe default if all failed
        logger.warning(f"All models in tier '{tier}' were disabled/exhausted. Falling back to default 'gemini-2.5-flash'.")
        return "gemini-2.5-flash"

    def mark_model_failure(self, model_name: str, reason: str = ""):
        """Marks a model as deprecated or quota-exhausted so subsequent calls switch to fallbacks."""
        logger.error(f"[MODEL DEPRECATION/QUOTA EXHAUSTION] Disabling model '{model_name}'. Reason: {reason}")
        self._disabled_models.add(model_name)

    def get_tier_chain(self, tier: str) -> List[str]:
        return list(self._tier_chains.get(tier.lower(), []))


# Global resolver instance
resolver = ModelLifecycleResolver()


def get_model(tier: str = TIER_BALANCED) -> str:
    """Helper function to fetch current best model for a given effort tier."""
    return resolver.get_active_model(tier)


def get_agent_retry_config() -> RetryConfig:
    """
    Generates an exponential backoff RetryConfig with jitter to mitigate
    transient 429 RESOURCE_EXHAUSTED errors.
    """
    return RetryConfig(
        max_attempts=int(os.getenv("ADK_RETRY_MAX_ATTEMPTS", "4")),
        initial_delay=float(os.getenv("ADK_RETRY_INITIAL_DELAY", "3.0")),
        max_delay=float(os.getenv("ADK_RETRY_MAX_DELAY", "25.0")),
        backoff_factor=2.0,
        jitter=True
    )


def on_model_error_handler(agent_name: str, tier: str):
    """
    Callback generator for Google ADK on_model_error_callback.
    Captures both deprecation (404/410) and quota exhaustion (429 RESOURCE_EXHAUSTED)
    to dynamically switch the agent to the next working fallback model.
    """
    def _handler(error: Exception):
        err_msg = str(error).lower()
        current = resolver.get_active_model(tier)
        
        quota_or_deprecation_triggers = [
            "not found", "deprecated", "404", "unsupported", "invalid model",
            "resource_exhausted", "resourceexhausted", "429", "quota",
            "rate limit", "too many requests"
        ]
        
        if any(term in err_msg for term in quota_or_deprecation_triggers):
            resolver.mark_model_failure(current, reason=str(error))
            new_model = resolver.get_active_model(tier)
            logger.warning(
                f"[AUTO-FAILOVER] Agent '{agent_name}' (Tier '{tier}') encountered error on '{current}'. "
                f"Automatically switching to fallback model '{new_model}'."
            )
            print(
                f"\n[!] Rate Limit/Error detected on model '{current}' in {agent_name}. "
                f"Switching automatically to fallback: '{new_model}'\n"
            )
    return _handler
