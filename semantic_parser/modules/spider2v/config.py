"""Spider2-V Module Configuration

Configuration settings for the Spider2-V module including API credentials,
BigQuery settings, and execution parameters.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "https://ovalnairr.openai.azure.com/")
AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "o3")

# BigQuery Configuration
BIGQUERY_PROJECT = os.getenv("BIGQUERY_PROJECT", "cs224v-recursive-parsing")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/CT-Engine/spider-471218-77fec1ca4fcf.json"
)

# Execution Configuration
OUTPUT_DIR = "/tmp/spider2v_output"
MAX_CONCURRENT_TASKS = 5
MAX_DEPTH = 5  # For DecomposeAgent
MAX_SUBTASKS = 5  # For DecomposeAgent

# Results Configuration
RESULTS_DIR = "results/spider2v"
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
