#!/usr/bin/env python3
"""
Analyze Spider2-V Experiment Results

Analyzes experiment results and generates LaTeX tables for the research paper.

Usage:
    python experiments/analyze_results.py <results.json>

Example:
    python experiments/analyze_results.py results/spider2v/pilot_test_20250128_143022_results.json
"""

import json
import sys
from pathlib import Path
from typing import Dict, List


def load_results(results_path: str) -> Dict:
    """Load results from JSON file"""
    with open(results_path, 'r') as f:
        return json.load(f)


def analyze_errors(results: List[Dict]) -> Dict:
    """Analyze error patterns"""
    errors = {}
    for r in results:
        if not r['success'] and r['error']:
            error_msg = r['error'][:100]  # First 100 chars
            errors[error_msg] = errors.get(error_msg, 0) + 1
    return errors


def analyze_by_category(results: List[Dict]) -> Dict:
    """Analyze success by task category"""
    categories = {}
    for r in results:
        cat = r['metadata'].get('category', 'unknown')
        if cat not in categories:
            categories[cat] = {'total': 0, 'success': 0}
        categories[cat]['total'] += 1
        if r['success']:
            categories[cat]['success'] += 1

    # Calculate rates
    for cat in categories:
        total = categories[cat]['total']
        success = categories[cat]['success']
        categories[cat]['success_rate'] = (success / total * 100) if total > 0 else 0

    return categories


def analyze_action_usage(results: List[Dict]) -> Dict:
    """Analyze which actions were used most frequently"""
    action_counts = {}
    for r in results:
        for action in r.get('actions_used', []):
            action_counts[action] = action_counts.get(action, 0) + 1
    return dict(sorted(action_counts.items(), key=lambda x: -x[1]))


def generate_latex_table(summary: Dict, categories: Dict) -> str:
    """Generate LaTeX table for paper"""
    lines = []
    lines.append("\\begin{table}[h]")
    lines.append("\\centering")
    lines.append("\\begin{tabular}{lcc}")
    lines.append("\\toprule")
    lines.append("\\textbf{Method} & \\textbf{Success Rate} & \\textbf{Tasks} \\\\")
    lines.append("\\midrule")
    lines.append(f"CT-Spider2V & {summary['success_rate']:.1f}\\% & {summary['total_tasks']} \\\\")

    if categories:
        lines.append("\\midrule")
        lines.append("\\multicolumn{3}{l}{\\textit{By Category:}} \\\\")
        for cat, data in sorted(categories.items()):
            lines.append(f"\\quad {cat.capitalize()} & {data['success_rate']:.1f}\\% & {data['total']} \\\\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append(f"\\caption{{CT-Spider2V Results on {summary['total_tasks']} Tasks}}")
    lines.append("\\label{tab:spider2v_results}")
    lines.append("\\end{table}")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_results.py <results.json>")
        print("\nExample:")
        print("  python analyze_results.py results/spider2v/pilot_test_20250128_143022_results.json")
        sys.exit(1)

    results_path = sys.argv[1]
    summary_path = results_path.replace('_results.json', '_summary.json')

    if not Path(results_path).exists():
        print(f"Error: File not found: {results_path}")
        sys.exit(1)

    print("\n" + "="*60)
    print("SPIDER2-V RESULTS ANALYSIS")
    print("="*60)

    # Load data
    print(f"\nLoading results from: {results_path}")
    results = load_results(results_path)
    summary = load_results(summary_path) if Path(summary_path).exists() else {}

    print(f"  ✓ Loaded {len(results)} task results")

    # High-level summary
    print("\n" + "="*60)
    print("OVERALL RESULTS")
    print("="*60)
    if summary:
        print(f"Experiment: {summary.get('experiment_name', 'N/A')}")
        print(f"Timestamp: {summary.get('timestamp', 'N/A')}")
        print(f"Total Tasks: {summary.get('total_tasks', len(results))}")
        print(f"Successful: {summary.get('successful', sum(1 for r in results if r['success']))}")
        print(f"Failed: {summary.get('failed', sum(1 for r in results if not r['success']))}")
        print(f"Success Rate: {summary.get('success_rate', 0):.1f}%")
        print(f"Avg Duration: {summary.get('avg_duration_seconds', 0):.2f}s")
        print(f"Avg Steps: {summary.get('avg_steps', 0):.1f}")

    # Error analysis
    print("\n" + "="*60)
    print("ERROR BREAKDOWN")
    print("="*60)
    errors = analyze_errors(results)
    if errors:
        for error_msg, count in sorted(errors.items(), key=lambda x: -x[1])[:5]:
            print(f"  [{count}x] {error_msg}")
    else:
        print("  ✓ No errors!")

    # Category analysis
    print("\n" + "="*60)
    print("SUCCESS BY CATEGORY")
    print("="*60)
    categories = analyze_by_category(results)
    for cat, data in sorted(categories.items()):
        print(f"  {cat.capitalize()}: {data['success']}/{data['total']} ({data['success_rate']:.1f}%)")

    # Action usage
    print("\n" + "="*60)
    print("ACTION USAGE")
    print("="*60)
    action_usage = analyze_action_usage(results)
    for action, count in list(action_usage.items())[:10]:
        print(f"  {action}: {count}x")

    # Generate LaTeX
    print("\n" + "="*60)
    print("LATEX TABLE FOR PAPER")
    print("="*60)
    latex_table = generate_latex_table(summary or {
        'success_rate': (sum(1 for r in results if r['success']) / len(results) * 100) if results else 0,
        'total_tasks': len(results)
    }, categories)
    print(latex_table)
    print("="*60)

    # Simple row for quick copy-paste
    success_rate = summary.get('success_rate', 0) if summary else (sum(1 for r in results if r['success']) / len(results) * 100 if results else 0)
    print("\nQUICK COPY-PASTE ROW:")
    print(f"\\textbf{{CT-Spider2V}} & \\textbf{{{success_rate:.1f}\\%}} \\\\")

    print("\n✅ Analysis complete!\n")


if __name__ == "__main__":
    main()
