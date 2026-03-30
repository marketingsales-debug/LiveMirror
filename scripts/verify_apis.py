#!/usr/bin/env python3
"""
LiveMirror API Verification Script
Tests all NVIDIA API keys and models to ensure they're working correctly.
Run in Kaggle or locally: python scripts/verify_apis.py
"""

import asyncio
import sys
from typing import Dict, List, Tuple
import requests
from openai import OpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA

# ANSI Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# All API configurations
NVIDIA_APIS = [
    {
        "name": "NVIDIA API 1 - Mistral Small (requests)",
        "key": "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",
        "model": "mistralai/mistral-small-4-119b-2603",
        "type": "requests",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    {
        "name": "NVIDIA API 2 - Qwen 3.5 122B (requests)",
        "key": "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",
        "model": "qwen/qwen3.5-122b-a10b",
        "type": "requests",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    {
        "name": "NVIDIA API 3 - Nemotron Super 120B (OpenAI SDK)",
        "key": "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",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "type": "openai",
        "endpoint": "https://integrate.api.nvidia.com/v1",
    },
    {
        "name": "NVIDIA API 4 - Nemotron Super (LangChain)",
        "key": "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",
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "type": "langchain",
    },
    {
        "name": "NVIDIA API 5 - Llama Reranker (requests)",
        "key": "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",
        "model": "llama-nemotron-rerank-1b-v2",
        "type": "requests",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    {
        "name": "NVIDIA API 6 - Table Structure (requests)",
        "key": "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",
        "model": "nemotron-table-structure-v1",
        "type": "requests",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    {
        "name": "NVIDIA API 7 - Qwen 3.5 397B (requests)",
        "key": "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",
        "model": "qwen/qwen3.5-397b-a17b",
        "type": "requests",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
    },
    {
        "name": "NVIDIA API 8 - Qwen 3.5 397B (LangChain)",
        "key": "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",
        "model": "qwen/qwen3.5-397b-a17b",
        "type": "langchain",
    },
    {
        "name": "NVIDIA API 9 - Step 3.5 Flash (LangChain)",
        "key": "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",
        "model": "stepfun-ai/step-3.5-flash",
        "type": "langchain",
    },
    {
        "name": "NVIDIA API 10 - DeepSeek v3.2 (OpenAI SDK)",
        "key": "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",
        "model": "deepseek-ai/deepseek-v3.2",
        "type": "openai",
        "endpoint": "https://integrate.api.nvidia.com/v1",
    },
    {
        "name": "NVIDIA API 11 - Devstral 2 (OpenAI SDK)",
        "key": "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",
        "model": "mistralai/devstral-2-123b-instruct-2512",
        "type": "openai",
        "endpoint": "https://integrate.api.nvidia.com/v1",
    },
]

TEST_MESSAGE = "Say 'Hello, LiveMirror!' in exactly 3 words."


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(70)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{YELLOW}⚠ {text}{RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{BLUE}ℹ {text}{RESET}")


def test_requests_api(api_config: Dict) -> Tuple[bool, str]:
    """Test API using requests library."""
    try:
        headers = {
            "Authorization": f"Bearer {api_config['key']}",
            "Accept": "application/json"
        }
        payload = {
            "model": api_config["model"],
            "messages": [{"role": "user", "content": TEST_MESSAGE}],
            "max_tokens": 100,
            "temperature": 0.5,
            "stream": False,
        }

        response = requests.post(
            api_config["endpoint"],
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {}).get("content", "")
                return True, f"Response: {message[:100]}"
            return False, f"Invalid response format: {response.text[:200]}"
        elif response.status_code == 401:
            return False, "Authentication failed (401) - Invalid API key"
        elif response.status_code == 429:
            return False, "Rate limited (429) - Too many requests"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"

    except requests.exceptions.Timeout:
        return False, "Request timeout (30s)"
    except requests.exceptions.ConnectionError:
        return False, "Connection error - Check internet connectivity"
    except Exception as e:
        return False, f"Error: {str(e)[:200]}"


def test_openai_api(api_config: Dict) -> Tuple[bool, str]:
    """Test API using OpenAI SDK."""
    try:
        client = OpenAI(
            base_url=api_config["endpoint"],
            api_key=api_config["key"]
        )

        completion = client.chat.completions.create(
            model=api_config["model"],
            messages=[{"role": "user", "content": TEST_MESSAGE}],
            max_tokens=100,
            temperature=0.5,
        )

        if completion.choices:
            message = completion.choices[0].message.content
            return True, f"Response: {message[:100]}"
        return False, "No choices in response"

    except Exception as e:
        error_str = str(e)
        if "401" in error_str or "Unauthorized" in error_str:
            return False, "Authentication failed (401) - Invalid API key"
        elif "429" in error_str or "rate" in error_str.lower():
            return False, "Rate limited - Too many requests"
        else:
            return False, f"Error: {error_str[:200]}"


def test_langchain_api(api_config: Dict) -> Tuple[bool, str]:
    """Test API using LangChain."""
    try:
        client = ChatNVIDIA(
            model=api_config["model"],
            api_key=api_config["key"],
            temperature=0.5,
            max_tokens=100,
        )

        response = client.invoke([{"role": "user", "content": TEST_MESSAGE}])
        message = response.content if hasattr(response, "content") else str(response)
        return True, f"Response: {message[:100]}"

    except Exception as e:
        error_str = str(e)
        if "401" in error_str or "Unauthorized" in error_str or "api_key" in error_str.lower():
            return False, "Authentication failed - Invalid API key"
        elif "429" in error_str or "rate" in error_str.lower():
            return False, "Rate limited - Too many requests"
        else:
            return False, f"Error: {error_str[:200]}"


def main():
    """Run all API tests."""
    print_header("🚀 LiveMirror API Verification Suite")

    results: List[Dict] = []
    working = 0
    failed = 0

    for i, api_config in enumerate(NVIDIA_APIS, 1):
        api_type = api_config["type"]
        api_name = api_config["name"]

        print(f"{BOLD}[{i}/{len(NVIDIA_APIS)}] {api_name}{RESET}")
        print(f"    Model: {api_config['model']}")
        print(f"    Type: {api_type.upper()}")
        print(f"    Key: {api_config['key'][:20]}...{api_config['key'][-10:]}")

        try:
            if api_type == "requests":
                success, message = test_requests_api(api_config)
            elif api_type == "openai":
                success, message = test_openai_api(api_config)
            elif api_type == "langchain":
                success, message = test_langchain_api(api_config)
            else:
                success, message = False, f"Unknown API type: {api_type}"

            if success:
                print_success(message)
                working += 1
                results.append({"name": api_name, "status": "✓ WORKING", "message": message})
            else:
                print_error(message)
                failed += 1
                results.append({"name": api_name, "status": "✗ FAILED", "message": message})

        except Exception as e:
            error_msg = str(e)[:200]
            print_error(f"Unexpected error: {error_msg}")
            failed += 1
            results.append({"name": api_name, "status": "✗ ERROR", "message": error_msg})

        print()

    # Print summary
    print_header("📊 Verification Summary")
    print(f"Total APIs: {len(NVIDIA_APIS)}")
    print_success(f"Working: {working}")
    print_error(f"Failed: {failed}")

    success_rate = (working / len(NVIDIA_APIS)) * 100
    if success_rate == 100:
        print_success(f"Success Rate: {success_rate:.1f}%")
    elif success_rate >= 70:
        print_warning(f"Success Rate: {success_rate:.1f}%")
    else:
        print_error(f"Success Rate: {success_rate:.1f}%")

    # Detailed results table
    print(f"\n{BOLD}Detailed Results:{RESET}")
    print(f"{BOLD}{'API Name':<50} {'Status':<10} Message{RESET}")
    print("-" * 120)
    for result in results:
        status_colored = f"{GREEN}{result['status']}{RESET}" if "✓" in result['status'] else f"{RED}{result['status']}{RESET}"
        print(f"{result['name']:<50} {status_colored:<20} {result['message'][:50]}")

    # Exit code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
