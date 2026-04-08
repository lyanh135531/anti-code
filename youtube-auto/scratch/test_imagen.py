import os
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def test_image_gen():
    prompt = "A high-resolution cinematic shot of an ancient Buddhist temple on a mountain top during sunset, 8k, photorealistic"
    print(f"Generating image for: {prompt}")
    
    try:
        # Use the model that supports generateContent
        model = genai.GenerativeModel("gemini-3.1-flash-image-preview")
        
        response = model.generate_content(prompt)
        
        print(f"Response received.")
        
        found = False
        if hasattr(response, 'candidates') and response.candidates:
            for i, candidate in enumerate(response.candidates):
                for j, part in enumerate(candidate.content.parts):
                    if hasattr(part, 'inline_data') and part.inline_data:
                        print(f"Found image data in candidate {i}, part {j}")
                        # save to file
                        save_path = f"scratch/test_image_{i}_{j}.png"
                        with open(save_path, "wb") as f:
                            f.write(part.inline_data.data)
                        print(f"Saved to {save_path}")
                        found = True
        
        if not found:
            print("No image data found in response.")
            print(f"Full response text: {response.text}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_image_gen()
