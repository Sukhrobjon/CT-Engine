#!/usr/bin/env python3
"""
Test Task 6 end-to-end with all fixes applied.

Task 6: Count austin bike stations that are active, save to CSV
- Uses public data (no dataset creation needed)
- Tests type mismatch fix (ExecuteQuery returns DataFrame)
- Tests SaveToCSV action
"""

import os
import sys
from google.cloud import bigquery
from google.oauth2 import service_account

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from semantic_parser.modules.spider2v.task_loader import Spider2VDatasetLoader
from semantic_parser.src.decompose.decompose_agent import DecomposeAgent
from semantic_parser.modules.spider2v.actions import SPIDER2V_ACTIONS
from semantic_parser.llm_client import AzureOpenAIClient

def test_task6():
    print("=" * 80)
    print("TASK 6 END-TO-END TEST")
    print("=" * 80)

    # Load Task 6
    dataset_path = "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/spider2v_dataset"
    loader = Spider2VDatasetLoader(dataset_path=dataset_path)
    task = loader.load_single_task("a954c45e-fb59-4231-a052-a7f74dc16bf1", app_name="bigquery")

    if not task:
        print("❌ Could not load task 6")
        return False

    print(f"\n📋 Task: {task['instruction'][:200]}...")
    print(f"   Full instruction length: {len(task['instruction'])} chars")

    # Setup BigQuery client
    SERVICE_ACCOUNT_PATH = "spider-471218-77fec1ca4fcf.json"
    PROJECT_ID = "cs224v-recursive-parsing"

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH,
        scopes=["https://www.googleapis.com/auth/bigquery"],
    )
    bq_client = bigquery.Client(credentials=credentials, project=PROJECT_ID)

    # Setup LLM client
    llm_client = AzureOpenAIClient()

    # Initialize actions with clients
    action_classes = SPIDER2V_ACTIONS
    actions = []
    for action_class in action_classes:
        action_name = action_class.__name__
        if action_name == "InspectSchema":
            actions.append(action_class(bigquery_client=bq_client, llm_client=llm_client))
        elif action_name == "GenerateSQL":
            actions.append(action_class(llm_client=llm_client))
        elif action_name == "ExecuteQuery":
            actions.append(action_class(bigquery_client=bq_client, llm_client=llm_client))
        elif action_name == "CreateFile":
            actions.append(action_class())
        elif action_name == "SaveToCSV":
            actions.append(action_class())
        elif action_name == "ClickButton":
            actions.append(action_class())
        elif action_name == "Finish":
            actions.append(action_class(llm_client=llm_client))
        else:
            actions.append(action_class())

    # Create DecomposeAgent
    agent = DecomposeAgent(
        client=llm_client,
        actions=actions,
        bigquery_client=bq_client,
        max_depth=5,
        enable_type_checking=True
    )

    print("\n🚀 Running task through DecomposeAgent...")
    print("-" * 80)

    # Execute task
    result = agent.execute(task['instruction'])

    print("-" * 80)
    print("\n📊 RESULT:")
    print(f"  Success: {result.success}")

    if result.success:
        print(f"  ✅ Result: {result.result[:500]}..." if len(str(result.result)) > 500 else f"  ✅ Result: {result.result}")
        print(f"\n  Metadata: {result.metadata}")

        # Check if CSV was created
        csv_path = "/tmp/spider2v_output/answer.csv"
        if os.path.exists(csv_path):
            print(f"\n  ✅ CSV file created at {csv_path}")
            with open(csv_path, 'r') as f:
                content = f.read()
                print(f"  CSV content preview:\n{content[:200]}")
        else:
            print(f"\n  ⚠️  CSV file not found at {csv_path}")
            # Check what files were created
            output_dir = "/tmp/spider2v_output"
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                print(f"  Files in output dir: {files}")
    else:
        print(f"  ❌ Error: {result.error}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return result.success

if __name__ == "__main__":
    success = test_task6()
    sys.exit(0 if success else 1)
