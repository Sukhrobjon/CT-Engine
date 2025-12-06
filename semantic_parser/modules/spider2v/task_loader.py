"""Task Loading Utilities for Spider2-V

Utilities for loading and creating Spider2-V tasks for experiments.
Supports both mock tasks for testing and loading from real Spider2-V dataset.
"""

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Spider2VTask:
    """Represents a Spider2-V task"""
    task_id: str
    instruction: str
    category: str  # "warehousing", "analytics", "integration", "gui"
    tools: List[str]  # ["BigQuery", "dbt", "Airbyte", "Selenium"]
    visual_context: Optional[str] = None  # Path to screenshot
    gold_output: Optional[str] = None  # Expected output for evaluation


def get_mock_tasks(n: int = 5) -> List[Spider2VTask]:
    """Create mock Spider2-V tasks for testing

    Args:
        n: Number of mock tasks to return (default: 5)

    Returns:
        List of Spider2VTask objects
    """
    tasks = [
        Spider2VTask(
            task_id="test_001",
            instruction="Inspect the schema of the bigquery-public-data.covid19_open_data dataset",
            category="warehousing",
            tools=["BigQuery"],
            gold_output="Schema with table information"
        ),
        Spider2VTask(
            task_id="test_002",
            instruction="Generate SQL to find the total number of COVID-19 cases worldwide on 2020-04-15 from bigquery-public-data.covid19_open_data.covid19_open_data",
            category="analytics",
            tools=["BigQuery"],
            gold_output="SQL query with SUM and WHERE date clause"
        ),
        Spider2VTask(
            task_id="test_003",
            instruction="Create a dbt model file named 'customer_metrics.sql' that calculates customer lifetime value",
            category="warehousing",
            tools=["dbt"],
            gold_output="File created at customer_metrics.sql"
        ),
        Spider2VTask(
            task_id="test_004",
            instruction="Execute a query to count total rows in bigquery-public-data.austin_bikeshare.bikeshare_stations",
            category="analytics",
            tools=["BigQuery"],
            gold_output="Query executed successfully with count result"
        ),
        Spider2VTask(
            task_id="test_005",
            instruction="Click the 'Run Query' button in the BigQuery interface",
            category="gui",
            tools=["Selenium"],
            gold_output="Clicked button: Run Query"
        ),
    ]
    return tasks[:n]


def load_tasks_from_json(filepath: str) -> List[Spider2VTask]:
    """Load Spider2-V tasks from JSON file

    Args:
        filepath: Path to JSON file containing task definitions

    Returns:
        List of Spider2VTask objects
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    tasks = []

    # Handle different JSON formats
    if isinstance(data, dict) and "examples" in data:
        # Format from bigquery_examples.json
        examples = data["examples"]
    elif isinstance(data, list):
        # Direct list of tasks
        examples = data
    else:
        examples = [data]

    for idx, item in enumerate(examples):
        # Extract fields with fallbacks
        task_id = item.get('task_id', f"task_{idx:03d}")
        instruction = item.get('instruction', item.get('verbose_instruction', ''))
        category = item.get('category', item.get('task_type', 'unknown'))
        tools = item.get('tools', [])

        # Determine tools from tables if not specified
        if not tools and 'tables' in item:
            if any('bigquery' in str(t).lower() for t in item['tables']):
                tools = ['BigQuery']

        tasks.append(Spider2VTask(
            task_id=task_id,
            instruction=instruction,
            category=category,
            tools=tools if tools else ['BigQuery'],
            visual_context=item.get('visual_context'),
            gold_output=item.get('gold_output', item.get('expected_result'))
        ))

    return tasks


def load_bigquery_examples(n: Optional[int] = None) -> List[Spider2VTask]:
    """Load tasks from the BigQuery examples file in recursive-parsing repo

    Args:
        n: Maximum number of tasks to load (None for all)

    Returns:
        List of Spider2VTask objects
    """
    bigquery_examples_path = "/Users/sukhrobjongolibboev/Desktop/Stanford/CS224VFall2025/final project/recursive-parsing/bigquery_examples.json"

    try:
        tasks = load_tasks_from_json(bigquery_examples_path)
        if n is not None:
            tasks = tasks[:n]
        return tasks
    except FileNotFoundError:
        print(f"Warning: Could not find {bigquery_examples_path}")
        print("Falling back to mock tasks")
        return get_mock_tasks(n or 5)


# ============================================================================
# Real Spider2-V Dataset Loader
# ============================================================================

class Spider2VDatasetLoader:
    """
    Load tasks from the official Spider2-V dataset.

    Dataset structure:
    spider2v_dataset/
        evaluation_examples/
            test_verbose.json       # Tasks with step-by-step instructions
            test_abstract.json      # Tasks with high-level goals only
            test_all.json           # All 494 tasks
            test_account.json       # Tasks requiring real accounts
            test_non_account.json   # Tasks without account requirements
            examples/
                bigquery/
                    <task_id>/
                        <task_id>.json
                dbt/
                excel/
                ...
    """

    def __init__(self, dataset_path: Optional[str] = None):
        """
        Initialize the dataset loader.

        Args:
            dataset_path: Path to spider2v_dataset directory.
                         Defaults to ../spider2v_dataset relative to this file.
        """
        if dataset_path is None:
            # Auto-detect dataset path relative to this file
            current_dir = Path(__file__).parent.parent.parent.parent
            dataset_path = current_dir / "spider2v_dataset"

        self.dataset_path = Path(dataset_path)
        self.examples_dir = self.dataset_path / "evaluation_examples"
        self.examples_data_dir = self.examples_dir / "examples"

        if not self.dataset_path.exists():
            raise FileNotFoundError(
                f"Spider2-V dataset not found at {self.dataset_path}. "
                f"Please clone it from https://github.com/xlang-ai/Spider2-V"
            )

    def load_task_split(self, split: str = "test_verbose") -> List[Dict]:
        """
        Load tasks from a specific split.

        Args:
            split: One of:
                - "test_verbose": Tasks with step-by-step instructions (recommended)
                - "test_abstract": Tasks with high-level goals only
                - "test_all": All 494 tasks
                - "test_account": Tasks requiring real accounts
                - "test_non_account": Tasks without account requirements

        Returns:
            List of task dictionaries with full Spider2-V format
        """
        split_file = self.examples_dir / f"{split}.json"

        if not split_file.exists():
            raise FileNotFoundError(f"Split file not found: {split_file}")

        with open(split_file, 'r') as f:
            split_data = json.load(f)

        # split_data is a dict like {"bigquery": ["task_id1", ...], "dbt": [...]}
        all_tasks = []

        for app_name, task_ids in split_data.items():
            for task_id in task_ids:
                # Load full task JSON
                task_file = self.examples_data_dir / app_name / task_id / f"{task_id}.json"

                if task_file.exists():
                    with open(task_file, 'r') as f:
                        task_data = json.load(f)
                    task_data['app_name'] = app_name
                    all_tasks.append(task_data)
                else:
                    print(f"Warning: Task file not found: {task_file}")

        return all_tasks

    def load_single_task(self, task_id: str, app_name: Optional[str] = None) -> Optional[Dict]:
        """
        Load a specific task by ID.

        Args:
            task_id: UUID of the task
            app_name: Optional app name (bigquery, dbt, etc.). If not provided, searches all apps.

        Returns:
            Task dictionary or None if not found
        """
        if app_name:
            # Search specific app
            task_file = self.examples_data_dir / app_name / task_id / f"{task_id}.json"
            if task_file.exists():
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                task_data['app_name'] = app_name
                return task_data
        else:
            # Search all apps
            for app_dir in self.examples_data_dir.iterdir():
                if app_dir.is_dir():
                    task_file = app_dir / task_id / f"{task_id}.json"
                    if task_file.exists():
                        with open(task_file, 'r') as f:
                            task_data = json.load(f)
                        task_data['app_name'] = app_dir.name
                        return task_data

        return None

    def load_bigquery_tasks(self, n: Optional[int] = None, verbose_only: bool = True) -> List[Dict]:
        """
        Load BigQuery tasks specifically.

        Args:
            n: Maximum number of tasks to load (None for all)
            verbose_only: If True, only load tasks with verbose instructions

        Returns:
            List of BigQuery task dictionaries
        """
        if verbose_only:
            split_file = self.examples_dir / "test_verbose.json"
        else:
            split_file = self.examples_dir / "test_all.json"

        with open(split_file, 'r') as f:
            split_data = json.load(f)

        bigquery_task_ids = split_data.get("bigquery", [])

        if n is not None:
            bigquery_task_ids = bigquery_task_ids[:n]

        tasks = []
        for task_id in bigquery_task_ids:
            task = self.load_single_task(task_id, app_name="bigquery")
            if task:
                tasks.append(task)

        return tasks

    def get_dataset_stats(self) -> Dict:
        """
        Get statistics about the dataset.

        Returns:
            Dictionary with counts by app, split, etc.
        """
        stats = {
            "apps": {},
            "splits": {}
        }

        # Count by split
        for split_name in ["test_verbose", "test_abstract", "test_all", "test_account", "test_non_account"]:
            split_file = self.examples_dir / f"{split_name}.json"
            if split_file.exists():
                with open(split_file, 'r') as f:
                    split_data = json.load(f)
                total = sum(len(task_ids) for task_ids in split_data.values())
                stats["splits"][split_name] = total

                # Count by app
                if split_name == "test_all":
                    stats["apps"] = {app: len(ids) for app, ids in split_data.items()}

        return stats


def load_spider2v_tasks(
    n: Optional[int] = None,
    split: str = "test_verbose",
    app_filter: Optional[str] = None,
    dataset_path: Optional[str] = None
) -> List[Spider2VTask]:
    """
    Convenience function to load Spider2-V tasks in the Spider2VTask format.

    Args:
        n: Maximum number of tasks to load
        split: Dataset split to use ("test_verbose", "test_abstract", etc.)
        app_filter: Optional app name to filter by ("bigquery", "dbt", etc.)
        dataset_path: Optional path to dataset directory

    Returns:
        List of Spider2VTask objects
    """
    loader = Spider2VDatasetLoader(dataset_path)

    if app_filter == "bigquery":
        raw_tasks = loader.load_bigquery_tasks(n=n, verbose_only=(split == "test_verbose"))
    else:
        raw_tasks = loader.load_task_split(split)
        if app_filter:
            raw_tasks = [t for t in raw_tasks if t.get('app_name') == app_filter]
        if n is not None:
            raw_tasks = raw_tasks[:n]

    # Convert to Spider2VTask format
    tasks = []
    for task_data in raw_tasks:
        # Determine if instruction is verbose or abstract
        instruction = task_data.get('instruction', '')
        is_verbose = 'verbose' in task_data.get('tags', [])

        # Extract category from tags
        tags = task_data.get('tags', [])
        if 'data_warehousing' in tags:
            category = 'warehousing'
        elif 'gui' in tags:
            category = 'gui'
        elif 'analytics' in tags or 'data_analytics' in tags:
            category = 'analytics'
        else:
            category = task_data.get('app_name', 'unknown')

        tasks.append(Spider2VTask(
            task_id=task_data['id'],
            instruction=instruction,
            category=category,
            tools=task_data.get('related_apps', []),
            visual_context=None,  # Could extract from task config
            gold_output=None  # Could extract from evaluator
        ))

    return tasks
