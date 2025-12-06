"""Experiment Evaluation Framework for Spider2-V

Utilities for running experiments on Spider2-V tasks and collecting metrics.
Supports both DecomposeAgent and ReACTEngine.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from .task_loader import Spider2VTask
from .config import RESULTS_DIR, MAX_CONCURRENT_TASKS


@dataclass
class TaskResult:
    """Result of executing a single task"""
    task_id: str
    instruction: str
    success: bool
    result: Optional[str]
    error: Optional[str]
    duration_seconds: float
    total_steps: int
    actions_used: List[str]
    timestamp: str
    metadata: Dict[str, Any]


class ExperimentRunner:
    """Run experiments on Spider2-V tasks"""

    def __init__(
        self,
        agent,  # Can be DecomposeAgent or ReACTEngine
        max_concurrent: int = MAX_CONCURRENT_TASKS,
        verbose: bool = True
    ):
        """Initialize experiment runner

        Args:
            agent: DecomposeAgent or ReACTEngine instance
            max_concurrent: Maximum number of concurrent tasks (default: 5)
            verbose: Whether to print progress (default: True)
        """
        self.agent = agent
        self.max_concurrent = max_concurrent
        self.verbose = verbose

    async def run_task(self, task: Spider2VTask) -> TaskResult:
        """Run a single task and return results

        Args:
            task: Spider2VTask to execute

        Returns:
            TaskResult with execution details
        """
        if self.verbose:
            print(f"Running task {task.task_id}: {task.instruction[:60]}...")

        start_time = time.time()

        try:
            # For DecomposeAgent (primary)
            if hasattr(self.agent, 'solve'):
                trace = await self.agent.solve(task.instruction)

                success = trace.error is None
                result = trace.result
                error = trace.error
                total_steps = trace.depth
                actions_used = self._extract_actions_from_trace(trace)

            # For ReACTEngine (fallback for compatibility)
            elif hasattr(self.agent, 'parse'):
                trace = self.agent.parse(
                    query=task.instruction,
                    target_format="SQL",
                    initial_context={"task_id": task.task_id}
                )

                success = trace.is_complete
                result = trace.final_output
                error = None
                total_steps = trace.get_step_count()
                actions_used = [step.action.action_name for step in trace.steps]

            else:
                raise ValueError("Agent must be DecomposeAgent or ReACTEngine")

            duration = time.time() - start_time

            return TaskResult(
                task_id=task.task_id,
                instruction=task.instruction,
                success=success,
                result=str(result) if result else None,
                error=error,
                duration_seconds=duration,
                total_steps=total_steps,
                actions_used=actions_used,
                timestamp=datetime.now().isoformat(),
                metadata={
                    "category": task.category,
                    "tools": task.tools,
                    "has_gold_output": task.gold_output is not None
                }
            )

        except Exception as e:
            duration = time.time() - start_time
            return TaskResult(
                task_id=task.task_id,
                instruction=task.instruction,
                success=False,
                result=None,
                error=str(e),
                duration_seconds=duration,
                total_steps=0,
                actions_used=[],
                timestamp=datetime.now().isoformat(),
                metadata={"category": task.category, "tools": task.tools}
            )

    def _extract_actions_from_trace(self, trace) -> List[str]:
        """Extract action names from decompose trace recursively

        Args:
            trace: DecomposeTrace object

        Returns:
            List of action names used
        """
        actions = []
        if trace.action_used:
            actions.append(trace.action_used)
        if trace.subtasks:
            for subtask in trace.subtasks:
                actions.extend(self._extract_actions_from_trace(subtask))
        return actions

    async def run_experiment(
        self,
        tasks: List[Spider2VTask],
        experiment_name: str = "spider2v_experiment"
    ) -> Dict[str, Any]:
        """Run experiment on multiple tasks

        Args:
            tasks: List of Spider2VTask objects to execute
            experiment_name: Name for this experiment run

        Returns:
            Dict with 'results' (list of TaskResult) and 'summary' (metrics)
        """
        print(f"\n{'='*60}")
        print(f"Running experiment: {experiment_name}")
        print(f"Total tasks: {len(tasks)}")
        print(f"Max concurrent: {self.max_concurrent}")
        print(f"{'='*60}\n")

        # Run tasks with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def run_with_semaphore(task):
            async with semaphore:
                return await self.run_task(task)

        results = await asyncio.gather(*[run_with_semaphore(task) for task in tasks])

        # Calculate metrics
        summary = self._calculate_summary(results, experiment_name)

        # Save results
        self._save_results(results, summary, experiment_name)

        # Print summary
        self._print_summary(summary)

        return {
            "results": results,
            "summary": summary
        }

    def _calculate_summary(self, results: List[TaskResult], experiment_name: str) -> Dict[str, Any]:
        """Calculate summary statistics from results

        Args:
            results: List of TaskResult objects
            experiment_name: Name of the experiment

        Returns:
            Dict with summary metrics
        """
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        avg_duration = sum(r.duration_seconds for r in results) / total if total > 0 else 0
        avg_steps = sum(r.total_steps for r in results) / total if total > 0 else 0

        # Action frequency
        all_actions = []
        for r in results:
            all_actions.extend(r.actions_used)
        action_counts = {}
        for action in all_actions:
            action_counts[action] = action_counts.get(action, 0) + 1

        # Error types
        error_types = {}
        for r in results:
            if r.error:
                error_type = r.error.split(':')[0] if ':' in r.error else 'Unknown'
                error_types[error_type] = error_types.get(error_type, 0) + 1

        return {
            "experiment_name": experiment_name,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_duration_seconds": avg_duration,
            "avg_steps": avg_steps,
            "action_counts": action_counts,
            "error_types": error_types
        }

    def _save_results(self, results: List[TaskResult], summary: Dict, experiment_name: str):
        """Save results to files in multiple formats

        Args:
            results: List of TaskResult objects
            summary: Summary metrics dict
            experiment_name: Name of the experiment
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save detailed results as JSON
        results_path = Path(RESULTS_DIR) / f"{experiment_name}_{timestamp}_results.json"
        with open(results_path, 'w') as f:
            json.dump([asdict(r) for r in results], f, indent=2)

        # Save summary
        summary_path = Path(RESULTS_DIR) / f"{experiment_name}_{timestamp}_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        # Save CSV for easy viewing
        import pandas as pd
        df = pd.DataFrame([asdict(r) for r in results])
        csv_path = Path(RESULTS_DIR) / f"{experiment_name}_{timestamp}_results.csv"
        df.to_csv(csv_path, index=False)

        print(f"\nResults saved:")
        print(f"  JSON: {results_path}")
        print(f"  Summary: {summary_path}")
        print(f"  CSV: {csv_path}")

    def _print_summary(self, summary: Dict):
        """Print experiment summary to console

        Args:
            summary: Summary metrics dict
        """
        print(f"\n{'='*60}")
        print(f"EXPERIMENT SUMMARY: {summary['experiment_name']}")
        print(f"{'='*60}")
        print(f"Total Tasks:       {summary['total_tasks']}")
        print(f"Successful:        {summary['successful']}")
        print(f"Failed:            {summary['failed']}")
        print(f"Success Rate:      {summary['success_rate']:.1f}%")
        print(f"Avg Duration:      {summary['avg_duration_seconds']:.2f}s")
        print(f"Avg Steps:         {summary['avg_steps']:.1f}")

        if summary['action_counts']:
            print(f"\nAction Usage:")
            for action, count in sorted(summary['action_counts'].items(), key=lambda x: -x[1]):
                print(f"  {action}: {count}")

        if summary['error_types']:
            print(f"\nError Types:")
            for error_type, count in sorted(summary['error_types'].items(), key=lambda x: -x[1]):
                print(f"  {error_type}: {count}")

        print(f"{'='*60}\n")
