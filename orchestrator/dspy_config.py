"""
DSPy Configuration Module

Configures DSPy with Mistral AI as the language model backend.
This module provides centralized configuration for all DSPy operations.
"""

import os
import logging
from typing import Optional
import dspy
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class MistralLM(dspy.LM):
    """
    Custom Mistral LM adapter for DSPy

    DSPy uses LiteLLM under the hood which supports Mistral natively,
    but we create this wrapper for explicit configuration.
    """

    def __init__(
        self,
        model: str = "mistral/mistral-large-latest",
        api_key: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        **kwargs
    ):
        """
        Initialize Mistral LM for DSPy

        Args:
            model: Mistral model name (via LiteLLM format)
            api_key: Mistral API key (from env if not provided)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional LiteLLM parameters
        """
        # Get API key from environment if not provided
        if api_key is None:
            api_key = os.getenv('MISTRAL_API_KEY')
            if not api_key:
                raise ValueError("MISTRAL_API_KEY not found in environment")

        # Set up the model configuration
        super().__init__(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        logger.info(f"Initialized Mistral LM: {model} (temp={temperature}, max_tokens={max_tokens})")


def setup_dspy(
    model: str = "mistral/mistral-small-latest",
    api_key: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2500,
    cache_enabled: bool = True
) -> dspy.LM:
    """
    Configure DSPy with Mistral as the LM backend

    This function sets up the global DSPy configuration and returns
    the configured language model instance.

    Args:
        model: Mistral model to use
               Default: "mistral/mistral-small-latest" (cost-effective)
               Fallback: "mistral/mistral-medium-latest"
               Options: "mistral/mistral-small-latest",
                       "mistral/mistral-medium-latest",
                       "mistral/mistral-large-latest"
        api_key: Mistral API key (optional, reads from env)
        temperature: Sampling temperature for responses
        max_tokens: Maximum tokens per response
        cache_enabled: Enable response caching

    Returns:
        Configured DSPy LM instance

    Example:
        >>> lm = setup_dspy()
        >>> # DSPy is now configured and ready to use
        >>> classifier = dspy.Predict(IntentSignature)
    """
    try:
        # Create Mistral LM instance
        lm = MistralLM(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Configure DSPy settings
        dspy.configure(
            lm=lm,
            # Enable caching for faster development
            cache_turn_on=cache_enabled
        )

        logger.info("DSPy configured successfully with Mistral backend")
        return lm

    except Exception as e:
        logger.error(f"Failed to configure DSPy: {e}")
        raise


def get_small_model() -> dspy.LM:
    """
    Get a small, fast Mistral model for simple tasks

    Returns:
        Configured small model LM
    """
    return MistralLM(
        model="mistral/mistral-small-latest",
        temperature=0.2,
        max_tokens=1000
    )


def get_medium_model() -> dspy.LM:
    """
    Get a medium Mistral model for complex tasks (fallback from small)

    Returns:
        Configured medium model LM
    """
    return MistralLM(
        model="mistral/mistral-medium-latest",
        temperature=0.2,
        max_tokens=2500
    )


def get_creative_model() -> dspy.LM:
    """
    Get a model with higher temperature for creative/flexible tasks

    Returns:
        Configured creative model LM
    """
    return MistralLM(
        model="mistral/mistral-small-latest",
        temperature=0.7,
        max_tokens=2500
    )


# Configuration presets for different use cases
# Strategy: Use small model first, fallback to medium if needed (cost optimization)
INTENT_CONFIG = {
    "model": "mistral/mistral-small-latest",
    "temperature": 0.2,
    "max_tokens": 500
}

EXTRACTION_CONFIG = {
    "model": "mistral/mistral-small-latest",
    "temperature": 0.2,
    "max_tokens": 2500
}

MATCHING_CONFIG = {
    "model": "mistral/mistral-small-latest",
    "temperature": 0.3,
    "max_tokens": 1000
}
