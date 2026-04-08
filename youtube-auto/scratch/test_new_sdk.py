import logging
import sys
import os
from pathlib import Path

# Thêm thư mục gốc vào path để import được modules
sys.path.append(os.getcwd())

from modules.gemini_image_gen import generate_single_image

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    test_dir = Path("output/test_sdk_v2")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    prompt = "A high-quality cinematic shot of an ancient library with floating books, magic glowing, 8k"
    save_path = test_dir / "test_imagen_new.png"
    
    print(f"--- TESTING NEW SDK WITH IMAGEN ---")
    success = generate_single_image(prompt, save_path)
    
    if success:
        print(f"✅ SUCCESS! Image saved to: {save_path}")
    else:
        print(f"❌ FAILED. Please check the logs above.")

if __name__ == "__main__":
    main()
