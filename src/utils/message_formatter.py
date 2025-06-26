# src/utils/message_formatter.py
"""
Message formatting utilities for different LLM message formats.
Supports OpenAI and Llama message formats with tool calling capabilities.
"""

import json
import logging
import uuid
import re
from typing import List, Dict, Any, Optional
from config.config import MESSAGE_FORMAT

logger = logging.getLogger('text2sql.message_formatter')


class MessageFormatter:
    """Handle formatting messages for different LLM providers."""
    
    @staticmethod
    def format_messages(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None, 
                       format_type: str = None) -> str:
        """
        Format messages according to the specified format.
        
        Args:
            messages: List of messages in OpenAI format
            tools: Optional list of tool definitions
            format_type: Format type ('openai' or 'llama'). If None, uses global config.
            
        Returns:
            Formatted message string
        """
        if format_type is None:
            format_type = MESSAGE_FORMAT
            
        if format_type == 'llama':
            return MessageFormatter._format_llama_messages(messages, tools)
        else:
            # Default to OpenAI format (return as-is for OpenAI API)
            return messages
    
    @staticmethod
    def _format_llama_messages(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Format messages for Llama models using the chat template format.
        
        Args:
            messages: List of messages in OpenAI format
            tools: Optional list of tool definitions
            
        Returns:
            Formatted Llama chat string
        """
        formatted_parts = ["<|begin_of_text|>"]
        
        # Process each message
        for i, message in enumerate(messages):
            role = message.get('role', 'user')
            content = message.get('content', '')
            
            if role == 'system':
                # System messages are handled as part of the first user message in Llama
                continue
            elif role == 'user':
                formatted_parts.append(f"<|start_header_id|>user<|end_header_id|>")
                
                # Include system message content if this is the first user message
                system_content = MessageFormatter._get_system_content(messages)
                if system_content and i == MessageFormatter._get_first_user_index(messages):
                    formatted_parts.append(f"System: {system_content}\n")
                
                # Add the user content
                if content:
                    formatted_parts.append(f"Questions: {content}")
                
                # Add tools if this is the first user message and tools are provided
                if tools and i == MessageFormatter._get_first_user_index(messages):
                    tools_text = MessageFormatter._format_tools_for_llama(tools)
                    formatted_parts.append(tools_text)
                    formatted_parts.append("\n" + "="*50)
                    formatted_parts.append("\nFUNCTION CALLING RULES:")
                    formatted_parts.append("1. If you need to use ANY function, respond with ONLY this JSON format:")
                    formatted_parts.append('{"tool_calls": [{"name": "function_name", "arguments": {"param1": "value1"}}]}')
                    formatted_parts.append("2. For multiple functions:")
                    formatted_parts.append('{"tool_calls": [{"name": "func1", "arguments": {...}}, {"name": "func2", "arguments": {...}}]}')
                    formatted_parts.append("3. NO explanations, NO markdown, NO extra text - ONLY the JSON")
                    formatted_parts.append("4. If no function is needed, give a normal text response")
                    formatted_parts.append("5. NEVER mix function calls with explanatory text")
                    formatted_parts.append("="*50)
                
                formatted_parts.append("<|eot_id|>")
                
            elif role == 'assistant':
                formatted_parts.append(f"<|start_header_id|>assistant<|end_header_id|>")
                
                # Check if this is a tool call response
                tool_calls = message.get('tool_calls')
                if tool_calls:
                    # Format tool calls in Llama format
                    tool_call_text = MessageFormatter._format_tool_calls_for_llama(tool_calls)
                    formatted_parts.append(tool_call_text)
                elif content:
                    formatted_parts.append(content)
                
                formatted_parts.append("<|eot_id|>")
                
            elif role == 'tool':
                # Tool responses are handled differently in Llama format
                # They become part of the conversation context
                tool_name = message.get('name', 'unknown_tool')
                tool_content = message.get('content', '')
                formatted_parts.append(f"<|start_header_id|>user<|end_header_id|>")
                formatted_parts.append(f"Tool {tool_name} returned: {tool_content}")
                formatted_parts.append("<|eot_id|>")
        
        return "".join(formatted_parts)
    
    @staticmethod
    def _get_system_content(messages: List[Dict[str, Any]]) -> str:
        """Extract system message content from messages list."""
        for message in messages:
            if message.get('role') == 'system':
                return message.get('content', '')
        return ''
    
    @staticmethod
    def _get_first_user_index(messages: List[Dict[str, Any]]) -> int:
        """Get the index of the first user message."""
        for i, message in enumerate(messages):
            if message.get('role') == 'user':
                return i
        return 0
    
    @staticmethod
    def _format_tools_for_llama(tools: List[Dict[str, Any]]) -> str:
        """Format tools list for Llama model."""
        if not tools:
            return ""
        
        tools_text = "\nHere is a list of functions in JSON format that you can invoke:\n"
        
        # Convert OpenAI tool format to Llama-compatible format
        llama_tools = []
        for tool in tools:
            if 'function' in tool:
                func = tool['function']
                llama_tool = {
                    "name": func.get('name', ''),
                    "description": func.get('description', ''),
                    "parameters": func.get('parameters', {})
                }
                
                # Ensure parameters have the right structure for Llama
                if 'properties' in llama_tool['parameters']:
                    # Convert properties to more Llama-friendly format
                    properties = llama_tool['parameters']['properties']
                    required = llama_tool['parameters'].get('required', [])
                    
                    # Ensure each property has proper type information
                    for prop_name, prop_info in properties.items():
                        if 'type' not in prop_info:
                            prop_info['type'] = 'string'  # Default type
                
                llama_tools.append(llama_tool)
        
        tools_text += json.dumps(llama_tools, indent=4)
        return tools_text
    
    @staticmethod
    def _format_tool_calls_for_llama(tool_calls: List[Dict[str, Any]]) -> str:
        """Format tool calls for Llama model response."""
        calls = []
        for call in tool_calls:
            function = call.get('function', {})
            name = function.get('name', '')
            args_str = function.get('arguments', '{}')
            
            try:
                args = json.loads(args_str) if isinstance(args_str, str) else args_str
                calls.append({
                    "name": name,
                    "arguments": args
                })
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call arguments: {args_str}")
                calls.append({
                    "name": name,
                    "arguments": {}
                })
        
        return json.dumps({"tool_calls": calls})
    
    @staticmethod
    def parse_llama_response(response_text: str, available_tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Parse Llama model response to extract tool calls or regular content.
        
        Args:
            response_text: Raw response from Llama model
            
        Returns:
            Parsed response with tool calls or content
        """
        response_text = response_text.strip()
        
        # Try to parse as JSON first
        try:
            parsed_json = json.loads(response_text)
            if isinstance(parsed_json, dict) and 'tool_calls' in parsed_json:
                tool_calls = []
                for tool_call_data in parsed_json['tool_calls']:
                    if isinstance(tool_call_data, dict) and 'name' in tool_call_data:
                        tool_call = {
                            'id': f"call_{uuid.uuid4().hex[:8]}",
                            'type': 'function',
                            'function': {
                                'name': tool_call_data['name'],
                                'arguments': json.dumps(tool_call_data.get('arguments', {}))
                            }
                        }
                        tool_calls.append(tool_call)
                
                if tool_calls:
                    return {
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': tool_calls
                    }
        except json.JSONDecodeError:
            # Not valid JSON, continue to other parsing methods
            pass
        
        # Look for JSON patterns in the response (in case there's extra text)
        # Try multiple regex patterns to catch different variations
        json_patterns = [
            r'\{[^{}]*"tool_calls"[^{}]*\[[^\]]*\][^{}]*\}',  # Simple pattern
            r'\{(?:[^{}]|{[^{}]*})*"tool_calls"(?:[^{}]|{[^{}]*})*\[(?:[^\[\]]|\[[^\[\]]*\])*\](?:[^{}]|{[^{}]*})*\}',  # Nested
            r'\{.*?"tool_calls".*?\[.*?\].*?\}',  # More flexible
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            
            for match in matches:
                try:
                    # Clean up the match - remove any leading/trailing non-JSON characters
                    match = match.strip()
                    
                    # Find the actual JSON boundaries
                    start_brace = match.find('{')
                    if start_brace != -1:
                        # Count braces to find the complete JSON object
                        brace_count = 0
                        end_pos = start_brace
                        for i, char in enumerate(match[start_brace:], start_brace):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    end_pos = i + 1
                                    break
                        
                        json_text = match[start_brace:end_pos]
                        parsed_json = json.loads(json_text)
                        
                        if isinstance(parsed_json, dict) and 'tool_calls' in parsed_json:
                            tool_calls = []
                            for tool_call_data in parsed_json['tool_calls']:
                                if isinstance(tool_call_data, dict) and 'name' in tool_call_data:
                                    tool_call = {
                                        'id': f"call_{uuid.uuid4().hex[:8]}",
                                        'type': 'function',
                                        'function': {
                                            'name': tool_call_data['name'],
                                            'arguments': json.dumps(tool_call_data.get('arguments', {}))
                                        }
                                    }
                                    tool_calls.append(tool_call)
                            
                            if tool_calls:
                                logger.info(f"Successfully parsed {len(tool_calls)} tool calls from LLaMA response")
                                return {
                                    'role': 'assistant',
                                    'content': None,
                                    'tool_calls': tool_calls
                                }
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug(f"Failed to parse JSON match: {match[:100]}... Error: {e}")
                    continue
        
        # Last resort: try to extract function names and arguments from natural language
        # Look for patterns like "I'll use the run_bash_shell function with command="ls -la""
        if available_tools:
            function_pattern = r'(\w+)\s*(?:function|tool)?\s*(?:with|using)?\s*(?:command|arguments?|params?)?\s*[=:]\s*["\']([^"\']*)["\']'
            matches = re.findall(function_pattern, response_text, re.IGNORECASE)
            
            if matches and len(matches) > 0:
                # Try to construct tool calls from natural language patterns
                tool_calls = []
                for func_name, arg_value in matches:
                    # Only proceed if the function name looks like a valid tool name
                    if any(func_name in tool.get('function', {}).get('name', '') for tool in available_tools if 'function' in tool):
                        tool_call = {
                            'id': f"call_{uuid.uuid4().hex[:8]}",
                            'type': 'function',
                            'function': {
                                'name': func_name,
                                'arguments': json.dumps({"command": arg_value}) if arg_value else json.dumps({})
                            }
                        }
                        tool_calls.append(tool_call)
                
                if tool_calls:
                    logger.info(f"Extracted {len(tool_calls)} tool calls from natural language patterns")
                    return {
                        'role': 'assistant',
                        'content': None,
                        'tool_calls': tool_calls
                    }
        
        # Regular text response
        return {
            'role': 'assistant',
            'content': response_text
        }
