#!/usr/bin/env python3
"""Quick test of a single action to verify BigQuery connectivity"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from semantic_parser.llm_client import AzureOpenAIClient
from semantic_parser.modules.spider2v.actions import InspectSchema
from semantic_parser.modules.spider2v.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    BIGQUERY_PROJECT,
    GOOGLE_APPLICATION_CREDENTIALS
)
from google.cloud import bigquery
from google.oauth2 import service_account

print("\n" + "="*60)
print("TESTING SINGLE ACTION - InspectSchema")
print("="*60)

# Setup
print("\n[1/3] Setting up clients...")
print(f"  BigQuery Project: {BIGQUERY_PROJECT}")
print(f"  Service Account: {GOOGLE_APPLICATION_CREDENTIALS}")

# Initialize BigQuery client
credentials = service_account.Credentials.from_service_account_file(
    GOOGLE_APPLICATION_CREDENTIALS
)
bq_client = bigquery.Client(credentials=credentials, project=BIGQUERY_PROJECT)
print(f"  ✓ BigQuery client initialized")

# Initialize LLM client
llm_client = AzureOpenAIClient(
    api_key=AZURE_OPENAI_API_KEY,
    deployment_name=AZURE_OPENAI_DEPLOYMENT
)
print(f"  ✓ LLM client initialized")

# Create action
print("\n[2/3] Creating InspectSchema action...")
action = InspectSchema(llm_client=llm_client, bigquery_client=bq_client)
print(f"  ✓ Action created: {action.name}")

# Test with a public dataset
print("\n[3/3] Testing with public dataset...")
dataset_name = "bigquery-public-data.covid19_open_data"
print(f"  Testing dataset: {dataset_name}")

try:
    result = action.execute(dataset_name=dataset_name)

    if result.success:
        print(f"\n✅ SUCCESS!")
        print(f"  Tables found: {result.metadata.get('table_count', 'N/A')}")
        print(f"  Total columns: {result.metadata.get('total_columns', 'N/A')}")
        print(f"\n  Schema preview (first 200 chars):")
        print(f"  {result.result[:200]}...")
    else:
        print(f"\n❌ FAILED")
        print(f"  Error: {result.error}")

except Exception as e:
    print(f"\n❌ EXCEPTION")
    print(f"  Error: {str(e)}")

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60 + "\n")
