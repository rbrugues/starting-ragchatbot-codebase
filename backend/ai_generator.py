import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive search tools for course information.

Available Tools:
1. **Content Search Tool** - For questions about specific course content or detailed educational materials
2. **Course Outline Tool** - For questions about course structure, lesson lists, or course navigation

Multi-Round Tool Usage Guidelines:
- **Strategic tool use**: You can make multiple tool calls across up to 2 rounds to gather comprehensive information
- **Progressive refinement**: Use initial tool results to inform more targeted follow-up searches
- **Information synthesis**: Combine results from multiple tool calls to provide complete answers
- **Efficiency focus**: Only use additional rounds when initial results are insufficient

Tool Usage Protocol:
- **Content questions**: Use content search for specific topics, concepts, or detailed course material
- **Structure questions**: Use outline tool for course overviews, lesson lists, or when users ask "what's in this course"
- **Multi-aspect queries**: Break down complex questions into multiple targeted tool calls
- **Verification searches**: Use follow-up searches to verify or expand on initial findings
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tools across multiple rounds if needed
- **Comprehensive synthesis**: Always provide a complete answer that addresses all aspects of the user's question
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the tool"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
5. **Comprehensive** - Address all aspects of the user's question using information from all tool calls
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.use_mock = not api_key or api_key == "your-anthropic-api-key-here"
        
        if not self.use_mock:
            self.client = anthropic.Anthropic(api_key=api_key)
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         enable_multi_round: bool = True) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            enable_multi_round: Whether to enable multi-round tool calling
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Use mock responses if no API key
        if self.use_mock:
            return self._generate_mock_response(query, tools, tool_manager)
        
        # Choose single-round or multi-round approach
        if enable_multi_round and tools and tool_manager:
            return self.generate_response_with_rounds(
                query, conversation_history, tools, tool_manager, max_rounds=2
            )
        else:
            # Fall back to original single-round behavior
            return self._generate_single_round_response(
                query, conversation_history, tools, tool_manager
            )
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text
    
    def _generate_mock_response(self, _query: str, _tools: Optional[List] = None, _tool_manager=None) -> str:
        """Generate response when no API key is available"""
        return "API key not configured. Please set your Anthropic API key to use this service."
    
    def generate_response_with_rounds(self, query: str,
                                    conversation_history: Optional[str] = None,
                                    tools: Optional[List] = None,
                                    tool_manager=None,
                                    max_rounds: int = 2) -> str:
        """
        Generate AI response with multi-round tool calling support.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool-calling rounds (default: 2)
            
        Returns:
            Generated response as string
        """
        # Initialize round tracking
        current_round = 0
        messages = [{"role": "user", "content": query}]
        
        while current_round < max_rounds:
            current_round += 1
            
            # Build system content for current round
            system_content = self._build_system_content_for_round(
                conversation_history, current_round, max_rounds
            )
            
            # Make API call with tools
            try:
                response = self._make_api_call_with_tools(messages, system_content, tools)
            except Exception as e:
                return f"Error in round {current_round}: {str(e)}"
            
            # Check if tools were used
            if response.stop_reason != "tool_use":
                # No tools used - return response
                return response.content[0].text
            
            # Execute tools and update messages
            try:
                messages = self._execute_tools_and_update_messages(response, messages, tool_manager)
            except Exception as e:
                return f"Tool execution error in round {current_round}: {str(e)}"
        
        # Final call without tools
        system_content = self._build_system_content_for_round(
            conversation_history, current_round, max_rounds, final_round=True
        )
        try:
            final_response = self._make_final_api_call(messages, system_content)
            return final_response.content[0].text
        except Exception as e:
            return f"Error generating final response: {str(e)}"
    
    def _generate_single_round_response(self, query: str,
                                      conversation_history: Optional[str] = None,
                                      tools: Optional[List] = None,
                                      tool_manager=None) -> str:
        """
        Original single-round response generation logic.
        """
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return response.content[0].text
    
    def _build_system_content_for_round(self, conversation_history: Optional[str], 
                                      current_round: int, max_rounds: int,
                                      final_round: bool = False) -> str:
        """
        Build system content with round-specific guidance.
        """
        base_prompt = self.SYSTEM_PROMPT
        
        if conversation_history:
            base_prompt += f"\n\nPrevious conversation:\n{conversation_history}"
        
        # Add round-specific instructions
        if final_round:
            base_prompt += "\n\nThis is your final response. Provide a comprehensive answer based on all the information gathered. No more tools are available."
        elif current_round > 0:
            remaining_rounds = max_rounds - current_round
            if remaining_rounds > 0:
                base_prompt += f"\n\nROUND {current_round}/{max_rounds}: You have {remaining_rounds} more tool call opportunities. Use them to gather additional information if needed, or provide a final answer if you have sufficient information."
            else:
                base_prompt += f"\n\nROUND {current_round}/{max_rounds}: This is your final tool round. Use tools if you need additional information."
        
        return base_prompt
    
    def _make_api_call_with_tools(self, messages: List[Dict], system_content: str, tools: Optional[List]):
        """
        Make API call with tools enabled.
        """
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        return self.client.messages.create(**api_params)
    
    def _make_final_api_call(self, messages: List[Dict], system_content: str):
        """
        Make final API call without tools.
        """
        api_params = {
            **self.base_params,
            "messages": messages,
            "system": system_content
        }
        
        return self.client.messages.create(**api_params)
    
    def _execute_tools_and_update_messages(self, response, messages: List[Dict], tool_manager) -> List[Dict]:
        """
        Execute tools from response and update message history.
        
        Returns:
            Updated messages list with assistant response and tool results
        """
        # Add AI's tool use response
        updated_messages = messages.copy()
        updated_messages.append({"role": "assistant", "content": response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        has_successful_execution = False
        
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
                    has_successful_execution = True
                    
                except Exception as e:
                    # Log error but continue with other tools
                    error_message = f"Tool execution failed: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": error_message,
                        "is_error": True
                    })
        
        # Add tool results as user message
        if tool_results:
            updated_messages.append({"role": "user", "content": tool_results})
        
        # Raise exception if no tools executed successfully
        if not has_successful_execution:
            raise Exception("All tool executions failed")
        
        return updated_messages