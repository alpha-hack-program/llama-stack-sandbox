"""
Main evaluator module for Llama Stack agents using DeepEval framework.
"""

import csv
import json
import logging
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

import asyncio
from llama_stack_client import LlamaStackClient
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.dataset import EvaluationDataset
from deepeval.dataset.golden import Golden

# Import custom evaluation metrics
from .metrics import (
    ToolSelectionMetric,
    ParameterAccuracyMetric,
    ResponseAccuracyMetric,
    ComprehensiveEvaluationMetric
)
from .wrapper import LlamaStackAgentWrapper

logger = logging.getLogger(__name__)


class LlamaStackEvaluator:
    """Main evaluator class for Llama Stack agents."""
    
    def __init__(
        self,
        stack_url: str = "http://localhost:8080",
        model_id: str = "llama-3-2-3b",
        tool_groups: Optional[List[str]] = None
    ):
        """
        Initialize the evaluator.
        
        Args:
            stack_url: URL of the Llama Stack server
            model_id: Model identifier to use for the agent
            tool_groups: List of tool groups to enable for the agent. If None, will auto-discover.
        """
        self.stack_url = stack_url
        self.model_id = model_id
        self.tool_groups = tool_groups  # Don't set default here
        
        # Initialize Llama Stack client
        self.client = LlamaStackClient(base_url=stack_url)
        self.agent_wrapper = None
        
    def load_test_cases_from_csv(self, csv_file_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from CSV file.
        
        Args:
            csv_file_path: Path to the CSV file containing test cases
            
        Returns:
            List of test case dictionaries
        """
        test_cases = []
        
        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    test_case = {
                        'question': row['question'],
                        'expected_answer': row['expected_answer'],
                        'tool_name': row['tool_name'],
                        'tool_parameters': json.loads(row['tool_parameters']) if row['tool_parameters'] else {},
                        'evaluation_criteria': row['evaluation_criteria'],
                        'category': row['category']
                    }
                    test_cases.append(test_case)
                    
            logger.info(f"Loaded {len(test_cases)} test cases from {csv_file_path}")
            return test_cases
            
        except FileNotFoundError:
            logger.error(f"CSV file not found: {csv_file_path}")
            return []
        except Exception as e:
            logger.error(f"Error loading CSV file: {e}")
            return []
    
    async def _discover_available_tools(self) -> List[str]:
        """
        Discover available mcp::* tool groups from the Llama Stack server.
        
        Returns:
            List of available mcp::* tool group identifiers
        """
        try:
            logger.info("Discovering available mcp::* tools from Llama Stack server...")
            
            # Query server for tools
            discovered_tools = await self._query_server_for_tools()
            
            if not discovered_tools:
                # Final fallback to default
                discovered_tools = self._get_default_tools()
                logger.warning("No tools discovered from server, using fallback default tools")
            
            logger.info(f"Using tools: {discovered_tools}")
            return discovered_tools
            
        except Exception as e:
            logger.error(f"Error discovering tools: {e}")
            return self._get_default_tools()
    
    async def _query_server_for_tools(self) -> List[str]:
        """
        Query the server for available mcp::* tools.
        
        Returns:
            List of mcp::* tool groups found on server
        """
        mcp_tools = []
        
        try:
            # Method 1: Try to get tool groups from /v1/toolgroups endpoint
            if hasattr(self.client, 'toolgroups'):
                try:
                    response = await self.client.toolgroups.list()
                    if hasattr(response, 'data'):
                        for tg in response.data:
                            tool_id = getattr(tg, 'identifier', str(tg))
                            if tool_id.startswith('mcp::'):
                                mcp_tools.append(tool_id)
                except Exception:
                    pass
            
            # Method 2: Try manual HTTP request to /v1/toolgroups if client method doesn't work
            if not mcp_tools:
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{self.stack_url}/v1/toolgroups")
                        if response.status_code == 200:
                            data = response.json()
                            if 'data' in data:
                                for item in data['data']:
                                    tool_id = item.get('identifier', '')
                                    if tool_id.startswith('mcp::'):
                                        mcp_tools.append(tool_id)
                except Exception as e:
                    logger.debug(f"Manual toolgroups request failed: {e}")
            
            # Method 3: Legacy fallback - try to get tools and extract groups
            if not mcp_tools and hasattr(self.client, 'tools'):
                try:
                    response = await self.client.tools.list()
                    if response:
                        tool_groups = set()
                        for tool in response:
                            if hasattr(tool, 'tool_group_id'):
                                tool_id = tool.tool_group_id
                                if tool_id.startswith('mcp::'):
                                    tool_groups.add(tool_id)
                        mcp_tools = list(tool_groups)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"Server query failed: {e}")
        
        return mcp_tools
    
    def _get_default_tools(self) -> List[str]:
        """
        Get default mcp::* tool groups as final fallback.
        
        Returns:
            List of default mcp::* tool groups
        """
        return ["mcp::compatibility-engine"]
    
    def _get_recommended_tools(self, available_tools: List[str]) -> List[str]:
        """
        Get recommended tools from available mcp::* tools based on priority.
        
        Args:
            available_tools: List of available mcp::* tool groups
            
        Returns:
            List of recommended mcp::* tool groups
        """
        # Priority order for mcp tools (updated to match actual server tool names)
        priority_order = [
            "mcp::compatibility-engine",
            "mcp::eligibility-engine",
            "mcp::compatibility",  # Keep legacy name as fallback
            "mcp::eligibility",    # Keep legacy name as fallback
            "mcp::finance",
            "mcp::admin"
        ]
        
        recommended = []
        for tool_group in priority_order:
            if tool_group in available_tools:
                recommended.append(tool_group)
        
        # If no priority tools available, return all available mcp tools
        if not recommended and available_tools:
            recommended = available_tools
        
        return recommended if recommended else ["mcp::compatibility-engine"]
    
    async def setup_agent(self) -> bool:
        """
        Set up the Llama Stack agent with specified model and tools.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Discover tools if none were specified
            if self.tool_groups is None:
                available_tools = await self._discover_available_tools()
                self.tool_groups = self._get_recommended_tools(available_tools)
                logger.info(f"Auto-discovered and using tool groups: {self.tool_groups}")
            else:
                logger.info(f"Using specified tool groups: {self.tool_groups}")
            
            self.agent_wrapper = LlamaStackAgentWrapper(
                client=self.client,
                model_id=self.model_id,
                tool_groups=self.tool_groups
            )
            
            # Initialize the agent and check if it was successful
            if not await self.agent_wrapper.initialize():
                logger.error("Agent initialization failed")
                return False
            
            logger.info(f"Agent setup completed with model: {self.model_id} and tools: {self.tool_groups}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup agent: {e}")
            return False
    
    def create_evaluation_dataset(self, test_cases: List[Dict[str, Any]]) -> EvaluationDataset:
        """
        Create DeepEval dataset from test cases.
        
        Args:
            test_cases: List of test case dictionaries
            
        Returns:
            EvaluationDataset for DeepEval
        """
        golden_objects = []
        
        for i, test_case in enumerate(test_cases):
            # Create Golden object for each test case
            golden = Golden(
                input=test_case['question'],
                expected_output=test_case['expected_answer'],
                context=[
                    f"Expected tool: {test_case['tool_name']}",  
                    f"Expected parameters: {json.dumps(test_case['tool_parameters'])}",
                    f"Evaluation criteria: {test_case['evaluation_criteria']}",
                    f"Category: {test_case['category']}"
                ],
                additional_metadata={
                    "tool_name": test_case['tool_name'],
                    "tool_parameters": test_case['tool_parameters'],
                    "evaluation_criteria": test_case['evaluation_criteria'],
                    "category": test_case['category']
                }
            )
            golden_objects.append(golden)
        
        dataset = EvaluationDataset(goldens=golden_objects)
        logger.info(f"Created evaluation dataset with {len(golden_objects)} test cases")
        return dataset
    
    async def run_evaluation(
        self,
        csv_file_path: str,
        output_file: Optional[str] = None,
        verbose: bool = False
    ) -> Dict[str, Any]:
        """
        Run the complete evaluation pipeline.
        
        Args:
            csv_file_path: Path to CSV file with test cases
            output_file: Optional path to save results
            verbose: Whether to print detailed results
            
        Returns:
            Dictionary containing evaluation results
        """
        # Load test cases
        test_cases = self.load_test_cases_from_csv(csv_file_path)
        if not test_cases:
            return {"error": "No test cases loaded"}
        
        # Setup agent
        if not await self.setup_agent():
            return {"error": "Failed to setup agent"}
        
        # Create dataset
        dataset = self.create_evaluation_dataset(test_cases)
        
        # Initialize evaluation metrics
        metrics = [
            ToolSelectionMetric(agent_wrapper=self.agent_wrapper),
            ParameterAccuracyMetric(agent_wrapper=self.agent_wrapper),
            ResponseAccuracyMetric(agent_wrapper=self.agent_wrapper),
            ComprehensiveEvaluationMetric(agent_wrapper=self.agent_wrapper)
        ]
        
        # Run evaluation
        logger.info("Starting evaluation...")
        results = await self._run_evaluation_with_metrics(dataset, metrics, test_cases)
        
        # Process and format results
        formatted_results = self._format_results(results, test_cases)
        
        # Save results if output file specified
        if output_file:
            self._save_results(formatted_results, output_file)
        
        # Print results if verbose
        if verbose:
            self._print_results(formatted_results)
        
        return formatted_results
    
    async def _run_evaluation_with_metrics(
        self,
        dataset: EvaluationDataset,
        metrics: List[Any],
        test_cases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run evaluation with custom metrics.
        
        Args:
            dataset: EvaluationDataset to evaluate
            metrics: List of evaluation metrics
            test_cases: Original test cases for context
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, golden_data in enumerate(dataset.goldens):
            logger.info(f"Evaluating test case {i+1}/{len(dataset.goldens)}")
            
            # Get agent response
            try:
                agent_response = await self.agent_wrapper.get_response(
                    golden_data.input,
                    context=golden_data.context
                )
                
                # Create LLMTestCase for evaluation (metrics still expect this format)
                test_case_for_metrics = LLMTestCase(
                    input=golden_data.input,
                    expected_output=golden_data.expected_output,
                    actual_output=agent_response,
                    context=golden_data.context
                )
                
                # Evaluate with each metric
                metric_results = {}
                for metric in metrics:
                    metric_result = await metric.a_measure(test_case_for_metrics)
                    metric_results[metric.__class__.__name__] = {
                        'score': metric_result.score,
                        'success': metric_result.success,
                        'reason': metric_result.reason,
                        'strict_mode': metric_result.strict_mode
                    }
                
                results.append({
                    'test_case_index': i,
                    'input': golden_data.input,
                    'expected_output': golden_data.expected_output,
                    'actual_output': agent_response,
                    'original_test_case': test_cases[i],
                    'metric_results': metric_results
                })
                
            except Exception as e:
                logger.error(f"Error evaluating test case {i}: {e}")
                results.append({
                    'test_case_index': i,
                    'input': golden_data.input,
                    'error': str(e),
                    'original_test_case': test_cases[i]
                })
        
        return results
    
    def _format_results(
        self,
        results: List[Dict[str, Any]],
        test_cases: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Format evaluation results for output."""
        total_cases = len(results)
        successful_cases = sum(1 for r in results if 'error' not in r)
        
        # Calculate metric averages
        metric_averages = {}
        metric_names = []
        
        if successful_cases > 0:
            # Get metric names from first successful result
            for result in results:
                if 'metric_results' in result:
                    metric_names = list(result['metric_results'].keys())
                    break
            
            # Calculate averages for each metric
            for metric_name in metric_names:
                scores = [
                    r['metric_results'][metric_name]['score']
                    for r in results
                    if 'metric_results' in r and metric_name in r['metric_results']
                ]
                if scores:
                    metric_averages[metric_name] = {
                        'average_score': sum(scores) / len(scores),
                        'success_rate': sum(1 for s in scores if s >= 0.7) / len(scores)
                    }
        
        # Categorize results
        category_results = {}
        for result in results:
            if 'original_test_case' in result:
                category = result['original_test_case']['category']
                if category not in category_results:
                    category_results[category] = []
                category_results[category].append(result)
        
        return {
            'summary': {
                'total_test_cases': total_cases,
                'successful_evaluations': successful_cases,
                'failed_evaluations': total_cases - successful_cases,
                'success_rate': successful_cases / total_cases if total_cases > 0 else 0
            },
            'metric_averages': metric_averages,
            'category_results': category_results,
            'detailed_results': results,
            'configuration': {
                'model_id': self.model_id,
                'tool_groups': self.tool_groups,
                'stack_url': self.stack_url
            }
        }
    
    def _save_results(self, results: Dict[str, Any], output_file: str):
        """Save results to JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            logger.info(f"Results saved to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _print_results(self, results: Dict[str, Any]):
        """Print formatted results to console."""
        print("\n" + "="*60)
        print("LLAMA STACK AGENT EVALUATION RESULTS")
        print("="*60)
        
        # Summary
        summary = results['summary']
        print(f"\nSUMMARY:")
        print(f"  Total test cases: {summary['total_test_cases']}")
        print(f"  Successful evaluations: {summary['successful_evaluations']}")
        print(f"  Failed evaluations: {summary['failed_evaluations']}")
        print(f"  Overall success rate: {summary['success_rate']:.2%}")
        
        # Metric averages
        if results['metric_averages']:
            print(f"\nMETRIC AVERAGES:")
            for metric_name, metric_data in results['metric_averages'].items():
                print(f"  {metric_name}:")
                print(f"    Average score: {metric_data['average_score']:.3f}")
                print(f"    Success rate: {metric_data['success_rate']:.2%}")
        
        # Category breakdown
        if results['category_results']:
            print(f"\nCATEGORY BREAKDOWN:")
            for category, category_results in results['category_results'].items():
                successful = sum(1 for r in category_results if 'error' not in r)
                total = len(category_results)
                print(f"  {category}: {successful}/{total} ({successful/total:.2%})")
        
        print("\n" + "="*60)
