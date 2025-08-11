# app/prompt_loader.py

from pathlib import Path

def load_prompt(file_name: str) -> str:
    """
    Loads a prompt from a file in the 'prompts' directory.
    """
    prompt_path = Path(__file__).parent / "prompts" / file_name
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Fallback or error handling
        return f"Error: Prompt file '{file_name}' not found."