#!/usr/bin/env python3
"""
Spider2-V Experiment Runner

Runs experiments on Spider2-V tasks using DecomposeAgent.
Collects metrics for research paper.

Usage:
    python experiments/run_spider2v_experiment.py [num_tasks] [experiment_name]

Examples:
    python experiments/run_spider2v_experiment.py 5 pilot_test
    python experiments/run_spider2v_experiment.py 10 bigquery_test
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from semantic_parser.llm_client import AzureOpenAIClient
from semantic_parser.src.decompose.decompose_agent import DecomposeAgent
from semantic_parser.modules.spider2v import create_action_registry
from semantic_parser.modules.spider2v.task_loader import get_mock_tasks, load_bigquery_examples, load_spider2v_tasks
from semantic_parser.modules.spider2v.evaluate import ExperimentRunner
from semantic_parser.modules.spider2v.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    BIGQUERY_PROJECT,
    MAX_DEPTH,
    MAX_SUBTASKS,
    GOOGLE_APPLICATION_CREDENTIALS
)


async def main():
    """Run Spider2-V experiment with DecomposeAgent"""

    print("\n" + "="*60)
    print("SPIDER2-V EXPERIMENT RUNNER")
    print("="*60)

    # 1. Setup LLM client
    print("\n[1/6] Initializing LLM client...")
    llm_client = AzureOpenAIClient(
        api_key=AZURE_OPENAI_API_KEY,
        deployment_name=AZURE_OPENAI_DEPLOYMENT
    )
    print(f"  ✓ Using deployment: {AZURE_OPENAI_DEPLOYMENT}")

    # 2. Create action registry with BigQuery
    print("\n[2/6] Creating action registry with BigQuery...")
    print(f"  ✓ BigQuery project: {BIGQUERY_PROJECT}")
    print(f"  ✓ Service account: {GOOGLE_APPLICATION_CREDENTIALS}")

    action_registry = create_action_registry(
        openai_api_key=AZURE_OPENAI_API_KEY,
        bigquery_project=BIGQUERY_PROJECT,
        service_account_path=GOOGLE_APPLICATION_CREDENTIALS
    )
    print(f"  ✓ Registered {len(action_registry.get_all_actions())} actions")

    # 3. Create DecomposeAgent
    print("\n[3/6] Creating DecomposeAgent...")
    agent = DecomposeAgent(
        llm_client=llm_client,
        action_registry=action_registry,
        max_depth=MAX_DEPTH,
        max_subtasks=MAX_SUBTASKS,
        verbose=True
    )
    print(f"  ✓ Max depth: {MAX_DEPTH}")
    print(f"  ✓ Max subtasks: {MAX_SUBTASKS}")

    # 4. Load tasks
    print("\n[4/6] Loading tasks...")
    n_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    use_real_data = '--real' in sys.argv

    if use_real_data:
        print(f"  ✓ Loading {n_tasks} real BigQuery tasks from Spider2-V dataset...")
        dataset_path = "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/spider2v_dataset"
        tasks = load_spider2v_tasks(
            n=n_tasks,
            split="test_verbose",
            app_filter="bigquery",
            dataset_path=dataset_path
        )
    else:
        print(f"  ✓ Loading {n_tasks} mock tasks...")
        tasks = get_mock_tasks(n=n_tasks)

    print(f"  ✓ Loaded {len(tasks)} tasks")

    # 5. Create experiment runner
    print("\n[5/6] Setting up experiment runner...")
    runner = ExperimentRunner(agent=agent, max_concurrent=3, verbose=True)

    # 6. Run experiment
    experiment_name = sys.argv[2] if len(sys.argv) > 2 and '--real' not in sys.argv[2] else "pilot_test"
    print(f"\n[6/6] Running experiment: {experiment_name}")

    results = await runner.run_experiment(tasks, experiment_name=experiment_name)

    # 7. Print LaTeX table row
    success_rate = results['summary']['success_rate']
    print(f"\n{'='*60}")
    print("LATEX TABLE ROW:")
    print(f"{'='*60}")
    print(f"\\textbf{{CT-Spider2V}} & \\textbf{{{success_rate:.1f}\\%}} \\\\")
    print(f"{'='*60}\n")

    print("\n✅ Experiment complete!")
    print(f"Success rate: {success_rate:.1f}%")
    print(f"Total tasks: {results['summary']['total_tasks']}")
    print(f"Successful: {results['summary']['successful']}")
    print(f"Failed: {results['summary']['failed']}")

    return results


if __name__ == "__main__":
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)

    asyncio.run(main())
