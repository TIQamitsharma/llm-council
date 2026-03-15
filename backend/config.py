"""Configuration for the LLM Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Council members - list of OpenRouter model identifiers
COUNCIL_MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.5-pro-preview",
    "anthropic/claude-sonnet-4-5",
    "x-ai/grok-3",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "google/gemini-2.5-pro-preview"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
