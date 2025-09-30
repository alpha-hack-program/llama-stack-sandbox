#!/usr/bin/env python3
"""
Example script showing how to use the Llama Stack evaluation framework.
"""

import asyncio
import logging
from pathlib import Path
from evaluation_config import EvaluationConfig, get_config
from evaluation_utils import setup_evaluation_environment, CSVTestCaseLoader

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_basic_evaluation():
    """Run a basic evaluation example."""
    try:
        # Import main evaluator (only when deepeval is available)
        from evaluate import LlamaStackEvaluator
        
        # Setup evaluation environment
        setup_evaluation_environment()
        logger.info("Evaluation environment setup complete")
        
        # Load configuration
        config = get_config('development')  # Use development config
        logger.info(f"Using configuration: {config.stack_url}, model: {config.default_model_id}")
        
        # Load and validate test cases
        csv_loader = CSVTestCaseLoader(config.default_csv_file)
        test_cases = csv_loader.load_and_validate()
        
        if not test_cases:
            logger.error(f"No valid test cases found in {config.default_csv_file}")
            return
        
        logger.info(f"Loaded {len(test_cases)} test cases")
        logger.info(f"Categories: {', '.join(csv_loader.get_categories())}")
        
        # Initialize evaluator
        evaluator = LlamaStackEvaluator(
            stack_url=config.stack_url,
            model_id=config.default_model_id,
            tool_groups=config.default_tool_groups
        )
        
        # Run evaluation
        results = await evaluator.run_evaluation(
            csv_file_path=config.default_csv_file,
            output_file=config.get_output_file_path("example_results.json"),
            verbose=config.verbose_output
        )
        
        if "error" in results:
            logger.error(f"Evaluation failed: {results['error']}")
            return
        
        # Print summary
        summary = results['summary']
        logger.info("="*50)
        logger.info("EVALUATION COMPLETE")
        logger.info("="*50)
        logger.info(f"Test cases: {summary['total_test_cases']}")
        logger.info(f"Successful: {summary['successful_evaluations']}")
        logger.info(f"Success rate: {summary['success_rate']:.2%}")
        logger.info("="*50)
        
    except ImportError as e:
        logger.error(f"Missing dependencies: {e}")
        logger.info("Please install required packages: pip install -r requirements.txt")
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")


async def run_category_evaluation():
    """Run evaluation for a specific category."""
    try:
        from evaluate import LlamaStackEvaluator
        
        config = get_config('development')
        
        # Load test cases and filter by category
        csv_loader = CSVTestCaseLoader(config.default_csv_file)
        all_test_cases = csv_loader.load_and_validate()
        
        # Evaluate penalty calculations only
        penalty_cases = csv_loader.filter_by_category("Penalty Calculations")
        
        if not penalty_cases:
            logger.info("No penalty calculation test cases found")
            return
        
        logger.info(f"Running evaluation for {len(penalty_cases)} penalty calculation test cases")
        
        # Create temporary CSV with filtered cases
        import csv
        import json
        temp_csv = "temp_penalty_cases.csv"
        
        with open(temp_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['question', 'expected_answer', 'tool_name', 'tool_parameters', 'evaluation_criteria', 'category']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for case in penalty_cases:
                writer.writerow({
                    'question': case['question'],
                    'expected_answer': case['expected_answer'],
                    'tool_name': case['tool_name'],
                    'tool_parameters': json.dumps(case['tool_parameters']),
                    'evaluation_criteria': case['evaluation_criteria'],
                    'category': case['category']
                })
        
        # Run evaluation on filtered cases
        evaluator = LlamaStackEvaluator(
            stack_url=config.stack_url,
            model_id=config.default_model_id,
            tool_groups=config.default_tool_groups
        )
        
        results = await evaluator.run_evaluation(
            csv_file_path=temp_csv,
            output_file=config.get_output_file_path("penalty_evaluation_results.json"),
            verbose=True
        )
        
        # Clean up temporary file
        Path(temp_csv).unlink(missing_ok=True)
        
        if "error" not in results:
            summary = results['summary']
            logger.info(f"Penalty calculations evaluation: {summary['successful_evaluations']}/{summary['total_test_cases']} successful")
        
    except ImportError:
        logger.error("DeepEval not available. Install with: pip install -r requirements.txt")
    except Exception as e:
        logger.error(f"Category evaluation failed: {e}")


def demonstrate_configuration():
    """Demonstrate different configuration options."""
    logger.info("Available configurations:")
    
    # Show available configs
    from evaluation_config import DEFAULT_CONFIGS
    for config_name in DEFAULT_CONFIGS:
        config = get_config(config_name)
        logger.info(f"  {config_name}: {config.stack_url}, {config.default_model_id}")
    
    # Create custom config
    custom_config = EvaluationConfig(
        stack_url="http://custom-llama-stack:8321",
        default_model_id="llama-4-scout-17b-16e-w4a16",
        default_tool_groups=["mcp::compatibility"],
        verbose_output=True,
        parallel_evaluation=True,
        max_concurrent_evaluations=5
    )
    
    logger.info("Custom configuration created:")
    logger.info(f"  URL: {custom_config.stack_url}")
    logger.info(f"  Model: {custom_config.default_model_id}")
    logger.info(f"  Tools: {custom_config.default_tool_groups}")
    logger.info(f"  Parallel: {custom_config.parallel_evaluation}")


def show_csv_analysis():
    """Analyze the CSV file structure."""
    config = get_config('development')
    
    if not Path(config.default_csv_file).exists():
        logger.error(f"CSV file not found: {config.default_csv_file}")
        return
    
    # Load and analyze test cases
    csv_loader = CSVTestCaseLoader(config.default_csv_file)
    test_cases = csv_loader.load_and_validate()
    
    logger.info("CSV Analysis:")
    logger.info(f"  Total test cases: {len(test_cases)}")
    logger.info(f"  Categories: {len(csv_loader.get_categories())}")
    
    # Category breakdown
    for category in csv_loader.get_categories():
        category_cases = csv_loader.filter_by_category(category)
        tools = set(case['tool_name'] for case in category_cases)
        logger.info(f"    {category}: {len(category_cases)} cases, tools: {', '.join(tools)}")
    
    # Tool usage
    all_tools = set(case['tool_name'] for case in test_cases)
    logger.info(f"  Tools used: {', '.join(all_tools)}")
    
    # Sample test case
    if test_cases:
        sample = test_cases[0]
        logger.info("Sample test case:")
        logger.info(f"  Question: {sample['question'][:100]}...")
        logger.info(f"  Tool: {sample['tool_name']}")
        logger.info(f"  Parameters: {sample['tool_parameters']}")
        logger.info(f"  Category: {sample['category']}")


async def main():
    """Main example function."""
    logger.info("Llama Stack Evaluation Framework Example")
    logger.info("="*50)
    
    # Show configuration options
    demonstrate_configuration()
    print()
    
    # Analyze CSV structure
    show_csv_analysis()
    print()
    
    # Check if evaluation can run
    config = get_config('development')
    if not Path(config.default_csv_file).exists():
        logger.error("CSV file not found. Please ensure scratch/compatibility.csv exists")
        return
    
    # Ask user what to run
    print("Choose an option:")
    print("1. Run basic evaluation (all test cases)")
    print("2. Run category-specific evaluation (penalty calculations only)")
    print("3. Setup evaluation environment only")
    print("4. Exit")
    
    try:
        choice = input("Enter choice (1-4): ").strip()
        
        if choice == "1":
            await run_basic_evaluation()
        elif choice == "2":
            await run_category_evaluation()
        elif choice == "3":
            setup_evaluation_environment()
            logger.info("Evaluation environment setup complete!")
        elif choice == "4":
            logger.info("Exiting...")
        else:
            logger.info("Invalid choice")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
