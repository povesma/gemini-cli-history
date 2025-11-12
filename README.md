# Gemini CLI Session Recovery Tool

This Python script, `gemini_history.py`, provides a mechanism to recover and persist automatically saved sessions from the Gemini CLI as manually savable checkpoints. These checkpoints can then be listed and resumed using the native `/chat list` and `/chat resume <tag>` commands within the Gemini CLI.

## Problem Statement

The Gemini CLI automatically saves conversational sessions in temporary directories. However, there is no direct command-line interface to list or resume these automatically saved sessions. While the CLI offers `/chat save <tag>` and `/chat resume <tag>` for manually managed checkpoints, these do not inherently interact with the automatically generated session data. This tool bridges that gap, allowing users to recover sessions that might otherwise be lost due to unexpected application closures or system events.

## Functionality

The `gemini_history.py` script performs the following operations:

1.  **Session Discovery**: Scans the Gemini CLI's temporary directory structure to locate all automatically saved session files.
2.  **Session Listing**: Presents a numbered list of discovered sessions, including their start time and the content of the last message, to aid in identification.
3.  **Session Persistence**: Allows the user to select an automatically saved session and assign a custom tag (name) to it. The script then transforms and copies the selected session's data into a format compatible with the Gemini CLI's manual checkpoint system.

## Technical Details

### Storage Locations

*   **Automatically Saved Sessions**: The Gemini CLI stores its ephemeral session data in a project-specific temporary directory. This directory is typically located at `~/.gemini/tmp/<project_hash>/chats/session-<timestamp>-<session_id>.json`. The `<project_hash>` is a SHA256 hash of the current working directory where the `gemini` CLI was invoked.
*   **Manually Saved Checkpoints**: The Gemini CLI expects manually saved checkpoints to reside in `~/.gemini/tmp/<project_hash>/checkpoint-<encoded_tag>.json`. The `<encoded_tag>` is the URL-encoded version of the user-provided tag.

### Data Transformation

The core challenge addressed by this tool is the structural difference between automatically saved session files and manually saved checkpoint files.

*   **Automatic Session File Structure**: These files are JSON objects containing metadata (`sessionId`, `projectHash`, `startTime`, `lastUpdated`) and a `messages` array. Each message object within this array contains fields such as `id`, `timestamp`, `type` (e.g., "user", "gemini"), `content` (raw text), `thoughts`, `tokens`, `model`, and `toolCalls`.

    **Example (`sample_live_session.json`):**
    ```json
    {
      "sessionId": "sample-session-id-123",
      "projectHash": "sample-project-hash-abc",
      "startTime": "2025-11-12T07:00:00.000Z",
      "lastUpdated": "2025-11-12T07:05:00.000Z",
      "messages": [
        {
          "id": "msg-1",
          "timestamp": "2025-11-12T07:00:00.000Z",
          "type": "user",
          "content": "Hello, Gemini! What's the weather like today?"
        },
        {
          "id": "msg-2",
          "timestamp": "2025-11-12T07:01:00.000Z",
          "type": "gemini",
          "content": "I need to use a tool to get the weather. What's your location?",
          "toolCalls": [
            {
              "id": "tool-call-1",
              "name": "get_weather",
              "args": {
                "location": "New York"
              }
            }
          ]
        },
        {
          "id": "msg-3",
          "timestamp": "2025-11-12T07:02:00.000Z",
          "type": "user",
          "content": "My location is New York."
        },
        {
          "id": "msg-4",
          "timestamp": "2025-11-12T07:03:00.000Z",
          "type": "gemini",
          "content": "The weather in New York is sunny with a temperature of 25°C.",
          "toolCalls": [
            {
              "id": "tool-call-1",
              "name": "get_weather",
              "args": {
                "location": "New York"
              },
              "result": [
                {
                  "functionResponse": {
                    "id": "tool-call-1",
                    "name": "get_weather",
                    "response": {
                      "output": "{\"temperature\": 25, \"conditions\": \"sunny\"}"
                    }
                  }
                }
              ]
            }
          ]
        }
      ]
    }
    ```

*   **Manual Checkpoint File Structure**: These files are JSON arrays where each element is a message object. Each message object is expected to have a `role` (e.g., "user", "model") and a `parts` array. The `parts` array can contain objects with a `text` key for conversational content, or `functionCall` and `functionResponse` keys for tool interactions.

    **Example (`sample_saved_chat.json`):**
    ```json
    [
      {
        "role": "user",
        "parts": [
          {
            "text": "Hello, Gemini! What's the weather like today?"
          }
        ]
      },
      {
        "role": "model",
        "parts": [
          {
            "text": "I need to use a tool to get the weather. What's your location?"
          },
          {
            "functionCall": {
              "name": "get_weather",
              "args": {
                "location": "New York"
              }
            }
          }
        ]
      },
      {
        "role": "user",
        "parts": [
          {
            "text": "My location is New York."
          }
        ]
      },
      {
        "role": "model",
        "parts": [
          {
            "text": "The weather in New York is sunny with a temperature of 25°C."
          },
          {
            "functionResponse": {
              "id": "tool-call-1",
              "name": "get_weather",
              "response": {
                "output": "{\"temperature\": 25, \"conditions\": \"sunny\"}"
              }
            }
          ]
        }
      }
    ]
    ```

The `gemini_history.py` script performs the following transformation:

1.  **Extraction**: It extracts the `messages` array from the automatically saved session file.
2.  **Message Iteration**: For each message in the extracted array:
    *   **Role Mapping**: The `type` field is mapped to `role` (`"user"` -> `"user"`, `"gemini"` -> `"model"`).
    *   **Content Mapping**: The `content` field is placed into a `parts` array as an object with a `text` key (`{"parts": [{"text": message["content"]}]}`).
    *   **Tool Call Handling**: If `toolCalls` are present in the original message, they are converted into `functionCall` and `functionResponse` objects within the `parts` array, mirroring the structure expected by the Gemini CLI for tool interactions.
3.  **Serialization**: The transformed array of message objects is then serialized as a JSON array and saved to the new checkpoint file.

### Project Hash Calculation

The script dynamically determines the `project_hash` by calculating the SHA256 hash of the current working directory. This ensures that the checkpoint is saved in the correct project-specific temporary directory, making it discoverable by the Gemini CLI when invoked from that same project context.

### Tag Encoding

The user-provided tag for the new checkpoint is URL-encoded using `urllib.parse.quote()`. This is crucial because the Gemini CLI's internal `_checkpointPath` function (located in `packages/core/src/core/logger.ts`) expects the tag in the filename to be URL-encoded to handle special characters safely.

## Usage

1.  **Navigate to your project directory**: Open your terminal and change to the directory where you typically run the `gemini` CLI for the session you wish to recover.
2.  **Run the script**: Execute the `gemini_history.py` script:
    ```bash
    python3 gemini_history.py
    ```
3.  **Select a session**: The script will display a numbered list of automatically saved sessions. Enter the number corresponding to the session you want to save.
4.  **Provide a name**: Enter a descriptive name (tag) for your new checkpoint.
5.  **Resume in Gemini CLI**: Once the script confirms the session is saved, you can launch the Gemini CLI and use the following commands:
    *   `/chat list`: To see your newly saved checkpoint.
    *   `/chat resume <your_chosen_tag>`: To resume the conversation from that checkpoint.
