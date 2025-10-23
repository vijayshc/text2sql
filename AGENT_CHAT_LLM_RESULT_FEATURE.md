# Agent Chat - LLM Result JSON Viewer Feature

## Overview
This feature adds the ability to view the detailed LLM result JSON directly from the agent chat UI. When an agent provides a final response, a clickable icon appears that displays the complete `llm_result` data in a modal dialog.

## Changes Made

### 1. Frontend Changes (`static/js/agent-chat.js`)

#### Added Variables
- `lastLlmResult`: Tracks the most recent LLM result JSON data for the current response

#### Modified `addMessage()` Function
- Added new parameter: `llmResultData = null`
- Stores the llm_result data when provided
- For final agent messages with llm_result data, adds a clickable icon button in the avatar container:
  - FontAwesome code icon (`fa-code`)
  - Positioned next to the robot avatar icon at the top
  - Tooltip: "View LLM Result JSON"
  - Click handler that opens the JSON modal

#### Updated `handleUpdate()` Function
- Modified the `llm_response` case to pass `llm_result` data from the server update
- Passes `update.llm_result || null` to the `addMessage()` function

#### Added `showLlmResultModal()` Function
- Creates and displays a Bootstrap modal with the LLM result JSON
- Features:
  - Pretty-printed JSON display with dark theme
  - Scrollable content area (max-height: 500px)
  - Copy button with visual feedback
  - Modal is created dynamically on first use and reused for subsequent calls

### 3. CSS Changes (`static/css/admin/agent-chat-enhanced.css`)

#### Avatar Container Styling
- Modified `.system-message .avatar` to support flexible width for icon button
- Changed from fixed 32px width to `width: auto` with `min-width: 32px`
- Added `gap: 4px` for spacing between avatar icon and button

#### LLM JSON Button Styling
- Added `.system-message .avatar .view-llm-json` for button styling
- Hover effect with scale transform (1.1x) for better interaction feedback
- Smooth opacity transition on hover

### 4. Backend Changes (`src/routes/autogen_routes.py`)

#### Modified `autogen_chat_stream()` Function
In the success response path:
- After getting the reply, fetches the run events using `RunMonitor.get_events(run_id)`
- Searches for the last `llm_result` event type in reversed order
- Extracts the `detail` field from the event as `llm_result_data`
- Includes `llm_result` in the SSE response JSON

## How It Works

1. **User sends a query** in agent chat mode (AutoGen team/workflow)

2. **Backend processes** the request through AutoGen orchestrator:
   - Logs an `llm_result` event in the run monitor database
   - Returns the final reply along with the run_id

3. **Backend fetches llm_result**:
   - Queries the run events to find the `llm_result` event
   - Extracts the detail JSON containing the full LLM response

4. **Frontend receives** the SSE update with:
   - `type`: 'llm_response'
   - `content`: The final answer text
   - `is_final`: true
   - `llm_result`: Complete JSON data from the LLM

5. **Frontend displays**:
   - Shows the formatted markdown response
   - Adds a small code icon button in the avatar area (next to robot icon)
   - Icon is visible with opacity 0.8 for subtlety

6. **User clicks icon**:
   - Modal opens showing pretty-printed JSON
   - User can copy the JSON or close the modal

## UI Features

### Icon Button Styling
- Font size: 1rem (matches avatar icon size)
- Opacity: 0.8 (semi-transparent)
- Positioned in avatar container, next to the robot icon
- Uses FontAwesome code icon
- Hover effect: scales to 1.1x with full opacity

### Modal Features
- Large modal dialog (`modal-lg`)
- Scrollable content
- Dark background for JSON display
- Copy button with success feedback
- Bootstrap 5 styling

## Use Cases

1. **Debugging**: Developers can inspect the raw LLM output structure
2. **Analysis**: Review the complete response including metadata like elapsed time and stop reason
3. **Troubleshooting**: Understand what the LLM actually returned vs. what was displayed
4. **Documentation**: Copy the JSON for bug reports or documentation

## Example LLM Result Data Structure

```json
{
  "reply": "messages=[TextMessage(...), ...]",
  "elapsed_sec": 2.345,
  "stop_reason": "stop"
}
```

## Testing

To test this feature:

1. Navigate to Agent Mode in the UI
2. Select an AutoGen team or workflow
3. Send a query
4. Wait for the final response
5. Look for the code icon (`</>`) next to the agent's response
6. Click the icon to view the LLM result JSON
7. Test the Copy button to copy the JSON to clipboard

## Browser Compatibility

- Requires modern browser with:
  - Clipboard API support for copy functionality
  - Bootstrap 5
  - FontAwesome icons
  - ES6 JavaScript features

## Future Enhancements

Possible improvements:
- Syntax highlighting for the JSON display
- Download JSON as a file
- Show multiple llm_result events if there were multiple LLM calls
- Filter or expand specific sections of the JSON
- Compare multiple LLM results side-by-side
