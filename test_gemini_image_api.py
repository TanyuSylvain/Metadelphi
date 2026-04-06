#!/usr/bin/env python3
"""
Test script for Gemini Image Generation API via curl.

Based on CherryStudio's NewApiPage.tsx implementation:
  POST {apiHost}/v1/images/generations
  Authorization: Bearer {apiKey}
  Content-Type: application/json

  {
    "model": "gemini-3-pro-image-preview",
    "prompt": "...",
    "size": "1024x1024",
    "n": 1
  }

Environment variables:
  GEMINI_API_KEY: API key for authentication
  GEMINI_IMAGE_API_URL: Base URL, defaults to https://www.packyapi.com
  GEMINI_IMAGE_MODEL: Model name, e.g. gemini-3-pro-image-preview
"""

import subprocess
import base64
import os
import json
from dotenv import load_dotenv

load_dotenv()


def test_image_generation():
    """Test the Gemini image generation API using curl."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        return False

    base_url = os.getenv("GEMINI_IMAGE_API_URL", "https://www.packyapi.com")
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")

    # OpenAI-style images API (per CherryStudio NewApiPage.tsx)
    endpoint = f"{base_url}/v1/images/generations"

    prompt = "A cute orange cat sitting on a windowsill, warm afternoon light, photorealistic"

    # Request body - OpenAI images API format
    request_body = {
        "model": model,
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1
    }

    curl_cmd = [
        "curl",
        "-s",  # silent
        "-X", "POST",
        endpoint,
        "-H", f"Authorization: Bearer {api_key}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(request_body)
    ]

    print(f"Request: {prompt[:50]}...")
    print(f"Endpoint: {endpoint}")
    print(f"Model: {model}")
    print("-" * 50)

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        print("Error: Request timed out")
        return False
    except Exception as e:
        print(f"Error running curl: {e}")
        return False

    if result.returncode != 0:
        print(f"Error: curl returned code {result.returncode}")
        print(f"stderr: {result.stderr}")
        return False

    try:
        response = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response")
        print(f"Response: {result.stdout[:500]}")
        return False

    # Check for API errors
    if "error" in response:
        print(f"API Error: {response['error']}")
        return False

    # Parse response - can be URL or base64
    urls = []
    base64s = []

    if isinstance(response, dict):
        data = response.get("data", [])
        for item in data:
            if item.get("url"):
                urls.append(item["url"])
            if item.get("b64_json"):
                base64s.append(item["b64_json"])
    elif isinstance(response, list):
        for item in response:
            if item.get("url"):
                urls.append(item["url"])
            if item.get("b64_json"):
                base64s.append(item["b64_json"])

    if not urls and not base64s:
        print(f"Error: No images in response")
        print(f"Response: {json.dumps(response, indent=2)}")
        return False

    # Handle base64 images
    if base64s:
        try:
            image_bytes = base64.b64decode(base64s[0])
            print(f"Image decoded successfully: {len(image_bytes)} bytes")

            output_path = "test_output.png"
            with open(output_path, "wb") as f:
                f.write(image_bytes)
            print(f"Saved to: {output_path}")
            return True
        except Exception as e:
            print(f"Error decoding image: {e}")
            return False

    # Handle URL images (download)
    if urls:
        print(f"Image URL: {urls[0]}")
        print("(URL download not implemented - use base64 response)")
        return True

    return False


if __name__ == "__main__":
    success = test_image_generation()
    exit(0 if success else 1)
