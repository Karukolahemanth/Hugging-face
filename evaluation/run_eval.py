"""
GAIA-style evaluation runner.
Runs a JSON dataset of tasks through the agent and measures accuracy.

Usage:
    python evaluation/run_eval.py --dataset evaluation/sample_tasks.json
"""

import asyncio
import json
import sys
import time
import argparse
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agent.agent import GAIAAgent


async def run_single(agent: GAIAAgent, task: dict) -> dict:
    """Run the agent on a single task and return evaluation result."""
    question = task.get("question", "")
    expected = str(task.get("expected_answer", "")).strip().lower()

    start = time.time()
    state = await agent.run(task=question)
    elapsed = round(time.time() - start, 2)

    agent_answer = (state.final_answer or "").strip()

    # Exact match (case-insensitive, stripped)
    exact_match = expected in agent_answer.lower() or agent_answer.lower() == expected

    return {
        "id": task.get("id", "unknown"),
        "question": question,
        "expected": expected,
        "agent_answer": agent_answer[:300],
        "correct": exact_match,
        "execution_time_s": elapsed,
        "num_steps": state.iteration,
        "num_tool_calls": len(state.tool_calls),
        "status": state.status.value,
    }


async def run_eval(dataset_path: str):
    dataset = json.loads(Path(dataset_path).read_text())
    agent = GAIAAgent()

    results = []
    for task in dataset:
        print(f"Running task: {task.get('id', '?')} — {task.get('question', '')[:60]}")
        result = await run_single(agent, task)
        results.append(result)
        status = "✓" if result["correct"] else "✗"
        print(f"  {status} | time: {result['execution_time_s']}s | steps: {result['num_steps']}")

    # Summary
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    print(f"\n{'='*50}")
    print(f"EVALUATION SUMMARY")
    print(f"{'='*50}")
    print(f"Tasks:    {total}")
    print(f"Correct:  {correct}")
    print(f"Accuracy: {accuracy}%")
    print(f"Avg time: {round(sum(r['execution_time_s'] for r in results) / total, 1)}s")
    print(f"Avg steps:{round(sum(r['num_steps'] for r in results) / total, 1)}")

    # Save results
    output_path = Path(dataset_path).with_suffix(".results.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GAIA Evaluation Runner")
    parser.add_argument(
        "--dataset",
        default="evaluation/sample_tasks.json",
        help="Path to JSON dataset file",
    )
    args = parser.parse_args()
    asyncio.run(run_eval(args.dataset))
