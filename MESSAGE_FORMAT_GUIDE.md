# Message Format Support Guide

This guide explains how to use the new message format support in the Text2SQL application.

## Overview

The application now supports multiple message formats for different LLM providers:

- **OpenAI Format**: Standard OpenAI message format with native tool calling
- **Llama Format**: Custom Llama chat template format with tool calling implementation

## Configuration

### Environment Variable

Set the message format in your `.env` file:

```bash
# For OpenAI format (default)
MESSAGE_FORMAT=openai

# For Llama format
MESSAGE_FORMAT=llama
```

The configuration is automatically loaded on application startup.

## Format Details

### OpenAI Format

Standard OpenAI message format:

```json
[
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "What is the weather like?"},
  {"role": "assistant", "content": "I'll check the weather for you.", "tool_calls": [...]}
]
```

### Llama Format

Custom chat template format:

```
<|begin_of_text|><|start_header_id|>user<|end_header_id|>
System: You are a helpful assistant.
Questions: What is the weather like?
Here is a list of functions in JSON format that you can invoke:
[
    {
        "name": "get_weather",
        "description": "Get current weather information",
        "parameters": {...}
    }
]
Should you decide to return the function call(s), Put it in the format of [func1(params_name=params_value, params_name2=params_value2...), func2(params)]
NO other text MUST be included.<|eot_id|><|start_header_id|>assistant<|end_header_id|>
[get_weather(location="New York")]<|eot_id|>
```

## Tool Calling

### OpenAI Tool Calls

Native OpenAI tool calling format:

```json
{
  "role": "assistant",
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "function": {
        "name": "get_user_info",
        "arguments": "{\"user_id\": 7890}"
      }
    }
  ]
}
```

### Llama Tool Calls

Custom function call format:

```
[get_user_info(user_id=7890, special='black')]
```

This gets automatically converted to OpenAI format internally.

## Usage Examples

### Basic Text Generation

Both formats work transparently with the existing LLM engine:

```python
from src.utils.common_llm import get_llm_engine

llm = get_llm_engine()
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello, world!"}
]

response = llm.generate_completion(messages)
print(response)
```

### Tool Calling

Tool calling works the same way regardless of format:

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }
]

response = llm.generate_completion_with_tools(
    messages=messages,
    tools=tools,
    tool_choice="auto"
)
```

### MCP Integration

The MCP client manager automatically uses the configured format:

```python
from src.utils.mcp_client_manager import get_mcp_client_for_query

client = await get_mcp_client_for_query("Get user info for ID 7890")
async for update in client.process_query_stream("Get user info for ID 7890"):
    print(update)
```

## Testing

### Running Tests

Test the message formatting with the included test script:

```bash
python test_message_formats.py
```

### Admin Testing Interface

Use the admin interface to test formatting:

1. Go to **Admin** → **Message Format**
2. Select a format to test
3. Modify the sample messages and tools
4. Click **Test Format** to see the output

## Best Practices

### When to Use Each Format

- **OpenAI Format**: Use with OpenAI-compatible models and APIs
- **Llama Format**: Use with Llama models that expect chat templates

### Performance Considerations

- OpenAI format has native tool calling support
- Llama format requires additional parsing overhead
- Choose based on your model's requirements

### Debugging

Enable debug logging to see formatted messages:

```python
import logging
logging.getLogger('text2sql.message_formatter').setLevel(logging.DEBUG)
```

## Migration

### From OpenAI Only

If you're currently using OpenAI format only:

1. No changes needed - OpenAI remains the default
2. Optionally test Llama format in admin interface
3. Switch format via environment variable when ready

### Adding Custom Formats

To add support for additional formats:

1. Extend `MessageFormatter` class in `src/utils/message_formatter.py`
2. Add format to `SUPPORTED_MESSAGE_FORMATS` in config
3. Update admin interface options

## Troubleshooting

### Common Issues

1. **Format not recognized**: Check `MESSAGE_FORMAT` value in config
2. **Tool calls not working**: Verify tool definition format
3. **Parsing errors**: Check Llama response format

### Debug Information

The LLM engine logs include format information:

```
[MCP-ServerName] Tool-enabled completion generation started (format: llama)
```

Look for these logs to verify which format is being used.

## API Reference

### MessageFormatter Class

```python
MessageFormatter.format_messages(messages, tools, format_type)
MessageFormatter.parse_llama_response(response_text)
```

### Configuration

```python
from config.config import MESSAGE_FORMAT, SUPPORTED_MESSAGE_FORMATS
```

### Routes

- `GET /api/admin/message-format` - Get current format
- `POST /api/admin/message-format` - Set format
- `POST /api/admin/message-format/test` - Test format
