#!/usr/bin/env python3
"""
Main entry point for the evaluate package.

This script provides the same functionality as the original evaluate.py
but using the refactored package structure.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from .evaluator import LlamaStackEvaluator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate Llama Stack agents using DeepEval framework"
    )
    parser.add_argument(
        "csv_file",
        help="Path to CSV file containing test cases"
    )
    parser.add_argument(
        "--model", "-m",
        default="llama-3-2-3b",
        help="Model ID to use for the agent (default: llama-3-2-3b)"
    )
    parser.add_argument(
        "--tools", "-t",
        nargs="*",  # Changed from "+" to "*" to allow empty list
        default=None,  # Changed default to None instead of hardcoded list
        help="mcp::* tool groups to enable. If not specified, will auto-discover from server."
    )
    parser.add_argument(
        "--stack-url", "-u",
        default="http://localhost:8080",
        help="Llama Stack server URL (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output file path for results (JSON format)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed results to console"
    )
    
    args = parser.parse_args()
    
    # Handle tools parameter: if it's an empty list, treat it as None for auto-discovery
    tools = args.tools if args.tools else None
    
    # Validate CSV file exists
    if not Path(args.csv_file).exists():
        logger.error(f"CSV file not found: {args.csv_file}")
        sys.exit(1)
    
    # Initialize evaluator
    evaluator = LlamaStackEvaluator(
        stack_url=args.stack_url,
        model_id=args.model,
        tool_groups=tools  # Use the processed tools parameter
    )
    
    # Run evaluation
    try:
        results = await evaluator.run_evaluation(
            csv_file_path=args.csv_file,
            output_file=args.output,
            verbose=args.verbose
        )
        
        if "error" in results:
            logger.error(f"Evaluation failed: {results['error']}")
            sys.exit(1)
        
        # Print summary if not verbose
        if not args.verbose:
            summary = results['summary']
            print(f"Evaluation completed: {summary['successful_evaluations']}/{summary['total_test_cases']} successful ({summary['success_rate']:.2%})")
            
    except KeyboardInterrupt:
        logger.info("Evaluation interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
