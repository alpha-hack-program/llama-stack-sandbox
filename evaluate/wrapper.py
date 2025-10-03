"""
Wrapper for Llama Stack client to provide agent functionality for evaluation.
"""

import json
import logging
import asyncio
import re
from typing import Dict, List, Any, Optional, Union
from llama_stack_client import LlamaStackClient
from llama_stack_client.lib.agents.agent import Agent

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
  Parameters: {"days_late": number}
  
- calc_tax: Progressive tax calculations with surcharge
  Parameters: {"income": number}
  
- check_voting: Validate voting results and quorum requirements
  Parameters: {"eligible_voters": number, "turnout": number, "yes_votes": number, "proposal_type": string}
  
- distribute_waterfall: Calculate financial waterfall distributions
  Parameters: {"cash_available": number, "senior_debt": number, "junior_debt": number}
  
- check_housing_grant: Check housing assistance eligibility
  Parameters: {"ami": number, "household_size": number, "income": number, "has_other_subsidy": boolean}

CRITICAL TOOL USAGE INSTRUCTIONS:
1. ALWAYS use the appropriate tool for calculations
2. Extract ALL required parameters from the user's question
3. ALWAYS complete the full JSON parameter structure - never truncate or leave incomplete
4. For check_housing_grant, you MUST include all 4 parameters: ami, household_size, income, has_other_subsidy
5. Use correct data types: numbers for numeric values, true/false for booleans
6. Present the tool's results clearly
7. Include any warnings or special conditions from the tool

EXAMPLES:
- For "family of 6 with income 35000, AMI 60000, no other subsidies": 
  Use check_housing_grant with {"ami": 60000, "household_size": 6, "income": 35000, "has_other_subsidy": false}
  
- For "15 days late payment":
  Use calc_penalty with {"days_late": 15}

Remember: Complete ALL parameters in tool calls. Never send incomplete JSON."""
    
    async def initialize(self) -> bool:
        """
        Initialize the agent with the Llama Stack system using the Agent class.
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing agent with model: {self.model_id}, tools: {self.tool_groups}")
            
            # Create agent using the Agent class (same as test.py)
            self.agent = Agent(
                self.client,
                model=self.model_id,
                instructions=self.system_prompt,
                enable_session_persistence=False,
                tools=self.tool_groups,  # Pass tool groups directly as strings
                tool_config={"tool_choice": "auto"}
            )
            
            # Verify agent was created successfully
            if self.agent is None:
                logger.error("Agent creation returned None")
                return False
            
            logger.info(f"Agent initialized successfully with model: {self.model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            logger.error(f"Model: {self.model_id}, Tools: {self.tool_groups}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            self.agent = None
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
            if self.agent is None:
                raise RuntimeError("Agent not initialized. Call initialize() first.")
                
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
            if self.agent is None:
                raise RuntimeError("Agent not initialized. Call initialize() first.")
                
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
            
            # Use non-streaming API with stream=False
            response = self.agent.create_turn(
                session_id=session_id,
                messages=messages,
                stream=False
            )
            
            # Extract response content directly from non-streaming response
            agent_response = ""
            tool_executions = []
            step_logs = []
            
            # Access the structured response data
            input_messages = response.input_messages
            output_message = response.output_message
            steps = response.steps
            
            # Extract the main response content
            if output_message and hasattr(output_message, 'content'):
                agent_response = output_message.content
            
            # Process steps to extract tool executions and detailed information
            for step in steps:
                step_info = {
                    'step_type': getattr(step, 'step_type', 'unknown'),
                    'step_id': getattr(step, 'step_id', ''),
                    'content': str(step)
                }
                step_logs.append(step_info)
                
                # Check if this step contains tool execution information
                if hasattr(step, 'tool_calls') or 'tool_call' in str(step).lower():
                    tool_executions.append({
                        'log_type': 'tool_execution_structured',
                        'step': step_info,
                        'content': str(step)
                    })
            
            # Log the structured response data for debugging
            logger.info(f"Input messages: {input_messages}")
            logger.info(f"Output message content: {agent_response}")
            logger.info(f"Number of steps: {len(steps)}")
            
            # Ensure we have some response
            if not agent_response or not agent_response.strip():
                logger.warning("No response content captured from non-streaming API")
                agent_response = "Error: No response content captured from agent"
            
            # Store turn in cache with structured response data
            if session_id in self.session_cache:
                self.session_cache[session_id]["turns"].append({
                    "input": user_input,
                    "output": agent_response,
                    "context": context,
                    "tool_executions": tool_executions,
                    "execution_logs": step_logs,
                    "structured_response": {
                        "input_messages": input_messages,
                        "output_message": output_message,
                        "steps": steps
                    }
                })
            
            return agent_response
            
        except Exception as e:
            logger.error(f"Failed to get response: {e}")
            return f"Error: {str(e)}"
    
    async def extract_tool_usage(self, response: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract tool usage information from agent response.
        
        Args:
            response: Agent response string
            session_id: Optional session ID to get structured response data
            
        Returns:
            Dictionary containing tool usage information
        """
        tool_usage = {
            "tool_called": None,
            "tool_parameters": {},
            "tool_result": None,
            "raw_response": response,
            "structured_data": None
        }
        
        try:
            # If we have a session ID, try to get structured data first
            if session_id and session_id in self.session_cache:
                turns = self.session_cache[session_id]["turns"]
                if turns:
                    # Get the most recent turn's structured response
                    latest_turn = turns[-1]
                    structured_response = latest_turn.get("structured_response", {})
                    
                    if structured_response:
                        tool_usage["structured_data"] = structured_response
                        steps = structured_response.get("steps", [])
                        
                        # Extract tool information from steps
                        for step in steps:
                            if hasattr(step, 'tool_calls'):
                                for tool_call in step.tool_calls:
                                    tool_usage["tool_called"] = getattr(tool_call, 'tool_name', None)
                                    tool_usage["tool_parameters"] = getattr(tool_call, 'arguments', {})
                                    break
                            
                            # Also check step content for tool information
                            step_str = str(step)
                            if 'tool_name=' in step_str and 'arguments=' in step_str:
                                # Try to extract tool name and arguments from step string
                                import re
                                tool_name_match = re.search(r'tool_name[=:]\\s*["\']?([^"\'\\s,}]+)["\']?', step_str)
                                if tool_name_match:
                                    tool_usage["tool_called"] = tool_name_match.group(1)
                                
                                # Try to extract arguments
                                args_match = re.search(r'arguments[=:]\\s*({[^}]+})', step_str)
                                if args_match:
                                    try:
                                        args_str = args_match.group(1)
                                        # Convert single quotes to double quotes for JSON parsing
                                        args_str = args_str.replace("'", '"')
                                        tool_usage["tool_parameters"] = json.loads(args_str)
                                    except json.JSONDecodeError:
                                        pass
                        
                        # If we found structured tool data, return it
                        if tool_usage["tool_called"]:
                            return tool_usage
            
            # Fallback to the original text-based extraction method
            tools = ["calc_penalty", "calc_tax", "check_voting", "distribute_waterfall", "check_housing_grant"]
            
            for tool in tools:
                if tool in response.lower():
                    tool_usage["tool_called"] = tool
                    break
            
            # Try to extract JSON-like parameters if present
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
    
    def get_structured_response(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the structured response data from the most recent turn in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Structured response data with input_messages, output_message, and steps
        """
        if session_id in self.session_cache:
            turns = self.session_cache[session_id]["turns"]
            if turns:
                latest_turn = turns[-1]
                return latest_turn.get("structured_response")
        return None
    
    def get_response_steps(self, session_id: str) -> List[Any]:
        """
        Get the steps from the most recent response in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of response steps
        """
        structured_response = self.get_structured_response(session_id)
        if structured_response:
            return structured_response.get("steps", [])
        return []
    
    def get_input_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the input messages from the most recent response in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of input messages
        """
        structured_response = self.get_structured_response(session_id)
        if structured_response:
            return structured_response.get("input_messages", [])
        return []
    
    def get_output_message(self, session_id: str) -> Optional[Any]:
        """
        Get the output message from the most recent response in a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Output message object
        """
        structured_response = self.get_structured_response(session_id)
        if structured_response:
            return structured_response.get("output_message")
        return None
    
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
