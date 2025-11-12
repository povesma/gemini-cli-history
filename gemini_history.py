import os
import json
from datetime import datetime

GEMINI_DIR = os.path.expanduser("~/.gemini")
TMP_DIR = os.path.join(GEMINI_DIR, "tmp")

def find_sessions(current_project_hash):
    """Finds all automatically saved sessions for the current project."""
    sessions = []
    
    project_tmp_dir = os.path.join(TMP_DIR, current_project_hash)
    chats_dir = os.path.join(project_tmp_dir, "chats")

    if not os.path.exists(chats_dir):
        return sessions

    for session_file in os.listdir(chats_dir):
        if session_file.startswith("session-") and session_file.endswith(".json"):
            sessions.append(os.path.join(chats_dir, session_file))
    return sessions

import hashlib
import shutil

def get_project_root():
    """Gets the project root directory."""
    return os.getcwd()

def get_project_hash(project_root):
    """Gets the SHA256 hash of the project root directory."""
    return hashlib.sha256(project_root.encode()).hexdigest()

import urllib.parse

def save_session(session_path, name):
    """Saves a session as a named chat."""
    project_root = get_project_root()
    project_hash = get_project_hash(project_root)
    
    chats_dir = os.path.join(TMP_DIR, project_hash)
    if not os.path.exists(chats_dir):
        os.makedirs(chats_dir)

    encoded_name = urllib.parse.quote(name)
    destination = os.path.join(chats_dir, f"checkpoint-{encoded_name}.json")
    
    with open(session_path, "r") as f:
        session_data = json.load(f)
    
    transformed_messages = []
    for message in session_data.get("messages", []):
        transformed_message = {"parts": []}
        
        # Map 'type' to 'role'
        if message.get("type") == "user":
            transformed_message["role"] = "user"
        elif message.get("type") == "gemini":
            transformed_message["role"] = "model"
        else:
            # Skip unknown message types
            continue
            
        # Map 'content' to 'parts[0].text'
        if message.get("content"):
            transformed_message["parts"].append({"text": message["content"]})
            
        # Convert 'toolCalls' to 'functionCall' and 'functionResponse' parts
        if message.get("toolCalls"):
            for tool_call in message["toolCalls"]:
                if tool_call.get("name") and tool_call.get("args"):
                    transformed_message["parts"].append({
                        "functionCall": {
                            "name": tool_call["name"],
                            "args": tool_call["args"]
                        }
                    })
                if tool_call.get("result"):
                    for result_item in tool_call["result"]:
                        if result_item.get("functionResponse"):
                            transformed_message["parts"].append({
                                "functionResponse": result_item["functionResponse"]
                            })
        transformed_messages.append(transformed_message)

    with open(destination, "w") as f:
        json.dump(transformed_messages, f, indent=2)
        
    print(f"Session saved as '{name}'")

def main():
    """Main function."""
    current_project_hash = get_project_hash(get_project_root())
    sessions = find_sessions(current_project_hash)
    if not sessions:
        print("No sessions found for the current directory.")
        return

    print("Found the following sessions:")
    for i, session_path in enumerate(sessions):
        try:
            with open(session_path, "r") as f:
                data = json.load(f)
            start_time = datetime.fromisoformat(data["startTime"].replace("Z", "+00:00"))
            
            first_message = data["messages"][0]["content"] if data["messages"] else "No messages"
            last_message = data["messages"][-1]["content"] if data["messages"] else "No messages"
            
            print(f"{i+1}: {start_time.strftime('%Y-%m-%d %H:%M:%S')} - First: {first_message[:100]}... - Last: {last_message[:100]}...")
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Error reading session file {session_path}: {e}")

    try:
        selection = input("Enter the number of the session to save (or 'q' to quit): ")
        if selection.lower() == 'q':
            return

        session_index = int(selection) - 1
        if not 0 <= session_index < len(sessions):
            print("Invalid selection.")
            return

        name = input("Enter a name for the saved chat: ")
        if not name:
            print("Name cannot be empty.")
            return

        save_session(sessions[session_index], name)

    except ValueError:
        print("Invalid input.")

if __name__ == "__main__":
    main()
