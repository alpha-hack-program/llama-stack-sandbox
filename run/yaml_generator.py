"""
YAML generation utilities for Llama Stack configuration.

This module provides functionality to generate run.yaml from Jinja2 templates
using dynamic model and MCP server configurations.
"""

import os
import sys
from .config import (
    get_model_numbers,
    get_mcp_server_numbers,
    get_all_models_config,
    get_all_mcp_servers_config
)

try:
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False


def generate_run_yaml(
    template_file: str = 'templates/run.yaml.template',
    output_file: str = 'run.yaml',
    backup_file: str = 'run.yaml.orig'
) -> None:
    """
    Generate run.yaml from Jinja2 template with dynamic MODEL_* and MCP_SERVER_* environment variables.
    
    Args:
        template_file: Path to the Jinja2 template file
        output_file: Path to the output YAML file
        backup_file: Path to create backup of existing output file
        
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
    if not HAS_JINJA2:
        print("Error: Jinja2 is not installed. Install it with: pip install Jinja2")
        sys.exit(1)
        
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
    
    # Setup Jinja2 environment - look in templates directory and current directory
    env = Environment(
        loader=FileSystemLoader(['templates', '.']),
        trim_blocks=False,
        lstrip_blocks=False
    )
    
    # Extract just the filename if template_file includes a path
    template_name = os.path.basename(template_file)
    
    try:
        template = env.get_template(template_name)
    except TemplateNotFound:
        print(f"Error: Template file {template_name} not found in templates/ or current directory!")
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
