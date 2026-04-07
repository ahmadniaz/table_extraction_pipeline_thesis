"""
Minimal configuration for the thesis evaluation system.
Database connection lives in db/database.py.
This file holds API keys and service configuration only.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- AI service API keys ---
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")

# --- Google Document AI ---
GOOGLE_CLOUD_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
GOOGLE_DOCAI_PROCESSOR_ID = os.environ.get("GOOGLE_DOCAI_PROCESSOR_ID") or os.environ.get("DOCAI_PROCESSOR_ID")
DOCAI_PROJECT_ID = os.environ.get("DOCAI_PROJECT_ID")
