#!/usr/bin/env python3
"""
Simple Python script demonstrating OpenAI API usage through the proxy server.
This script shows how to use the OpenAI Python package to connect to the proxy server.
"""

import os
import sys
from openai import OpenAI


def main():
    # Configure the client to use our proxy server
    proxy_base_url = os.environ.get("PROXY_BASE_URL", "http://localhost:8080")
    api_key = os.environ.get("OPENAI_API_KEY", "dummy-key-for-testing")

    if not api_key or api_key == "dummy-key-for-testing":
        print("Warning: Using dummy API key. Set OPENAI_API_KEY environment variable for real usage.")

    # Initialize OpenAI client pointing to our proxy
    client = OpenAI(
        api_key=api_key,
        base_url=proxy_base_url
    )

    print("=== Testing Non-Streaming Request ===")
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say hello and introduce yourself briefly."}
            ],
            temperature=0.7
        )

        print(f"Response: {response.choices[0].message.content}")
        print(f"Model: {response.model}")
        print(f"Usage: {response.usage}")

    except Exception as e:
        print(f"Non-streaming request failed: {e}")

    print("\n=== Testing Streaming Request ===")
    try:
        stream = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Count from 1 to 5 slowly, one number per line."}
            ],
            temperature=0.7,
            stream=True
        )

        print("Streaming response:")
        for chunk in stream:
            print(chunk)
            sys.stdout.flush()
        print("\n")

    except Exception as e:
        print(f"Streaming request failed: {e}")


if __name__ == "__main__":
    main()
