#!/usr/bin/env python3
"""
Test script for message formatting functionality.
This script tests both OpenAI and Llama message formats with tool calling.
"""

import os
import sys
import json

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.utils.message_formatter import MessageFormatter

def test_openai_format():
    """Test OpenAI message formatting."""
    print("Testing OpenAI Format:")
    print("=" * 50)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Can you retrieve the details for user ID 7890 with special request 'black'?"}
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_user_info",
                "description": "Retrieve details for a specific user by their unique identifier",
                "parameters": {
                    "type": "object",
                    "required": ["user_id"],
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "The unique identifier of the user"
                        },
                        "special": {
                            "type": "string", 
                            "description": "Any special information or parameters",
                            "default": "none"
                        }
                    }
                }
            }
        }
    ]
    
    formatted = MessageFormatter.format_messages(messages, tools, 'openai')
    print("Formatted messages (OpenAI):")
    print(json.dumps(formatted, indent=2))
    print()

def test_llama_format():
    """Test Llama message formatting."""
    print("Testing Llama Format:")
    print("=" * 50)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Can you retrieve the details for user ID 7890 with special request 'black'?"}
    ]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_user_info",
                "description": "Retrieve details for a specific user by their unique identifier",
                "parameters": {
                    "type": "object",
                    "required": ["user_id"],
                    "properties": {
                        "user_id": {
                            "type": "integer",
                            "description": "The unique identifier of the user"
                        },
                        "special": {
                            "type": "string",
                            "description": "Any special information or parameters",
                            "default": "none"
                        }
                    }
                }
            }
        }
    ]
    
    formatted = MessageFormatter.format_messages(messages, tools, 'llama')
    print("Formatted messages (Llama):")
    print(formatted)
    print()

def test_llama_response_parsing():
    """Test parsing Llama response format."""
    print("Testing Llama Response Parsing:")
    print("=" * 50)
    
    # Test function call response
    llama_response = "[get_user_info(user_id=7890, special='black')]"
    parsed = MessageFormatter.parse_llama_response(llama_response)
    print("Llama function call response:")
    print(f"Input: {llama_response}")
    print(f"Parsed: {json.dumps(parsed, indent=2)}")
    print()
    
    # Test regular text response
    text_response = "Here are the user details you requested..."
    parsed_text = MessageFormatter.parse_llama_response(text_response)
    print("Llama text response:")
    print(f"Input: {text_response}")
    print(f"Parsed: {json.dumps(parsed_text, indent=2)}")
    print()

def test_complex_conversation():
    """Test a complex conversation with multiple turns."""
    print("Testing Complex Conversation:")
    print("=" * 50)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant with access to user management tools."},
        {"role": "user", "content": "I need to find user 7890 and then update their information."},
        {"role": "assistant", "content": "I'll help you find and update user 7890. Let me first retrieve their current details."},
        {"role": "assistant", "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "get_user_info",
                    "arguments": '{"user_id": 7890}'
                }
            }
        ]},
        {"role": "tool", "tool_call_id": "call_123", "name": "get_user_info", "content": '{"id": 7890, "name": "John Doe", "email": "john@example.com"}'},
        {"role": "user", "content": "Great! Now please update their special field to 'premium'"}
    ]
    
    formatted_llama = MessageFormatter.format_messages(messages, [], 'llama')
    print("Complex conversation (Llama format):")
    print(formatted_llama)
    print()

if __name__ == "__main__":
    print("Message Format Testing")
    print("=" * 70)
    print()
    
    try:
        test_openai_format()
        test_llama_format()
        test_llama_response_parsing()
        test_complex_conversation()
        
        print("All tests completed successfully! ✓")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
