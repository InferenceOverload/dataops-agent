"""
Simple test script to verify Bedrock connectivity
"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from infrastructure.llm.llm_factory import create_llm

print("Creating Bedrock LLM client...")
llm = create_llm()

print(f"LLM client created: {type(llm)}")
print("\nTesting simple invocation...")

try:
    response = llm.invoke("What is 2+2? Answer in one word.")
    print(f"\nResponse: {response.content}")
    print("\n✓ Bedrock connection successful!")
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
