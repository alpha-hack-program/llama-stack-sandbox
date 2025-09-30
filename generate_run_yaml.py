#!/usr/bin/env python3
"""
Generate run.yaml from Jinja2 template with dynamic MODEL_* and MCP_SERVER_* environment variables.

Environment variables:
- MODEL_<N>_URL: Model endpoint URL (required for each model)
- MODEL_<N>_MODEL: Model name (required for each model)
- MODEL_<N>_API_TOKEN: API token for the model (required for each model)
- MODEL_<N>_MAX_TOKENS: Maximum tokens (optional, defaults to 12000)
- MODEL_<N>_TLS_VERIFY: Whether to verify TLS certificates (optional, defaults to true)
- MCP_SERVER_<N>_ID: MCP server tool group ID (required for each MCP server)
- MCP_SERVER_<N>_URI: MCP server endpoint URI (required for each MCP server)
- LSD_BASE_DIR: Base directory for database and config paths (optional, defaults to /opt/app-root/src)
"""

import os
import re
import sys
from typing import List, Dict, Any

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


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


def main():
    """Main function to generate run.yaml from Jinja2 template."""
    if not HAS_JINJA2:
        print("Error: Jinja2 is not installed. Install it with: pip install Jinja2")
        sys.exit(1)
        
    template_file = 'run.yaml.template'
    output_file = 'run.yaml'
    backup_file = 'run.yaml.orig'
    
    # Check if template exists
    if not os.path.exists(template_file):
        print(f"Error: Template file {template_file} not found!")
        sys.exit(1)
    
    # Get lsdBaseDir from environment or use default
    lsd_base_dir = os.environ.get('LSD_BASE_DIR', '/opt/app-root/src')
    
    # Discover model numbers
    model_numbers = get_model_numbers()
    
    if not model_numbers:
        print("Warning: No MODEL_*_URL environment variables found!")
        print("Please define MODEL_1_URL, MODEL_1_API_TOKEN, etc. in your .env file")
        sys.exit(1)
    
    # Discover MCP server numbers
    mcp_numbers = get_mcp_server_numbers()
    
    print(f"Found models: {model_numbers}")
    if mcp_numbers:
        print(f"Found MCP servers: {mcp_numbers}")
    print(f"Using base directory: {lsd_base_dir}")
    
    # Create backup of existing run.yaml if it exists and backup doesn't exist yet
    if os.path.exists(output_file) and not os.path.exists(backup_file):
        print(f"Creating backup: {backup_file}")
        with open(output_file, 'r') as src, open(backup_file, 'w') as dst:
            dst.write(src.read())
    
    # Get all models and MCP servers configuration for template
    models_config = get_all_models_config(model_numbers)
    mcp_servers_config = get_all_mcp_servers_config(mcp_numbers)
    
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader('.'),
        trim_blocks=False,
        lstrip_blocks=False
    )
    
    try:
        template = env.get_template(template_file)
    except TemplateNotFound:
        print(f"Error: Template file {template_file} not found!")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading template: {e}")
        sys.exit(1)
    
    # Render template with models data, MCP servers, and base directory
    try:
        rendered_content = template.render(
            models=models_config,
            mcp_servers=mcp_servers_config,
            lsdBaseDir=lsd_base_dir
        )
    except Exception as e:
        print(f"Error rendering template: {e}")
        sys.exit(1)
    
    # Write final run.yaml
    try:
        with open(output_file, 'w') as f:
            f.write(rendered_content)
        print(f"Successfully generated {output_file} with models: {model_numbers}")
        if mcp_numbers:
            print(f"MCP servers configured: {mcp_numbers}")
        print(f"Base directory configured as: {lsd_base_dir}")
    except IOError as e:
        print(f"Error writing output file: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
