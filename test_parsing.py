#!/usr/bin/env python3
"""
Quick test script to verify LLM response parsing with the current model.
Run with: python test_parsing.py
"""

import logging
logging.basicConfig(level=logging.INFO)

from agents.graph import create_llm, parse_json_response
from agents.prompts import REVIEW_SYSTEM_PROMPT, get_review_prompt
from models.schemas import CodeReview
from langchain_core.messages import HumanMessage, SystemMessage
from config import get_config

def test_parse():
    config = get_config()
    print(f"\n{'='*60}")
    print(f"Testing with model: {config.model_name}")
    print(f"{'='*60}\n")
    
    # Simple test code
    test_code = """
def greet(name):
    print("Hello, " + name)

greet("World")
"""
    
    llm = create_llm()
    
    messages = [
        SystemMessage(content=REVIEW_SYSTEM_PROMPT),
        HumanMessage(content=get_review_prompt(test_code)),
    ]
    
    print("Calling LLM...")
    response = llm.invoke(messages)
    
    print(f"\n{'='*60}")
    print("FULL RAW RESPONSE:")
    print(f"{'='*60}")
    print(response.content)
    print(f"{'='*60}\n")
    
    # Try parsing
    result = parse_json_response(response.content, CodeReview)
    
    if result:
        print("\n✅ PARSING SUCCEEDED!")
        print(f"Issues: {result.get('issues', [])}")
        print(f"Severity: {result.get('severity', 'unknown')}")
        print(f"Summary: {result.get('summary', 'none')}")
    else:
        print("\n❌ PARSING FAILED - Check logs above for details")

if __name__ == "__main__":
    test_parse()
