"""
Configuration utilities for Llama Stack deployment.

This module provides functions to discover and configure models and MCP servers
from environment variables.
"""

import os
import re
from typing import List, Dict, Any


def get_model_numbers() -> List[int]:
    """Discover all MODEL_*_URL environment variables and extract model numbers."""
    model_numbers = set()
    pattern = re.compile(r'^MODEL_(\d+)_URL$')
    
    for key in os.environ:
        match = pattern.match(key)
        if match:
            model_numbers.add(int(match.group(1)))
    
    return sorted(model_numbers)


def get_mcp_server_numbers() -> List[int]:
    """Discover all MCP_SERVER_*_ID environment variables and extract server numbers."""
    mcp_numbers = set()
    pattern = re.compile(r'^MCP_SERVER_(\d+)_ID$')
    
    for key in os.environ:
        match = pattern.match(key)
        if match:
            mcp_numbers.add(int(match.group(1)))
    
    return sorted(mcp_numbers)


def get_model_config(model_num: int) -> Dict[str, Any]:
    """Get configuration for a specific model number."""
    config = {}
    for suffix in ['URL', 'MODEL', 'API_TOKEN', 'MAX_TOKENS', 'TLS_VERIFY']:
        env_var = f"MODEL_{model_num}_{suffix}"
        value = os.environ.get(env_var)
        if value:
            config[suffix.lower()] = value
    return config


def get_mcp_server_config(mcp_num: int) -> Dict[str, Any]:
    """Get configuration for a specific MCP server number."""
    config = {}
    for suffix in ['ID', 'URI']:
        env_var = f"MCP_SERVER_{mcp_num}_{suffix}"
        value = os.environ.get(env_var)
        if value:
            config[suffix.lower()] = value
    return config


def get_all_models_config(model_numbers: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get configuration for all discovered models."""
    models_config = {}
    for model_num in model_numbers:
        config = get_model_config(model_num)
        if config:  # Only include models that have some configuration
            models_config[model_num] = config
    return models_config


def get_all_mcp_servers_config(mcp_numbers: List[int]) -> Dict[int, Dict[str, Any]]:
    """Get configuration for all discovered MCP servers."""
    mcp_config = {}
    for mcp_num in mcp_numbers:
        config = get_mcp_server_config(mcp_num)
        if config and 'id' in config and 'uri' in config:  # Only include servers with both ID and URI
            mcp_config[mcp_num] = config
    return mcp_config
