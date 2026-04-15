#!/usr/bin/env python3
"""
Test script for Gemini Image Generation API via curl.

Uses the native Gemini generateContent endpoint to support aspect-ratio control,
with fallbacks to OpenAI-style /v1/images/generations and /v1/chat/completions.

Environment variables:
  GEMINI_API_KEY: API key for authentication
  GEMINI_IMAGE_API_URL: Base URL, defaults to https://www.packyapi.com
  GEMINI_IMAGE_MODEL: Model name, e.g. gemini-3.1-flash-image-preview
  GEMINI_IMAGE_ASPECT_RATIO: Optional aspect ratio, e.g. 1:1, 16:9, 4:3
"""

import subprocess
import base64
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()


def run_curl(endpoint, headers, body, timeout=120):
    """Run a curl POST request and return the parsed JSON response or None."""
    cmd = [
        "curl",
        "-s",
        "-X", "POST",
        endpoint,
        "-H", "Content-Type: application/json",
    ]
    for key, value in headers.items():
        cmd.extend(["-H", f"{key}: {value}"])
    cmd.extend(["-d", json.dumps(body)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("Error: Request timed out")
        return None
    except Exception as e:
        print(f"Error running curl: {e}")
        return None

    if result.returncode != 0:
        print(f"Error: curl returned code {result.returncode}")
        print(f"stderr: {result.stderr}")
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response")
        print(f"Response: {result.stdout[:500]}")
        return None


def parse_images_api_response(response):
    """Parse OpenAI-style /v1/images/generations response."""
    urls = []
    base64s = []
    data = response.get("data", []) if isinstance(response, dict) else response if isinstance(response, list) else []
    for item in data:
        if item.get("url"):
            urls.append(item["url"])
        if item.get("b64_json"):
            base64s.append(item["b64_json"])
    return urls, base64s


def extract_base64_from_markdown(content):
    """Extract base64 image data from markdown ![image](data:image/...;base64,...)"""
    if not content:
        return []
    pattern = r'!\[image\]\(data:image/[^;]+;base64,([^)]+)\)'
    return re.findall(pattern, content)


def save_base64_image(b64_data, output_path="test_output.png"):
    """Decode and save a base64 image."""
    try:
        image_bytes = base64.b64decode(b64_data)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        print(f"Image decoded successfully: {len(image_bytes)} bytes")
        print(f"Saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error decoding image: {e}")
        return False


def test_native_gemini_generate(base_url, api_key, model, prompt, aspect_ratio=None):
    """Call the native Gemini generateContent endpoint."""
    endpoint = f"{base_url}/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        }
    }
    image_config = {}
    if aspect_ratio:
        image_config["aspectRatio"] = aspect_ratio
    image_size = os.getenv("GEMINI_IMAGE_SIZE")
    if image_size:
        image_config["imageSize"] = image_size
    if image_config:
        body["generationConfig"]["imageConfig"] = image_config

    print(f"Trying native Gemini generateContent: {endpoint.split('?')[0]}")
    print(f"  aspect_ratio: {aspect_ratio or '(default)'}")
    print(f"  image_size:   {image_size or '(default)'}")

    response = run_curl(endpoint, {}, body)
    if response is None:
        return None
    if "error" in response:
        print(f"Native API Error: {response['error']}")
        return None

    # Extract inlineData images from candidates
    candidates = response.get("candidates", [])
    for candidate in candidates:
        for part in candidate.get("content", {}).get("parts", []):
            if "inlineData" in part:
                mime_type = part["inlineData"].get("mimeType", "image/png")
                b64_data = part["inlineData"].get("data", "")
                if b64_data:
                    print(f"  Found inline image ({mime_type})")
                    return b64_data
    return None


def test_image_generation():
    """Test the Gemini image generation API using curl."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set")
        return False

    base_url = os.getenv("GEMINI_IMAGE_API_URL", "https://www.packyapi.com")
    model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    aspect_ratio = os.getenv("GEMINI_IMAGE_ASPECT_RATIO")

    prompt = "A cute orange cat sitting on a windowsill, warm afternoon light, photorealistic"

    print(f"Request: {prompt[:50]}...")
    print(f"Model: {model}")
    print("-" * 50)

    # ------------------------------------------------------------------
    # 1) Native Gemini generateContent (supports aspect ratio / resolution)
    # ------------------------------------------------------------------
    b64_data = test_native_gemini_generate(base_url, api_key, model, prompt, aspect_ratio)
    if b64_data:
        return save_base64_image(b64_data)

    # ------------------------------------------------------------------
    # 2) Fallback to OpenAI-style /v1/images/generations
    # ------------------------------------------------------------------
    print("\nFalling back to OpenAI-style images API...")
    images_endpoint = f"{base_url}/v1/images/generations"
    images_body = {
        "model": model,
        "prompt": prompt,
        "n": 1,
    }
    size = os.getenv("GEMINI_IMAGE_SIZE")
    if size:
        images_body["size"] = size

    response = run_curl(images_endpoint, {"Authorization": f"Bearer {api_key}"}, images_body)
    images_api_failed = False

    if response is None:
        images_api_failed = True
    elif "error" in response:
        err = response["error"]
        msg = err.get("message", "") if isinstance(err, dict) else str(err)
        print(f"Images API Error: {msg}")
        if "not supported model" in msg.lower() or "convert_request_failed" in msg.lower():
            images_api_failed = True
        else:
            return False

    if not images_api_failed:
        urls, base64s = parse_images_api_response(response)
        if urls:
            print(f"Image URL: {urls[0]}")
            print("(URL download not implemented - use base64 response)")
            return True
        if base64s:
            return save_base64_image(base64s[0])
        print("Error: No images in response")
        print(f"Response: {json.dumps(response, indent=2)}")
        images_api_failed = True

    # ------------------------------------------------------------------
    # 3) Fallback to /v1/chat/completions
    # ------------------------------------------------------------------
    print("\nFalling back to chat completions API...")
    chat_endpoint = f"{base_url}/v1/chat/completions"
    chat_body = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    if size:
        chat_body["size"] = size

    response = run_curl(chat_endpoint, {"Authorization": f"Bearer {api_key}"}, chat_body)
    if response is None:
        return False

    if "error" in response:
        print(f"Chat API Error: {response['error']}")
        return False

    choices = response.get("choices", []) if isinstance(response, dict) else []
    content = ""
    if choices:
        content = choices[0].get("message", {}).get("content", "")

    base64s = extract_base64_from_markdown(content)
    if base64s:
        return save_base64_image(base64s[0])

    message = choices[0].get("message", {}) if choices else {}
    images = message.get("images", []) if isinstance(message, dict) else []
    if images:
        image_url = images[0].get("image_url", {}).get("url", "") if isinstance(images[0], dict) else ""
        if image_url.startswith("data:image"):
            b64 = image_url.split("base64,", 1)[-1]
            return save_base64_image(b64)
        elif image_url:
            print(f"Image URL: {image_url}")
            return True

    print("Error: No images in chat response")
    print(f"Response content: {content[:500] if content else '(empty)'}")
    return False


if __name__ == "__main__":
    success = test_image_generation()
    exit(0 if success else 1)
