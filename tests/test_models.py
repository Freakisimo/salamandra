import pytest
from src.config.models import (
    ModelLifecycleResolver,
    TIER_LIGHT,
    TIER_BALANCED,
    TIER_DEEP
)

def test_model_resolver_default_tiers():
    resolver = ModelLifecycleResolver()
    
    light_model = resolver.get_active_model(TIER_LIGHT)
    assert light_model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
    
    deep_model = resolver.get_active_model(TIER_DEEP)
    assert deep_model in ["gemini-2.5-pro", "gemini-2.5-flash"]

def test_model_resolver_dynamic_fallback():
    resolver = ModelLifecycleResolver()
    chain = resolver.get_tier_chain(TIER_LIGHT)
    assert len(chain) >= 2
    
    first_model = chain[0]
    second_model = chain[1]
    
    assert resolver.get_active_model(TIER_LIGHT) == first_model
    
    # Mark first model as failed/deprecated
    resolver.mark_model_failure(first_model, reason="Simulated 404 Model Deprecated")
    
    # Should automatically advance to second model
    assert resolver.get_active_model(TIER_LIGHT) == second_model
