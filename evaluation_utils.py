"""
Utility functions and classes for Llama Stack evaluation system.
"""

import json
import csv
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class EvaluationReport:
    """Class for generating evaluation reports."""
    
    def __init__(self, results: Dict[str, Any]):
        self.results = results
        self.timestamp = datetime.now()
    
    def generate_summary_report(self) -> str:
        """Generate a summary report in text format."""
        summary = self.results.get('summary', {})
        metric_averages = self.results.get('metric_averages', {})
        category_results = self.results.get('category_results', {})
        
        report_lines = [
            "="*60,
            "LLAMA STACK AGENT EVALUATION REPORT",
            "="*60,
            f"Generated: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY:",
            f"  Total test cases: {summary.get('total_test_cases', 0)}",
            f"  Successful evaluations: {summary.get('successful_evaluations', 0)}",
            f"  Failed evaluations: {summary.get('failed_evaluations', 0)}",
            f"  Overall success rate: {summary.get('success_rate', 0):.2%}",
            ""
        ]
        
        if metric_averages:
            report_lines.extend([
                "METRIC PERFORMANCE:",
                ""
            ])
            for metric_name, metric_data in metric_averages.items():
                report_lines.extend([
                    f"  {metric_name}:",
                    f"    Average Score: {metric_data.get('average_score', 0):.3f}",
                    f"    Success Rate: {metric_data.get('success_rate', 0):.2%}",
                    ""
                ])
        
        if category_results:
            report_lines.extend([
                "CATEGORY BREAKDOWN:",
                ""
            ])
            for category, results in category_results.items():
                successful = sum(1 for r in results if 'error' not in r)
                total = len(results)
                success_rate = successful / total if total > 0 else 0
                report_lines.append(f"  {category}: {successful}/{total} ({success_rate:.2%})")
            report_lines.append("")
        
        # Configuration info
        config = self.results.get('configuration', {})
        if config:
            report_lines.extend([
                "CONFIGURATION:",
                f"  Model: {config.get('model_id', 'Unknown')}",
                f"  Tool Groups: {', '.join(config.get('tool_groups', []))}",
                f"  Stack URL: {config.get('stack_url', 'Unknown')}",
                ""
            ])
        
        report_lines.append("="*60)
        
        return "\\n".join(report_lines)
    
    def generate_detailed_report(self) -> str:
        """Generate a detailed report including individual test case results."""
        summary_report = self.generate_summary_report()
        
        detailed_lines = [
            summary_report,
            "",
            "DETAILED RESULTS:",
            "="*60,
            ""
        ]
        
        detailed_results = self.results.get('detailed_results', [])
        
        for i, result in enumerate(detailed_results, 1):
            detailed_lines.extend([
                f"Test Case {i}:",
                f"  Input: {result.get('input', 'N/A')[:100]}{'...' if len(result.get('input', '')) > 100 else ''}",
                ""
            ])
            
            if 'error' in result:
                detailed_lines.extend([
                    f"  Status: ERROR",
                    f"  Error: {result['error']}",
                    ""
                ])
                continue
            
            detailed_lines.append("  Status: SUCCESS")
            
            if 'metric_results' in result:
                detailed_lines.append("  Metric Results:")
                for metric_name, metric_result in result['metric_results'].items():
                    score = metric_result.get('score', 0)
                    success = metric_result.get('success', False)
                    reason = metric_result.get('reason', 'N/A')
                    
                    detailed_lines.extend([
                        f"    {metric_name}:",
                        f"      Score: {score:.3f}",
                        f"      Success: {success}",
                        f"      Reason: {reason}",
                        ""
                    ])
            
            detailed_lines.append("-" * 40)
            detailed_lines.append("")
        
        return "\\n".join(detailed_lines)
    
    def save_report(self, filepath: str, detailed: bool = False):
        """Save report to file."""
        report_content = self.generate_detailed_report() if detailed else self.generate_summary_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        logger.info(f"Report saved to {filepath}")
    
    def save_json_report(self, filepath: str):
        """Save results as JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON report saved to {filepath}")


class CSVTestCaseLoader:
    """Enhanced CSV loader with validation and preprocessing."""
    
    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.test_cases = []
        self.validation_errors = []
    
    def load_and_validate(self) -> List[Dict[str, Any]]:
        """Load CSV and validate test cases."""
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 because of header
                    test_case = self._process_row(row, row_num)
                    if test_case:
                        self.test_cases.append(test_case)
            
            logger.info(f"Loaded {len(self.test_cases)} valid test cases from {self.csv_file}")
            
            if self.validation_errors:
                logger.warning(f"Found {len(self.validation_errors)} validation errors")
                for error in self.validation_errors:
                    logger.warning(error)
            
            return self.test_cases
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {self.csv_file}")
            return []
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return []
    
    def _process_row(self, row: Dict[str, str], row_num: int) -> Optional[Dict[str, Any]]:
        """Process and validate a single CSV row."""
        try:
            # Required fields
            required_fields = ['question', 'expected_answer', 'tool_name', 'evaluation_criteria', 'category']
            
            for field in required_fields:
                if not row.get(field, '').strip():
                    self.validation_errors.append(f"Row {row_num}: Missing required field '{field}'")
                    return None
            
            # Parse tool parameters
            tool_parameters = {}
            if row.get('tool_parameters', '').strip():
                try:
                    tool_parameters = json.loads(row['tool_parameters'])
                except json.JSONDecodeError as e:
                    self.validation_errors.append(f"Row {row_num}: Invalid JSON in tool_parameters: {e}")
                    return None
            
            # Create test case
            test_case = {
                'question': row['question'].strip(),
                'expected_answer': row['expected_answer'].strip(),
                'tool_name': row['tool_name'].strip(),
                'tool_parameters': tool_parameters,
                'evaluation_criteria': row['evaluation_criteria'].strip(),
                'category': row['category'].strip(),
                'row_number': row_num
            }
            
            return test_case
            
        except Exception as e:
            self.validation_errors.append(f"Row {row_num}: Error processing row: {e}")
            return None
    
    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        return list(set(tc['category'] for tc in self.test_cases))
    
    def filter_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Filter test cases by category."""
        return [tc for tc in self.test_cases if tc['category'] == category]
    
    def filter_by_tool(self, tool_name: str) -> List[Dict[str, Any]]:
        """Filter test cases by tool name."""
        return [tc for tc in self.test_cases if tc['tool_name'] == tool_name]


class EvaluationBenchmark:
    """Class for benchmarking evaluation performance."""
    
    def __init__(self):
        self.benchmark_results = {}
    
    def time_function(self, func_name: str):
        """Decorator to time function execution."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()
                
                execution_time = end_time - start_time
                if func_name not in self.benchmark_results:
                    self.benchmark_results[func_name] = []
                
                self.benchmark_results[func_name].append(execution_time)
                logger.debug(f"{func_name} executed in {execution_time:.3f} seconds")
                
                return result
            return wrapper
        return decorator
    
    def get_benchmark_summary(self) -> Dict[str, Dict[str, float]]:
        """Get benchmark summary statistics."""
        summary = {}
        
        for func_name, times in self.benchmark_results.items():
            summary[func_name] = {
                'count': len(times),
                'total_time': sum(times),
                'average_time': sum(times) / len(times),
                'min_time': min(times),
                'max_time': max(times)
            }
        
        return summary


async def run_parallel_evaluations(
    evaluations: List[tuple],
    max_concurrency: int = 3
) -> List[Any]:
    """
    Run multiple evaluations in parallel with concurrency control.
    
    Args:
        evaluations: List of (function, args, kwargs) tuples
        max_concurrency: Maximum number of concurrent evaluations
    
    Returns:
        List of evaluation results
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def run_single_evaluation(func, args, kwargs):
        async with semaphore:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    
    tasks = [
        run_single_evaluation(func, args, kwargs)
        for func, args, kwargs in evaluations
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results


def create_sample_config() -> str:
    """Create a sample configuration YAML file content."""
    sample_config = """
# Llama Stack Evaluation Configuration

# Llama Stack connection settings
stack_url: "http://localhost:8321"
default_model_id: "llama-3-2-3b"
default_tool_groups:
  - "mcp::compatibility"
  - "mcp::eligibility"

# File paths
default_csv_file: "scratch/compatibility.csv"
output_directory: "evaluation_results"

# Metric weights (should sum to 1.0)
tool_selection_weight: 0.3
parameter_accuracy_weight: 0.3
response_accuracy_weight: 0.4

# Success thresholds
tool_selection_threshold: 1.0
parameter_accuracy_threshold: 0.8
response_accuracy_threshold: 0.7
comprehensive_threshold: 0.7

# Agent configuration
agent_sampling_params:
  strategy: "greedy"
  temperature: 0.0
  max_tokens: 2048

# Evaluation settings
verbose_output: false
save_detailed_results: true
session_cleanup: true
parallel_evaluation: false
max_concurrent_evaluations: 3

# Logging
log_level: "INFO"
log_file: null  # Set to filename to log to file
"""
    return sample_config.strip()


def setup_evaluation_environment(base_dir: str = "."):
    """Set up the evaluation environment with necessary directories and files."""
    base_path = Path(base_dir)
    
    # Create directories
    directories = [
        "evaluation_results",
        "evaluation_results/reports",
        "evaluation_results/logs",
        "configs"
    ]
    
    for directory in directories:
        dir_path = base_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {dir_path}")
    
    # Create sample configuration file
    config_path = base_path / "configs" / "sample_evaluation_config.yaml"
    if not config_path.exists():
        with open(config_path, 'w') as f:
            f.write(create_sample_config())
        logger.info(f"Created sample configuration: {config_path}")
    
    # Create .gitignore for evaluation results
    gitignore_path = base_path / ".gitignore"
    gitignore_content = """
# Evaluation results
evaluation_results/
*.log

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.egg-info/

# Environment
.env
.venv
env/
venv/
"""
    
    if not gitignore_path.exists():
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content.strip())
        logger.info(f"Created .gitignore: {gitignore_path}")


if __name__ == "__main__":
    # Example usage
    setup_evaluation_environment()
    print("Evaluation environment setup complete!")
