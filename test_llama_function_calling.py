#!/usr/bin/env python3
"""
Test script to validate LLaMA function calling integration
"""

import sys
import os
import asyncio
import json
import logging

# Add project root to path
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(level=logging.INFO)

from src.utils.message_formatter import MessageFormatter
from src.utils.llm_engine import LLMEngine

def test_message_formatting():
    """Test the message formatting for LLaMA"""
    print("Testing LLaMA message formatting...")
    
    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Get the largest file in current directory"}
    ]
    
    # Test tools
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_bash_shell",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute"
                        }
                    },
                    "required": ["command"]
                }
            }
        }
    ]
    
    # Format for LLaMA
    formatted = MessageFormatter.format_messages(messages, tools, 'llama')
    print("Formatted LLaMA prompt:")
    print(formatted)
    print("=" * 50)
    
def test_response_parsing():
    """Test parsing LLaMA responses"""
    print("Testing LLaMA response parsing...")
    
    # Test cases
    test_responses = [
        '{"tool_calls": [{"name": "run_bash_shell", "arguments": {"command": "ls -la"}}]}',
        '{"tool_calls": [{"name": "run_bash_shell", "arguments": {"command": "ls -la"}}, {"name": "read_file", "arguments": {"file_path": "test.txt"}}]}',
        'I need to run a command. {"tool_calls": [{"name": "run_bash_shell", "arguments": {"command": "pwd"}}]}',
        'Here is the answer without any function calls.',
        '{"tool_calls": [{"name": "get_largest_file", "arguments": {}}]}',
        'To find the largest file, I will run: {"tool_calls": [{"name": "run_bash_shell", "arguments": {"command": "find . -type f -exec ls -la {} + | sort -k5 -rn | head -1"}}]}',
        '{"tool_calls": [{"name": "execute_sql_query", "arguments": {"query": "SELECT * FROM users LIMIT 10"}}]}'
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\nTest case {i}: {response}")
        parsed = MessageFormatter.parse_llama_response(response)
        print(f"Parsed: {json.dumps(parsed, indent=2)}")
    
    print("=" * 50)

async def test_llm_integration():
    """Test the full LLM integration"""
    print("Testing LLM integration...")
    
    try:
        # Initialize LLM engine
        llm = LLMEngine()
        
        # Test messages
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "List the contents of the current directory"}
        ]
        
        # Test tools
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "run_bash_shell",
                    "description": "Execute a shell command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Shell command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                }
            }
        ]
        
        # Generate completion with tools
        response = llm.generate_completion_with_tools(
            messages=messages,
            tools=tools,
            tool_choice="auto",
            log_prefix="TEST"
        )
        
        message = response.choices[0].message
        print(f"Response content: {message.content}")
        print(f"Has tool calls: {hasattr(message, 'tool_calls') and message.tool_calls is not None}")
        
        if hasattr(message, 'tool_calls') and message.tool_calls:
            print(f"Tool calls ({len(message.tool_calls)}):")
            for i, tool_call in enumerate(message.tool_calls):
                print(f"  {i+1}. {tool_call.function.name}({tool_call.function.arguments})")
        
    except Exception as e:
        print(f"Error in LLM integration test: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 50)

def main():
    """Run all tests"""
    print("LLaMA Function Calling Integration Test")
    print("=" * 50)
    
    # Test 1: Message formatting
    test_message_formatting()
    
    # Test 2: Response parsing
    test_response_parsing()
    
    # Test 3: Full LLM integration
    asyncio.run(test_llm_integration())
    
    print("Tests completed!")

if __name__ == "__main__":
    main()
