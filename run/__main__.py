#!/usr/bin/env python3
"""
Main entry point for the run package.

This script provides the same functionality as the original generate_run_yaml.py
but using the refactored package structure.
"""

import sys
from .yaml_generator import generate_run_yaml


def main():
    """Main function to generate run.yaml from Jinja2 template."""
    generate_run_yaml()


if __name__ == '__main__':
    main()
