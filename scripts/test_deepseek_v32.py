#!/usr/bin/env python3
"""
Test DeepSeek v3.2 API
"""

from openai import OpenAI

api_key = "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"
model = "deepseek-ai/deepseek-v3.2"

print(f"🧪 Testing {model}...")
print(f"API Key: {api_key[:30]}...{api_key[-10:]}")
print("-" * 80)

try:
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    print("Sending test message with reasoning enabled...")

    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say 'Hello LiveMirror!' in exactly 3 words."}],
        temperature=1,
        top_p=0.95,
        max_tokens=500,
        extra_body={"chat_template_kwargs": {"thinking": True}},
        stream=True
    )

    print("\n📝 Response:")
    print("-" * 80)

    reasoning_output = ""
    content_output = ""

    for chunk in completion:
        if not getattr(chunk, "choices", None):
            continue

        reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
        if reasoning:
            reasoning_output += reasoning
            print(f"[REASONING] {reasoning}", end="", flush=True)

        if chunk.choices and chunk.choices[0].delta.content is not None:
            content = chunk.choices[0].delta.content
            content_output += content
            print(content, end="", flush=True)

    print("\n" + "-" * 80)
    print("\n✅ SUCCESS! API is working properly")
    print(f"\nReasoning Length: {len(reasoning_output)} chars")
    print(f"Content Length: {len(content_output)} chars")
    print(f"\nFinal Response:\n{content_output}")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    print(f"Type: {type(e).__name__}")

    if "401" in str(e) or "Unauthorized" in str(e):
        print("→ Authentication failed - Check API key")
    elif "404" in str(e):
        print("→ Model not found - Check model name")
    elif "429" in str(e):
        print("→ Rate limited - Too many requests")
    elif "timeout" in str(e).lower():
        print("→ Request timeout - Server is slow or overloaded")
    else:
        print(f"→ {str(e)}")
