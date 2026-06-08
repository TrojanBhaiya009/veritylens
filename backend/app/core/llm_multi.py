"""
LLM wrapper — multi-provider support with user-provided API keys.
Supports: OpenAI, Anthropic, Google Gemini, OpenRouter, Custom (Ollama/local)
"""

import json
import logging
import os
import re
import asyncio
from typing import Optional, Literal

logger = logging.getLogger(__name__)

ModelProvider = Literal['openai', 'anthropic', 'google', 'openrouter', 'custom', 'duckduckgo']


async def ask_llm(
    prompt: str,
    provider: ModelProvider = 'duckduckgo',
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 2
) -> str:
    """
    Unified LLM interface supporting multiple providers.
    
    Args:
        prompt: The input prompt
        provider: LLM provider to use
        api_key: User's API key (not needed for 'custom' with Ollama)
        base_url: Custom base URL (for Ollama or custom endpoints)
        model: Model name/ID
        max_retries: Number of retries on failure
    
    Returns:
        LLM response as string
    
    Raises:
        RuntimeError: If all providers fail
    """
    
    if provider == 'duckduckgo':
        # Original DuckDuckGo Chat (free, no key needed)
        from .llm import ask_llm as ask_llm_ddg
        return await ask_llm_ddg(prompt, max_retries)
    
    elif provider == 'openai':
        return await _call_openai(prompt, api_key, base_url, model, max_retries)
    
    elif provider == 'anthropic':
        return await _call_anthropic(prompt, api_key, model, max_retries)
    
    elif provider == 'google':
        return await _call_google(prompt, api_key, model, max_retries)
    
    elif provider == 'openrouter':
        return await _call_openrouter(prompt, api_key, model, max_retries)
    
    elif provider == 'custom':
        return await _call_custom(prompt, api_key, base_url, model, max_retries)
    
    else:
        raise ValueError(f"Unsupported provider: {provider}")


async def _call_openai(
    prompt: str,
    api_key: str,
    base_url: Optional[str] = None,
    model: str = 'gpt-4o',
    max_retries: int = 2
) -> str:
    """Call OpenAI-compatible API (includes Ollama via custom base_url)."""
    try:
        from openai import AsyncOpenAI
        
        client_kwargs = {'api_key': api_key or 'dummy'}
        if base_url:
            client_kwargs['base_url'] = base_url
        
        client = AsyncOpenAI(**client_kwargs)
        
        for attempt in range(max_retries):
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[{'role': 'user', 'content': prompt}],
                    temperature=0.1,
                    timeout=30.0
                )
                return response.choices[0].message.content.strip()
            
            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
        
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


async def _call_anthropic(
    prompt: str,
    api_key: str,
    model: str = 'claude-3-5-sonnet-20241022',
    max_retries: int = 2
) -> str:
    """Call Anthropic Claude API."""
    try:
        import anthropic
        
        client = anthropic.AsyncAnthropic(api_key=api_key)
        
        for attempt in range(max_retries):
            try:
                response = await client.messages.create(
                    model=model,
                    max_tokens=1024,
                    messages=[{'role': 'user', 'content': prompt}],
                    timeout=30.0
                )
                return response.content[0].text.strip()
            
            except Exception as e:
                logger.warning(f"Anthropic attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
    
    except ImportError:
        raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
    except Exception as e:
        raise RuntimeError(f"Anthropic API error: {e}")


async def _call_google(
    prompt: str,
    api_key: str,
    model: str = 'gemini-2.0-flash-exp',
    max_retries: int = 2
) -> str:
    """Call Google Gemini API."""
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        
        for attempt in range(max_retries):
            try:
                response = await model_obj.generate_content_async(
                    prompt,
                    generation_config={'temperature': 0.1}
                )
                return response.text.strip()
            
            except Exception as e:
                logger.warning(f"Google attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(1 * (attempt + 1))
    
    except ImportError:
        raise RuntimeError("google-generativeai package not installed. Run: pip install google-generativeai")
    except Exception as e:
        raise RuntimeError(f"Google API error: {e}")


async def _call_openrouter(
    prompt: str,
    api_key: str,
    model: str = 'openai/gpt-4o',
    max_retries: int = 2
) -> str:
    """Call OpenRouter API (aggregates multiple models)."""
    # OpenRouter uses OpenAI-compatible API
    return await _call_openai(
        prompt,
        api_key=api_key,
        base_url='https://openrouter.ai/api/v1',
        model=model,
        max_retries=max_retries
    )


async def _call_custom(
    prompt: str,
    api_key: Optional[str] = None,
    base_url: str = 'http://localhost:11434/v1',
    model: str = 'llama3.3:70b',
    max_retries: int = 2
) -> str:
    """Call custom endpoint (Ollama, local server, etc.)."""
    # For Ollama, api_key can be dummy
    return await _call_openai(
        prompt,
        api_key=api_key or 'ollama',
        base_url=base_url,
        model=model,
        max_retries=max_retries
    )


# ============================================================
# Provider configurations for frontend
# ============================================================

PROVIDER_CONFIGS = {
    'duckduckgo': {
        'name': 'DuckDuckGo Chat (Free)',
        'models': ['gpt-4o-mini', 'claude-3-haiku', 'mixtral-8x7b', 'llama-3.1-70b'],
        'api_key_required': False,
        'base_url_required': False,
        'description': 'Free multi-model chat via DuckDuckGo. No API key needed.'
    },
    'openai': {
        'name': 'OpenAI',
        'models': ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
        'api_key_required': True,
        'base_url_required': False,
        'api_key_placeholder': 'sk-...',
        'description': 'Premium models with high accuracy. Get key from platform.openai.com'
    },
    'anthropic': {
        'name': 'Anthropic (Claude)',
        'models': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-haiku-20240307'],
        'api_key_required': True,
        'base_url_required': False,
        'api_key_placeholder': 'sk-ant-...',
        'description': 'Excellent reasoning and analysis. Get key from console.anthropic.com'
    },
    'google': {
        'name': 'Google (Gemini)',
        'models': ['gemini-2.0-flash-exp', 'gemini-1.5-pro', 'gemini-1.5-flash'],
        'api_key_required': True,
        'base_url_required': False,
        'api_key_placeholder': 'AIza...',
        'description': 'Free tier available. Get key from aistudio.google.com'
    },
    'openrouter': {
        'name': 'OpenRouter (Aggregated)',
        'models': [
            'openai/gpt-4o',
            'anthropic/claude-3-5-sonnet',
            'google/gemini-pro',
            'meta-llama/llama-3.1-405b',
            'mistralai/mistral-large'
        ],
        'api_key_required': True,
        'base_url_required': False,
        'api_key_placeholder': 'sk-or-...',
        'description': 'Access multiple models via one API. Free credits available at openrouter.ai'
    },
    'custom': {
        'name': 'Custom (Ollama/Local)',
        'models': ['llama3.3:70b', 'mistral:7b', 'gemma2:9b', 'custom-model-name'],
        'api_key_required': False,
        'base_url_required': True,
        'base_url_placeholder': 'http://localhost:11434/v1',
        'description': 'Use local models via Ollama or custom OpenAI-compatible endpoint.'
    }
}


def get_provider_configs() -> dict:
    """Return provider configurations for frontend."""
    return PROVIDER_CONFIGS


def validate_config(provider: str, api_key: Optional[str], base_url: Optional[str], model: str) -> tuple[bool, str]:
    """Validate LLM configuration."""
    if provider not in PROVIDER_CONFIGS:
        return False, f"Invalid provider: {provider}"
    
    config = PROVIDER_CONFIGS[provider]
    
    if config['api_key_required'] and not api_key:
        return False, f"API key required for {config['name']}"
    
    if config['base_url_required'] and not base_url:
        return False, f"Base URL required for {config['name']}"
    
    if not model:
        return False, "Model name is required"
    
    return True, ""


# ============================================================
# Integration with existing verification pipeline
# ============================================================

async def ask_llm_with_fallback(
    prompt: str,
    provider: ModelProvider = 'duckduckgo',
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    max_retries: int = 2
) -> str:
    """
    Call LLM with fallback to DuckDuckGo (free) if primary provider fails.
    This ensures the system always works, even with invalid API keys.
    """
    try:
        return await ask_llm(prompt, provider, api_key, base_url, model, max_retries)
    except Exception as e:
        logger.warning(f"Primary provider '{provider}' failed: {e}")
        logger.info("Falling back to DuckDuckGo Chat (free)")
        
        # Fallback to DuckDuckGo
        try:
            from .llm import ask_llm as ask_llm_ddg
            return await ask_llm_ddg(prompt, max_retries)
        except Exception as fallback_error:
            raise RuntimeError(f"Both primary provider and fallback failed. Primary: {e}. Fallback: {fallback_error}")
