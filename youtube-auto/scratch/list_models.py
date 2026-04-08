import logging
import sys
import os
from google import genai

# Thêm thư mục gốc vào path để import được modules
sys.path.append(os.getcwd())
from config import GEMINI_API_KEY

def main():
    client = genai.Client(api_key=GEMINI_API_KEY)
    print("--- AVAILABLE MODELS ---")
    try:
        for model in client.models.list():
            if 'image' in model.name.lower() or 'imagen' in model.name.lower():
                print(f"Name: {model.name}, Supported: {model.supported_actions}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    main()
