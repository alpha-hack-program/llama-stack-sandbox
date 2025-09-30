"""
Wrapper for Llama Stack client to provide agent functionality for evaluation.
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.agent import Agent
from llama_stack_client.lib.agents.event_logger import EventLogger as AgentEventLogger

logger = logging.getLogger(__name__)


class LlamaStackAgentWrapper:
    """
    Wrapper class for Llama Stack client that provides agent functionality.
    Handles session management, tool calling, and response formatting.
    """
    
    def __init__(
        self,
        client: LlamaStackClient,
        model_id: str,
        tool_groups: List[str],
        system_prompt: Optional[str] = None
    ):
        """
        Initialize the agent wrapper.
        
        Args:
            client: LlamaStackClient instance
            model_id: Model identifier to use
            tool_groups: List of tool groups to enable
            system_prompt: Optional system prompt for the agent
        """
        self.client = client
        self.model_id = model_id
        self.tool_groups = tool_groups
        self.system_prompt = system_prompt or self._get_default_system_prompt()
        self.agent = None
        self.session_cache = {}
        
    def _get_default_system_prompt(self) -> str:
        """Get default system prompt for the agent."""
        return """You are a helpful financial and administrative assistant with access to specialized calculation tools. 

IMPORTANT: You MUST use the available tools to perform calculations. Do not do manual calculations.

Available tools:
- calc_penalty: Calculate late payment penalties with interest and caps
- calc_tax: Progressive tax calculations with surcharge
- check_voting: Validate voting results and quorum requirements  
- distribute_waterfall: Calculate financial waterfall distributions
- check_housing_grant: Check housing assistance eligibility

When answering questions:
1. ALWAYS use the appropriate tool for calculations
2. Extract the required parameters from the user's question
3. Call the tool with the correct parameters
4. Present the tool's results clearly
5. Include any warnings or special conditions from the tool

Do not perform manual calculations - always use the tools provided."""
    
    async def initialize(self) -> bool:
        """
        Initialize the agent with the Llama Stack system using the Agent class.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Create agent using the Agent class (same as test.py)
            self.agent = Agent(
                self.client,
                model=self.model_id,
                instructions=self.system_prompt,
                enable_session_persistence=False,
                tools=self.tool_groups,  # Pass tool groups directly as strings
                tool_config={"tool_choice": "auto"}
            )
            
            logger.info(f"Agent initialized with model: {self.model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            return False
    
    async def create_session(self, session_name: Optional[str] = None) -> str:
        """
        Create a new session for the agent.
        
        Args:
            session_name: Optional name for the session
            
        Returns:
            Session ID
        """
        try:
            session_name = session_name or f"eval_session_{len(self.session_cache)}"
            session_id = self.agent.create_session(session_name)
            
            self.session_cache[session_id] = {
                "created": True,
                "turns": []
            }
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_response(
        self,
        user_input: str,
        context: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Get response from the agent for a given input.
        
        Args:
            user_input: User question/input
            context: Optional context information
            session_id: Optional session ID to use
            
        Returns:
            Agent response as string
        """
        try:
            # Create session if not provided
            if session_id is None:
                session_id = await self.create_session()
            
            # Prepare messages - use only user message, put context in content
            if context:
                context_str = "\\n".join(context)
                full_content = f"Context: {context_str}\\n\\nUser question: {user_input}"
            else:
                full_content = user_input
            
            messages = [{"role": "user", "content": full_content}]
            
            # Use the Agent class create_turn method (same as test.py)
            response = self.agent.create_turn(
                messages=messages,
                session_id=session_id
            )
            
            # Extract the response content using AgentEventLogger (same as test.py)
            agent_response = ""
            tool_executions = []
            step_logs = []
            
            # Process the response using AgentEventLogger like test.py does
            response_parts = []
            inference_tokens = []
            collecting_inference = False
            
            for log in AgentEventLogger().log(response):
                # Capture all log content
                log_str = str(log)
                step_logs.append(log_str)
                
                # Look for tool execution logs (both formats)
                if "tool_execution>" in log_str:
                    tool_executions.append({
                        'log_type': 'tool_execution',
                        'content': log_str
                    })
                elif "call_id=" in log_str and "tool_name=" in log_str:
                    # Handle incomplete tool calls - add them to tool executions but don't include in final response
                    tool_executions.append({
                        'log_type': 'tool_execution_new_format',
                        'content': log_str
                    })
                    # Don't add these to inference tokens as they are tool calls, not final response
                    continue
                elif "inference>" in log_str:
                    # Start collecting inference tokens
                    collecting_inference = True
                    inference_content = log_str.split("inference>", 1)[-1].strip()
                    if inference_content:
                        # Skip tool call content that got mixed into inference
                        if not ("call_id=" in inference_content and "tool_name=" in inference_content):
                            inference_tokens.append(inference_content)
                elif collecting_inference and log_str.strip():
                    # Continue collecting inference tokens until we hit an empty line or new section
                    if log_str.strip() and not ("tool_execution>" in log_str or "step_complete>" in log_str or "call_id=" in log_str):
                        inference_tokens.append(log_str.strip())
                    else:
                        # Stop collecting when we hit a new section
                        collecting_inference = False
            
            # Combine all inference tokens into a coherent response
            if inference_tokens:
                # Filter out empty tokens and join them properly
                meaningful_tokens = [token for token in inference_tokens if token.strip()]
                
                # Smart joining to handle currency, numbers, and punctuation
                agent_response = ""
                for i, token in enumerate(meaningful_tokens):
                    if i == 0:
                        agent_response = token
                    else:
                        prev_token = meaningful_tokens[i-1]
                        # Don't add space before punctuation
                        if token in ['.', ',', ':', ';', '!', '?', '%']:
                            agent_response += token
                        # Don't add space after currency symbols
                        elif prev_token in ['$', '€', '£', '¥']:
                            agent_response += token
                        # Don't add space between digits and decimal points
                        elif prev_token.isdigit() and token in ['.', ','] and i+1 < len(meaningful_tokens) and meaningful_tokens[i+1].isdigit():
                            agent_response += token
                        # Don't add space between parts of numbers
                        elif prev_token.isdigit() and token.isdigit():
                            agent_response += token
                        # Don't add space before decimal numbers
                        elif prev_token == '.' and token.isdigit():
                            agent_response += token
                        # Add space for normal word boundaries
                        else:
                            agent_response += " " + token
            elif step_logs:
                # If no inference tokens, try to extract from logs
                # Look for the final response content
                for log in reversed(step_logs):
                    if log.strip() and "tool_execution>" not in log and "inference>" not in log:
                        agent_response = log.strip()
                        break
            
            # Log the captured execution details
            if step_logs:
                logger.info("Detailed execution logs captured:")
                for log in step_logs:
                    logger.info(log)
            
            # Ensure we have some response
            if not agent_response.strip():
                logger.warning("No response content captured from streaming")
                agent_response = "Error: No response captured from agent"
            
            # Store turn in cache with detailed execution info
            if session_id in self.session_cache:
                self.session_cache[session_id]["turns"].append({
                    "input": user_input,
                    "output": agent_response,
                    "context": context,
                    "tool_executions": tool_executions,
                    "execution_logs": step_logs
                })
            
            return agent_response
            
        except Exception as e:
            logger.error(f"Failed to get response: {e}")
            return f"Error: {str(e)}"
    
    async def extract_tool_usage(self, response: str) -> Dict[str, Any]:
        """
        Extract tool usage information from agent response.
        
        Args:
            response: Agent response string
            
        Returns:
            Dictionary containing tool usage information
        """
        # This is a simplified extraction - in practice, you might need
        # more sophisticated parsing based on your agent's response format
        tool_usage = {
            "tool_called": None,
            "tool_parameters": {},
            "tool_result": None,
            "raw_response": response
        }
        
        try:
            # Look for common tool patterns in response
            tools = ["calc_penalty", "calc_tax", "check_voting", "distribute_waterfall", "check_housing_grant"]
            
            for tool in tools:
                if tool in response.lower():
                    tool_usage["tool_called"] = tool
                    break
            
            # Try to extract JSON-like parameters if present
            # This is a simplified approach - real implementation might need more robust parsing
            if "{" in response and "}" in response:
                try:
                    # Find JSON-like structures
                    start = response.find("{")
                    end = response.rfind("}") + 1
                    if start < end:
                        potential_json = response[start:end]
                        parsed = json.loads(potential_json)
                        if isinstance(parsed, dict):
                            tool_usage["tool_parameters"] = parsed
                except:
                    pass
            
        except Exception as e:
            logger.error(f"Error extracting tool usage: {e}")
        
        return tool_usage
    
    async def validate_tool_selection(
        self,
        response: str,
        expected_tool: str,
        expected_parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate if the agent selected the correct tool and parameters.
        
        Args:
            response: Agent response
            expected_tool: Expected tool name
            expected_parameters: Expected tool parameters
            
        Returns:
            Validation results dictionary
        """
        tool_usage = await self.extract_tool_usage(response)
        
        validation_result = {
            "tool_selection_correct": False,
            "parameter_accuracy": 0.0,
            "missing_parameters": [],
            "incorrect_parameters": [],
            "tool_usage": tool_usage
        }
        
        # Check tool selection
        if tool_usage["tool_called"] and tool_usage["tool_called"].lower() == expected_tool.lower():
            validation_result["tool_selection_correct"] = True
        
        # Check parameters
        extracted_params = tool_usage["tool_parameters"]
        if expected_parameters and extracted_params:
            correct_params = 0
            total_params = len(expected_parameters)
            
            for key, expected_value in expected_parameters.items():
                if key in extracted_params:
                    if extracted_params[key] == expected_value:
                        correct_params += 1
                    else:
                        validation_result["incorrect_parameters"].append({
                            "parameter": key,
                            "expected": expected_value,
                            "actual": extracted_params[key]
                        })
                else:
                    validation_result["missing_parameters"].append(key)
            
            validation_result["parameter_accuracy"] = correct_params / total_params if total_params > 0 else 0.0
        
        return validation_result
    
    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get history of turns for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of turn dictionaries
        """
        if session_id in self.session_cache:
            return self.session_cache[session_id]["turns"]
        return []
    
    async def cleanup_session(self, session_id: str):
        """
        Clean up a session.
        
        Args:
            session_id: Session to clean up
        """
        try:
            # Remove from cache
            if session_id in self.session_cache:
                del self.session_cache[session_id]
                
            # You might want to call the Llama Stack API to delete the session
            # depending on the API's capabilities
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    async def cleanup_all_sessions(self):
        """Clean up all cached sessions."""
        session_ids = list(self.session_cache.keys())
        for session_id in session_ids:
            await self.cleanup_session(session_id)
