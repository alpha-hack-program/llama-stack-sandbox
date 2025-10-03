"""
Custom evaluation metrics for Llama Stack agent evaluation using DeepEval framework.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
from deepeval.scorer import Scorer
from deepeval.models import DeepEvalBaseLLM
# from deepeval.utils import trimAndLoadJson  # Not needed

logger = logging.getLogger(__name__)


class ToolSelectionMetric(BaseMetric):
    """
    Metric to evaluate if the agent selected the correct tool for the task.
    """
    
    def __init__(
        self,
        agent_wrapper,
        threshold: float = 1.0,
        model: Optional[DeepEvalBaseLLM] = None,
        include_reason: bool = True
    ):
        """
        Initialize the tool selection metric.
        
        Args:
            agent_wrapper: LlamaStackAgentWrapper instance
            threshold: Score threshold for success (default: 1.0 for exact match)
            model: Optional model for LLM-based evaluation
            include_reason: Whether to include reasoning in the result
        """
        self.agent_wrapper = agent_wrapper
        self.threshold = threshold
        self.model = model
        self.include_reason = include_reason
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure tool selection accuracy."""
        return self._evaluate_tool_selection(test_case).score
    
    async def a_measure(self, test_case: LLMTestCase):
        """Async version of measure."""
        return self._evaluate_tool_selection(test_case)
    
    def _evaluate_tool_selection(self, test_case: LLMTestCase):
        """
        Evaluate tool selection accuracy.
        
        Args:
            test_case: LLMTestCase containing input and expected output
            
        Returns:
            Metric result with score, success status, and reason
        """
        # Extract expected tool from context
        expected_tool = None
        for context_item in test_case.context or []:
            if "Expected tool:" in context_item:
                expected_tool = context_item.split("Expected tool: ")[1].strip()
                break
        
        if not expected_tool:
            return self._create_metric_result(0.0, "Expected tool not found in context")
        
        # First try to get tool from execution logs (more reliable)
        detected_tool = self._extract_tool_from_execution_logs()
        
        # Fallback to extracting from response text if no execution logs found
        if not detected_tool:
            actual_output = test_case.actual_output or ""
            detected_tool = self._extract_tool_from_response(actual_output)
        
        # Calculate score
        if detected_tool and detected_tool.lower() == expected_tool.lower():
            score = 1.0
            success = True
            reason = f"Correctly selected tool: {expected_tool}"
        elif detected_tool:
            score = 0.0
            success = False
            reason = f"Incorrect tool selected. Expected: {expected_tool}, Got: {detected_tool}"
        else:
            score = 0.0
            success = False
            reason = f"No tool detected in response. Expected: {expected_tool}"
        
        return self._create_metric_result(score, reason, success)
    
    def _extract_tool_from_execution_logs(self) -> Optional[str]:
        """Extract tool name from captured execution logs (current session only)."""
        if not self.agent_wrapper or not hasattr(self.agent_wrapper, 'session_cache'):
            return None
        
        tools = ["calc_penalty", "calc_tax", "check_voting", "distribute_waterfall", "check_housing_grant"]
        
        # Get the most recent session (current test case's session)
        if not self.agent_wrapper.session_cache:
            return None
            
        # Get the most recently created session ID (last in insertion order)
        current_session_id = list(self.agent_wrapper.session_cache.keys())[-1]
        session_data = self.agent_wrapper.session_cache[current_session_id]
        
        found_tools = []
        
        # Only check the CURRENT session (current test case)
        turns = session_data.get('turns', [])
        for turn_idx, turn in enumerate(turns):
            # Check tool executions
            tool_executions = turn.get('tool_executions', [])
            for tool_exec in tool_executions:
                content = tool_exec.get('content', '')
                # Handle old format: Tool:calc_penalty Args:...
                if 'Tool:' in content:
                    for tool in tools:
                        if f'Tool:{tool}' in content:
                            found_tools.append((current_session_id, turn_idx, tool))
                # Handle new format: call_id='...' tool_name='check_housing_grant' arguments=...
                elif 'tool_name=' in content:
                    for tool in tools:
                        if f"tool_name='{tool}'" in content or f'tool_name="{tool}"' in content:
                            found_tools.append((current_session_id, turn_idx, tool))
            
            # Also check execution logs
            execution_logs = turn.get('execution_logs', [])
            for log in execution_logs:
                # Handle old format: tool_execution> Tool:calc_penalty Args:...
                if 'tool_execution>' in log and 'Tool:' in log:
                    for tool in tools:
                        if f'Tool:{tool}' in log:
                            found_tools.append((current_session_id, turn_idx, tool))
                # Handle new format: call_id='...' tool_name='check_housing_grant' arguments=...
                elif 'tool_name=' in log:
                    for tool in tools:
                        if f"tool_name='{tool}'" in log or f'tool_name="{tool}"' in log:
                            found_tools.append((current_session_id, turn_idx, tool))
        
        # Return the MOST RECENT tool from the current session only
        if found_tools:
            return found_tools[-1][2]  # Return the tool name from the last execution
        
        return None
    
    def _extract_tool_from_response(self, response: str) -> Optional[str]:
        """Extract tool name from agent response."""
        tools = ["calc_penalty", "calc_tax", "check_voting", "distribute_waterfall", "check_housing_grant"]
        
        response_lower = response.lower()
        for tool in tools:
            if tool in response_lower:
                return tool
        
        return None
    
    def _create_metric_result(self, score: float, reason: str, success: Optional[bool] = None):
        """Create metric result object."""
        if success is None:
            success = score >= self.threshold
        
        # DeepEval metric result structure
        class MetricResult:
            def __init__(self, score, success, reason, strict_mode=False):
                self.score = score
                self.success = success
                self.reason = reason
                self.strict_mode = strict_mode
        
        return MetricResult(score, success, reason)
    
    def is_successful(self) -> bool:
        """Check if the metric evaluation was successful."""
        return True
    
    @property
    def __name__(self):
        return "Tool Selection"


class ParameterAccuracyMetric(BaseMetric):
    """
    Metric to evaluate the accuracy of parameters extracted/used by the agent.
    """
    
    def __init__(
        self,
        agent_wrapper,
        threshold: float = 0.8,
        model: Optional[DeepEvalBaseLLM] = None,
        include_reason: bool = True
    ):
        self.agent_wrapper = agent_wrapper
        self.threshold = threshold
        self.model = model
        self.include_reason = include_reason
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure parameter accuracy."""
        return self._evaluate_parameters(test_case).score
    
    async def a_measure(self, test_case: LLMTestCase):
        """Async version of measure."""
        return self._evaluate_parameters(test_case)
    
    def _evaluate_parameters(self, test_case: LLMTestCase):
        """
        Evaluate parameter extraction and usage accuracy.
        
        Args:
            test_case: LLMTestCase containing input and expected output
            
        Returns:
            Metric result with score, success status, and reason
        """
        # Extract expected parameters from context
        expected_params = {}
        for context_item in test_case.context or []:
            if "Expected parameters:" in context_item:
                param_str = context_item.split("Expected parameters: ")[1].strip()
                try:
                    expected_params = json.loads(param_str)
                except json.JSONDecodeError:
                    pass
                break
        
        if not expected_params:
            return self._create_metric_result(0.0, "Expected parameters not found in context")
        
        # Extract parameters from execution logs first (more reliable), then fallback to response  
        # Try structured response data first (from non-streaming API)
        actual_params = self._extract_parameters_from_structured_response()
        
        # Fallback to execution logs (for streaming API)
        if not actual_params:
            actual_params = self._extract_parameters_from_execution_logs()
            
        # Final fallback to response text parsing
        if not actual_params:
            actual_params = self._extract_parameters_from_response(test_case.actual_output or "")
        
        # Calculate accuracy
        score, reason = self._calculate_parameter_accuracy(expected_params, actual_params)
        
        return self._create_metric_result(score, reason)
    
    def _extract_parameters_from_structured_response(self) -> Dict[str, Any]:
        """Extract parameters from structured response data (non-streaming API)."""
        if not self.agent_wrapper or not hasattr(self.agent_wrapper, 'session_cache'):
            return {}
        
        # Get the most recent session (current test case's session)
        if not self.agent_wrapper.session_cache:
            return {}
            
        # Get the most recently created session ID (last in insertion order)
        current_session_id = list(self.agent_wrapper.session_cache.keys())[-1]
        session_data = self.agent_wrapper.session_cache[current_session_id]
        
        # Check the CURRENT session (current test case)
        turns = session_data.get('turns', [])
        for turn in turns:
            # Try to extract from structured response data
            structured_response = turn.get('structured_response', {})
            if structured_response:
                steps = structured_response.get('steps', [])
                for step in steps:
                    # Check if this step has tool_calls
                    if hasattr(step, 'tool_calls') and step.tool_calls:
                        for tool_call in step.tool_calls:
                            if hasattr(tool_call, 'arguments') and tool_call.arguments:
                                # Found tool call with arguments - return the parameters
                                return tool_call.arguments
        
        return {}
    
    def _extract_parameters_from_execution_logs(self) -> Dict[str, Any]:
        """Extract parameters from captured execution logs (current session only)."""
        if not self.agent_wrapper or not hasattr(self.agent_wrapper, 'session_cache'):
            return {}
        
        all_parameters = []
        
        # Get the most recent session (current test case's session)
        if not self.agent_wrapper.session_cache:
            return {}
            
        # Get the most recently created session ID (last in insertion order)
        current_session_id = list(self.agent_wrapper.session_cache.keys())[-1]
        session_data = self.agent_wrapper.session_cache[current_session_id]
        
        # Only check the CURRENT session (current test case)
        turns = session_data.get('turns', [])
        for turn_idx, turn in enumerate(turns):
            # Check tool executions
            tool_executions = turn.get('tool_executions', [])
            for tool_exec in tool_executions:
                content = tool_exec.get('content', '')
                # Handle old format: Args:{'days_late': '15'}
                if 'Args:' in content:
                    try:
                        args_start = content.find('Args:')
                        if args_start != -1:
                            args_str = content[args_start + 5:].strip()
                            # Handle both string and dict representations
                            if args_str.startswith('{') and args_str.endswith('}'):
                                # Try to parse as dict - replace single quotes with double quotes for JSON
                                json_str = args_str.replace("'", '"')
                                # Convert Python booleans to JSON booleans
                                json_str = json_str.replace("False", "false").replace("True", "true")
                                args_dict = json.loads(json_str)
                                if isinstance(args_dict, dict):
                                    parameters = {}
                                    # Convert string values to appropriate types
                                    for key, value in args_dict.items():
                                        if isinstance(value, str) and value.isdigit():
                                            parameters[key] = int(value)
                                        elif isinstance(value, str) and value.lower() in ['true', 'false']:
                                            parameters[key] = value.lower() == 'true'
                                        else:
                                            parameters[key] = value
                                    all_parameters.append((current_session_id, turn_idx, parameters))
                    except Exception:
                        # If parsing fails, continue to next execution
                        continue
                
                # Handle new format: arguments='{"ami": 55000, "household_size": 2, ...}'
                elif 'arguments=' in content and 'tool_name=' in content:
                    try:
                        # Extract arguments from new format  
                        args_start = content.find('arguments=')
                        if args_start != -1:
                            # Find the start of the JSON (either single or double quote)
                            args_section = content[args_start + 10:]  # Skip 'arguments='
                            
                            # Handle both quoted formats  
                            if args_section.startswith("'") or args_section.startswith('"'):
                                quote_char = args_section[0]
                                
                                # Special handling for double-quoted JSON with unescaped quotes
                                if quote_char == '"' and '{"' in args_section:
                                    # Find the JSON block - look for the opening brace and try to find the matching closing brace
                                    json_start = args_section.find('{')
                                    if json_start > 0:
                                        # Count braces to find the end of JSON
                                        brace_count = 0
                                        json_end = json_start
                                        while json_end < len(args_section):
                                            if args_section[json_end] == '{':
                                                brace_count += 1
                                            elif args_section[json_end] == '}':
                                                brace_count -= 1
                                                if brace_count == 0:
                                                    json_end += 1
                                                    break
                                            json_end += 1
                                        
                                        if brace_count == 0:  # Found matching closing brace
                                            args_str = args_section[json_start:json_end]
                                        else:
                                            args_str = args_section[json_start:]  # Take what we have
                                    else:
                                        args_str = ""
                                else:
                                    # Standard quote handling
                                    json_end = 1
                                    while json_end < len(args_section):
                                        if args_section[json_end] == quote_char:
                                            # Check if this quote is escaped
                                            if json_end == 1 or args_section[json_end-1] != '\\':
                                                break
                                        json_end += 1
                                    
                                    if json_end < len(args_section):
                                        args_str = args_section[1:json_end]  # Extract the JSON content
                                    else:
                                        args_str = args_section[1:]  # Take what we have
                                
                                if args_str and args_str.startswith('{'):
                                    # Try to parse as JSON, handling incomplete JSON gracefully
                                    try:
                                        args_dict = json.loads(args_str)
                                        if isinstance(args_dict, dict):
                                            parameters = {}
                                            for key, value in args_dict.items():
                                                if isinstance(value, str) and value.isdigit():
                                                    parameters[key] = int(value)
                                                elif isinstance(value, str) and value.lower() in ['true', 'false']:
                                                    parameters[key] = value.lower() == 'true'
                                                else:
                                                    parameters[key] = value
                                            all_parameters.append((current_session_id, turn_idx, parameters))
                                    except json.JSONDecodeError:
                                        # Handle incomplete/malformed JSON - extract with regex
                                        if '{' in args_str:
                                            parameters = {}
                                            # Look for key-value pairs manually with better regex
                                            import re
                                            # Match both quoted and unquoted values
                                            kv_pattern = r'"([^"]+)":\s*((?:"[^"]*")|(?:\'[^\']*\')|(?:\d+(?:\.\d+)?)|(?:true|false|null))'
                                            matches = re.findall(kv_pattern, args_str)
                                            for key, value in matches:
                                                # Clean up the value
                                                value = value.strip().strip('"\'')
                                                if value.isdigit():
                                                    parameters[key] = int(value)
                                                elif value.replace('.', '').isdigit():
                                                    parameters[key] = float(value)
                                                elif value.lower() in ['true', 'false']:
                                                    parameters[key] = value.lower() == 'true'
                                                elif value.lower() == 'null':
                                                    parameters[key] = None
                                                else:
                                                    parameters[key] = value
                                            if parameters:
                                                all_parameters.append((current_session_id, turn_idx, parameters))
                    except Exception:
                        # If all parsing fails, continue
                        continue
                
                # Also check execution logs
                execution_logs = turn.get('execution_logs', [])
                for log in execution_logs:
                    # Handle old format: tool_execution> Tool:calc_penalty Args:{'days_late': '15'}
                    if 'tool_execution>' in log and 'Args:' in log:
                        try:
                            args_start = log.find('Args:')
                            if args_start != -1:
                                args_str = log[args_start + 5:].strip()
                                if args_str.startswith('{') and args_str.endswith('}'):
                                    json_str = args_str.replace("'", '"')
                                    # Convert Python booleans to JSON booleans
                                    json_str = json_str.replace("False", "false").replace("True", "true")
                                    args_dict = json.loads(json_str)
                                    if isinstance(args_dict, dict):
                                        parameters = {}
                                        for key, value in args_dict.items():
                                            if isinstance(value, str) and value.isdigit():
                                                parameters[key] = int(value)
                                            elif isinstance(value, str) and value.lower() in ['true', 'false']:
                                                parameters[key] = value.lower() == 'true'
                                            else:
                                                parameters[key] = value
                                        all_parameters.append((current_session_id, turn_idx, parameters))
                        except Exception:
                            continue
                    
                    # Handle new format: call_id='...' tool_name='check_housing_grant' arguments='{"ami": 550, ...}'
                    elif 'arguments=' in log and 'tool_name=' in log:
                        try:
                            # Extract arguments from new format
                            args_start = log.find('arguments=')
                            if args_start != -1:
                                # Find the start of the JSON (either single or double quote)
                                args_section = log[args_start + 10:]  # Skip 'arguments='
                                
                                # Handle both quoted formats
                                if args_section.startswith("'") or args_section.startswith('"'):
                                    quote_char = args_section[0]
                                    # Find the end of the quoted JSON, handling potential escaped quotes
                                # Find the end of the quoted JSON, handling potential escaped quotes
                                json_end = 1
                                while json_end < len(args_section):
                                    if args_section[json_end] == quote_char:
                                        # Check if this quote is escaped
                                        if json_end == 1 or args_section[json_end-1] != '\\':
                                            break
                                    json_end += 1
                                
                                if json_end < len(args_section):
                                    args_str = args_section[1:json_end]  # Extract the JSON content
                                    if args_str and args_str.startswith('{'):
                                        # Try to parse as JSON
                                        try:
                                            args_dict = json.loads(args_str)
                                            if isinstance(args_dict, dict):
                                                parameters = {}
                                                for key, value in args_dict.items():
                                                    if isinstance(value, str) and value.isdigit():
                                                        parameters[key] = int(value)
                                                    elif isinstance(value, str) and value.lower() in ['true', 'false']:
                                                        parameters[key] = value.lower() == 'true'
                                                    else:
                                                        parameters[key] = value
                                                all_parameters.append((current_session_id, turn_idx, parameters))
                                        except Exception:
                                            continue
                        except Exception as e:
                            # If JSON parsing fails, continue
                            continue
        
        # Return the MOST RECENT parameters (last in the list)
        if all_parameters:
            return all_parameters[-1][2]  # Return the parameters from the last execution
        
        return {}
    
    def _extract_parameters_from_response(self, response: str) -> Dict[str, Any]:
        """Extract parameters from agent response."""
        parameters = {}
        
        # Look for common parameter patterns
        patterns = {
            r'days_late[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'days_late',
            r'income[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'income',
            r'eligible_voters[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'eligible_voters',
            r'turnout[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'turnout',
            r'yes_votes[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'yes_votes',
            r'cash_available[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'cash_available',
            r'senior_debt[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'senior_debt',
            r'junior_debt[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'junior_debt',
            r'ami[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'ami',
            r'household_size[\"\'\\s]*[:=][\"\'\\s]*(\d+)': 'household_size',
            r'has_other_subsidy[\"\'\\s]*[:=][\"\'\\s]*(true|false)': 'has_other_subsidy',
            r'proposal_type[\"\'\\s]*[:=][\"\'\\s]*[\"\'](\\w+)[\"\']*': 'proposal_type'
        }
        
        for pattern, param_name in patterns.items():
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                value = match.group(1)
                if param_name == 'has_other_subsidy':
                    parameters[param_name] = value.lower() == 'true'
                elif param_name == 'proposal_type':
                    parameters[param_name] = value
                else:
                    try:
                        parameters[param_name] = int(value)
                    except ValueError:
                        parameters[param_name] = value
        
        # Also try to extract from JSON blocks
        json_matches = re.findall(r'\{[^}]*\}', response)
        for json_match in json_matches:
            try:
                parsed = json.loads(json_match)
                if isinstance(parsed, dict):
                    parameters.update(parsed)
            except:
                continue
        
        return parameters
    
    def _calculate_parameter_accuracy(
        self,
        expected_params: Dict[str, Any],
        actual_params: Dict[str, Any]
    ) -> tuple[float, str]:
        """Calculate parameter accuracy score."""
        if not expected_params:
            return 1.0, "No parameters expected"
        
        total_params = len(expected_params)
        correct_params = 0
        missing_params = []
        incorrect_params = []
        
        for key, expected_value in expected_params.items():
            if key in actual_params:
                actual_value = actual_params[key]
                
                # Handle type mismatches (e.g., int vs string)
                values_match = False
                
                # Direct comparison first
                if actual_value == expected_value:
                    values_match = True
                else:
                    # Try type conversion comparisons
                    try:
                        # Try converting both to strings
                        if str(actual_value) == str(expected_value):
                            values_match = True
                        # Try converting both to integers if they're numeric
                        elif (str(actual_value).replace('.', '').replace('-', '').isdigit() and 
                              str(expected_value).replace('.', '').replace('-', '').isdigit()):
                            if int(float(actual_value)) == int(float(expected_value)):
                                values_match = True
                        # Try boolean comparisons with proper type handling
                        elif self._is_boolean_like(actual_value) or self._is_boolean_like(expected_value):
                            # Convert both to canonical boolean values for comparison
                            actual_bool = self._to_boolean(actual_value)
                            expected_bool = self._to_boolean(expected_value)
                            if actual_bool == expected_bool:
                                values_match = True
                    except (ValueError, TypeError):
                        # If conversion fails, values don't match
                        values_match = False
                
                if values_match:
                    correct_params += 1
                else:
                    incorrect_params.append(f"{key}: expected {expected_value}, got {actual_value}")
            else:
                missing_params.append(key)
        
        score = correct_params / total_params if total_params > 0 else 0.0
        
        reason_parts = []
        if correct_params > 0:
            reason_parts.append(f"{correct_params}/{total_params} parameters correct")
        if missing_params:
            reason_parts.append(f"Missing: {', '.join(missing_params)}")
        if incorrect_params:
            reason_parts.append(f"Incorrect: {', '.join(incorrect_params)}")
        
        reason = "; ".join(reason_parts) if reason_parts else "All parameters correct"
        
        return score, reason
    
    def _is_boolean_like(self, value) -> bool:
        """Check if a value represents a boolean."""
        if isinstance(value, bool):
            return True
        if isinstance(value, str):
            return value.lower() in ['true', 'false', 'yes', 'no', '1', '0']
        if isinstance(value, (int, float)):
            return value in [0, 1, 0.0, 1.0]
        return False
    
    def _to_boolean(self, value) -> bool:
        """Convert a value to boolean with proper handling of various formats."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ['true', 'yes', '1']
        if isinstance(value, (int, float)):
            return bool(value) and value != 0
        return bool(value)
    
    def _create_metric_result(self, score: float, reason: str, success: Optional[bool] = None):
        """Create metric result object."""
        if success is None:
            success = score >= self.threshold
        
        class MetricResult:
            def __init__(self, score, success, reason, strict_mode=False):
                self.score = score
                self.success = success
                self.reason = reason
                self.strict_mode = strict_mode
        
        return MetricResult(score, success, reason)
    
    def is_successful(self) -> bool:
        return True
    
    @property
    def __name__(self):
        return "Parameter Accuracy"


class ResponseAccuracyMetric(BaseMetric):
    """
    Metric to evaluate the accuracy of the agent's final response.
    """
    
    def __init__(
        self,
        agent_wrapper,
        threshold: float = 0.7,
        model: Optional[DeepEvalBaseLLM] = None,
        include_reason: bool = True,
        custom_status_mapping: Optional[Dict[str, str]] = None
    ):
        self.agent_wrapper = agent_wrapper
        self.threshold = threshold
        self.model = model
        self.include_reason = include_reason
        self.custom_status_mapping = custom_status_mapping or {}
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure response accuracy."""
        return self._evaluate_response(test_case).score
    
    async def a_measure(self, test_case: LLMTestCase):
        """Async version of measure."""
        return self._evaluate_response(test_case)
    
    def _evaluate_response(self, test_case: LLMTestCase):
        """
        Evaluate response accuracy against expected output.
        
        Args:
            test_case: LLMTestCase containing expected and actual outputs
            
        Returns:
            Metric result with score, success status, and reason
        """
        expected_output = test_case.expected_output or ""
        actual_output = test_case.actual_output or ""
        
        # Extract key information from both outputs
        expected_info = self._extract_key_information(expected_output)
        actual_info = self._extract_key_information(actual_output)
        
        # Calculate similarity score
        score, reason = self._calculate_response_similarity(expected_info, actual_info)
        
        return self._create_metric_result(score, reason)
    
    def _extract_key_information(self, text: str) -> Dict[str, Any]:
        """Extract key information from response text."""
        info = {
            'numbers': [],
            'percentages': [],
            'amounts': [],
            'warnings': [],
            'status': None,
            'calculations': []
        }
        
        # Extract numbers
        numbers = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', text)
        info['numbers'] = [float(n.replace(',', '')) for n in numbers]
        
        # Extract percentages
        percentages = re.findall(r'(\d+(?:\.\d+)?)%', text)
        info['percentages'] = [float(p) for p in percentages]
        
        # Extract dollar amounts
        amounts = re.findall(r'\$([\d,]+(?:\.\d+)?)', text)
        info['amounts'] = [float(a.replace(',', '')) for a in amounts]
        
        # Extract warnings - first try structured tool data, then text
        tool_warnings = self._extract_warnings_from_tool_data()
        if tool_warnings is not None:
            # Use structured warnings from tool responses
            info['warnings'] = tool_warnings
        else:
            # Fall back to text-based warning detection
            if 'warning' in text.lower():
                info['warnings'] = re.findall(r'warning[^.]*\.', text, re.IGNORECASE)
        
        # Extract status (PASSED, FAILED, ELIGIBLE, NOT ELIGIBLE, etc.)
        # Enhanced patterns to catch semantic variations
        status_patterns = [
            # Exact matches (highest priority)
            r'\b(PASSED|FAILED|ELIGIBLE|NOT ELIGIBLE)\b',
            r'\b(passed|failed)\b',
            # Verb forms and variations
            r'\b(passes|pass)\b',
            r'\b(fails|fail)\b', 
            r'\b(approved?|approve)\b',
            r'\b(rejected?|reject)\b',
            r'\b(valid|invalid)\b',
            r'\b(successful|success)\b',
            r'\b(unsuccessful|unsuccessful)\b'
        ]
        
        # Mapping semantic variations to standard status
        default_mapping = {
            'PASSES': 'PASSED', 'PASS': 'PASSED',
            'FAILS': 'FAILED', 'FAIL': 'FAILED',
            'APPROVED': 'PASSED', 'APPROVE': 'PASSED',
            'REJECTED': 'FAILED', 'REJECT': 'FAILED', 
            'VALID': 'PASSED', 'INVALID': 'FAILED',
            'SUCCESSFUL': 'PASSED', 'SUCCESS': 'PASSED',
            'UNSUCCESSFUL': 'FAILED'
        }
        
        # Merge with custom status mapping if provided
        status_mapping = {**default_mapping, **self.custom_status_mapping}
        
        for pattern in status_patterns:
            status_match = re.search(pattern, text, re.IGNORECASE)
            if status_match:
                raw_status = status_match.group(1).upper()
                info['status'] = status_mapping.get(raw_status, raw_status)
                break
        
        # Extract calculation elements
        calc_patterns = [
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*[×*]\s*(\d+(?:\.\d+)?)%',
            r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*[×*]\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)',
            r'\$?(\d+(?:,\d{3})*(?:\.\d+)?)\s*[+\-]\s*\$?(\d+(?:,\d{3})*(?:\.\d+)?)'
        ]
        
        for pattern in calc_patterns:
            matches = re.findall(pattern, text)
            info['calculations'].extend(matches)
        
        return info
    
    def _extract_warnings_from_tool_data(self) -> Optional[List[str]]:
        """Extract warnings from actual tool response data (structured)."""
        if not self.agent_wrapper or not hasattr(self.agent_wrapper, 'session_cache'):
            return None
        
        # Get the most recent session (current test case's session)
        if not self.agent_wrapper.session_cache:
            return None
            
        # Get the most recently created session ID (last in insertion order)
        current_session_id = list(self.agent_wrapper.session_cache.keys())[-1]
        session_data = self.agent_wrapper.session_cache[current_session_id]
        
        all_warnings = []
        
        # Only check the CURRENT session (current test case)
        turns = session_data.get('turns', [])
        for turn in turns:
            # Check execution logs for tool responses
            execution_logs = turn.get('execution_logs', [])
            for log in execution_logs:
                if 'tool_execution>' in log and 'Response:' in log:
                    # Extract the tool response JSON
                    response_start = log.find('Response:')
                    if response_start != -1:
                        response_section = log[response_start + 9:].strip()
                        # Look for TextContentItem content
                        if 'TextContentItem(text=' in response_section:
                            json_start = response_section.find("'")
                            if json_start != -1:
                                json_end = response_section.rfind("'")
                                if json_end > json_start:
                                    json_str = response_section[json_start + 1:json_end]
                                    try:
                                        # Parse the JSON response
                                        import json
                                        tool_response = json.loads(json_str)
                                        
                                        # Extract warnings from tool response
                                        if 'warnings' in tool_response and tool_response['warnings']:
                                            all_warnings.extend(tool_response['warnings'])
                                        
                                        # Extract additional_requirements that indicate warnings
                                        if 'additional_requirements' in tool_response:
                                            for req in tool_response['additional_requirements']:
                                                if any(indicator in req.lower() for indicator in 
                                                      ['close to threshold', 'verify', 'caution', 'warning', 'alert']):
                                                    all_warnings.append(req)
                                                    
                                    except json.JSONDecodeError:
                                        continue
        
        return all_warnings if all_warnings else []
    
    def _calculate_response_similarity(
        self,
        expected_info: Dict[str, Any],
        actual_info: Dict[str, Any]
    ) -> tuple[float, str]:
        """Calculate similarity between expected and actual response information."""
        scores = []
        reasons = []
        
        # Compare status
        if expected_info.get('status') and actual_info.get('status'):
            if expected_info['status'] == actual_info['status']:
                scores.append(1.0)
                reasons.append("Status matches")
            else:
                scores.append(0.0)
                reasons.append(f"Status mismatch: expected {expected_info['status']}, got {actual_info['status']}")
        elif expected_info.get('status'):
            scores.append(0.0)
            reasons.append(f"Missing status: expected {expected_info['status']}")
        
        # Compare key amounts (most important numbers)
        expected_amounts = expected_info['amounts']
        actual_amounts = actual_info['amounts']
        
        if expected_amounts and actual_amounts:
            # Find the closest matches for the most significant amounts
            main_expected = expected_amounts[0] if expected_amounts else 0
            main_actual = actual_amounts[0] if actual_amounts else 0
            
            if main_expected > 0:
                amount_accuracy = 1.0 - abs(main_expected - main_actual) / main_expected
                amount_accuracy = max(0.0, amount_accuracy)
            else:
                amount_accuracy = 1.0 if main_actual == 0 else 0.0
            
            scores.append(amount_accuracy)
            reasons.append(f"Main amount accuracy: {amount_accuracy:.2f}")
        
        # Compare percentages
        expected_pcts = expected_info['percentages']
        actual_pcts = actual_info['percentages']
        
        if expected_pcts and actual_pcts:
            pct_matches = 0
            for exp_pct in expected_pcts:
                for act_pct in actual_pcts:
                    if abs(exp_pct - act_pct) < 0.1:  # Within 0.1%
                        pct_matches += 1
                        break
            
            pct_score = pct_matches / len(expected_pcts)
            scores.append(pct_score)
            reasons.append(f"Percentage accuracy: {pct_score:.2f}")
        
        # Check for warnings presence
        expected_has_warnings = len(expected_info['warnings']) > 0
        actual_has_warnings = len(actual_info['warnings']) > 0
        
        if expected_has_warnings == actual_has_warnings:
            scores.append(1.0)
            reasons.append("Warning presence matches")
        else:
            scores.append(0.5)
            reasons.append("Warning presence mismatch")
        
        # Calculate overall score
        overall_score = sum(scores) / len(scores) if scores else 0.0
        reason = "; ".join(reasons) if reasons else "No comparable elements found"
        
        return overall_score, reason
    
    def _create_metric_result(self, score: float, reason: str, success: Optional[bool] = None):
        """Create metric result object."""
        if success is None:
            success = score >= self.threshold
        
        class MetricResult:
            def __init__(self, score, success, reason, strict_mode=False):
                self.score = score
                self.success = success
                self.reason = reason
                self.strict_mode = strict_mode
        
        return MetricResult(score, success, reason)
    
    def is_successful(self) -> bool:
        return True
    
    @property
    def __name__(self):
        return "Response Accuracy"


class ComprehensiveEvaluationMetric(BaseMetric):
    """
    Comprehensive metric that combines tool selection, parameter accuracy, and response quality.
    """
    
    def __init__(
        self,
        agent_wrapper,
        threshold: float = 0.7,
        tool_weight: float = 0.3,
        param_weight: float = 0.3,
        response_weight: float = 0.4,
        model: Optional[DeepEvalBaseLLM] = None,
        include_reason: bool = True
    ):
        self.agent_wrapper = agent_wrapper
        self.threshold = threshold
        self.tool_weight = tool_weight
        self.param_weight = param_weight
        self.response_weight = response_weight
        self.model = model
        self.include_reason = include_reason
        
        # Initialize sub-metrics
        self.tool_metric = ToolSelectionMetric(agent_wrapper, model=model)
        self.param_metric = ParameterAccuracyMetric(agent_wrapper, model=model)
        self.response_metric = ResponseAccuracyMetric(agent_wrapper, model=model)
    
    def measure(self, test_case: LLMTestCase) -> float:
        """Measure comprehensive evaluation score."""
        return self._evaluate_comprehensive(test_case).score
    
    async def a_measure(self, test_case: LLMTestCase):
        """Async version of measure."""
        return self._evaluate_comprehensive(test_case)
    
    def _evaluate_comprehensive(self, test_case: LLMTestCase):
        """
        Perform comprehensive evaluation combining multiple metrics.
        
        Args:
            test_case: LLMTestCase containing input and expected output
            
        Returns:
            Metric result with weighted score, success status, and detailed reason
        """
        # Get scores from individual metrics
        tool_result = self.tool_metric._evaluate_tool_selection(test_case)
        param_result = self.param_metric._evaluate_parameters(test_case)
        response_result = self.response_metric._evaluate_response(test_case)
        
        # Calculate weighted score
        weighted_score = (
            tool_result.score * self.tool_weight +
            param_result.score * self.param_weight +
            response_result.score * self.response_weight
        )
        
        # Compile detailed reason
        reason_parts = [
            f"Tool Selection ({self.tool_weight:.1%}): {tool_result.score:.2f} - {tool_result.reason}",
            f"Parameter Accuracy ({self.param_weight:.1%}): {param_result.score:.2f} - {param_result.reason}",
            f"Response Accuracy ({self.response_weight:.1%}): {response_result.score:.2f} - {response_result.reason}",
            f"Weighted Score: {weighted_score:.3f}"
        ]
        
        comprehensive_reason = " | ".join(reason_parts)
        
        return self._create_metric_result(weighted_score, comprehensive_reason)
    
    def _create_metric_result(self, score: float, reason: str, success: Optional[bool] = None):
        """Create metric result object."""
        if success is None:
            success = score >= self.threshold
        
        class MetricResult:
            def __init__(self, score, success, reason, strict_mode=False):
                self.score = score
                self.success = success
                self.reason = reason
                self.strict_mode = strict_mode
        
        return MetricResult(score, success, reason)
    
    def is_successful(self) -> bool:
        return True
    
    @property
    def __name__(self):
        return "Comprehensive Evaluation"
