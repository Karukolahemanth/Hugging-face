"""
GAIA Benchmark Submission Generator.

Downloads the official GAIA validation set from HuggingFace, runs your agent
on all tasks, and produces a submission.jsonl file in the exact format required
by the GAIA leaderboard.

Usage:
    python evaluation/gaia_submit.py --split validation --level 1
    python evaluation/gaia_submit.py --split validation  # all levels

Prerequisites:
    pip install datasets huggingface_hub
    huggingface-cli login   (or set HF_TOKEN in .env)
"""

import asyncio
import json
import sys
import time
import argparse
from pathlib import Path

# Force UTF-8 output so Windows cp1252 console doesn't crash on Unicode chars
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.agent.agent import GAIAAgent
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ── GAIA output format ────────────────────────────────────────────────────────
def make_submission_row(task_id: str, model_answer: str) -> dict:
    """Produce a row in the GAIA leaderboard submission format."""
    return {
        "task_id": task_id,
        "model_answer": model_answer,
    }


# ── Load GAIA dataset ─────────────────────────────────────────────────────────
def load_gaia_dataset(split: str = "validation", level: int | None = None):
    """Load GAIA tasks from the HuggingFace dataset hub."""
    try:
        from datasets import load_dataset
        import warnings
        warnings.filterwarnings("ignore", message=".*symlinks.*")
    except ImportError:
        print("ERROR: Install datasets: pip install datasets huggingface_hub")
        sys.exit(1)

    print(f"Loading GAIA dataset (split={split}) ...")
    ds = load_dataset("gaia-benchmark/GAIA", "2023_all", split=split)

    if level is not None:
        ds = ds.filter(lambda x: x["Level"] == str(level))
        print(f"  Filtered to Level {level}: {len(ds)} tasks")
    else:
        print(f"  Total tasks: {len(ds)}")

    return ds


# ── Run agent on a single task ────────────────────────────────────────────────
async def run_task(agent: GAIAAgent, task: dict, idx: int, total: int) -> dict:
    task_id = task.get("task_id", task.get("id", f"task_{idx}"))
    question = task.get("Question", task.get("question", ""))
    expected = str(task.get("Final answer", task.get("expected_answer", ""))).strip()
    level = task.get("Level", "?")

    print(f"\n[{idx+1}/{total}] Level {level} | {task_id[:16]}…")
    print(f"  Q: {question[:100]}…" if len(question) > 100 else f"  Q: {question}")

    start = time.time()
    try:
        state = await asyncio.wait_for(agent.run(task=question), timeout=300)
        model_answer = (state.final_answer or "").strip()
        status = state.status.value
        steps = state.iteration
    except asyncio.TimeoutError:
        model_answer = ""
        status = "timeout"
        steps = 0
    except Exception as e:
        model_answer = ""
        status = f"error: {e}"
        steps = 0

    elapsed = round(time.time() - start, 1)

    # Score (only available in validation set which has answers)
    correct = None
    if expected:
        correct = expected.lower() in model_answer.lower() or model_answer.lower() == expected.lower()
        mark = "[OK]" if correct else "[X]"
        print(f"  {mark} | answer: {model_answer[:80]} | expected: {expected[:40]}")
    else:
        print(f"  -> answer: {model_answer[:80]}")

    print(f"  time: {elapsed}s | {steps} steps | {status}")

    return {
        # Leaderboard submission fields
        "task_id": task_id,
        "model_answer": model_answer,
        # Extra tracking fields (not submitted, kept locally)
        "_question": question[:200],
        "_expected": expected,
        "_correct": correct,
        "_elapsed_s": elapsed,
        "_steps": steps,
        "_status": status,
        "_level": level,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
async def main(split: str, level: int | None, output_dir: Path, dry_run: bool, args_delay: float = 5.0):
    output_dir.mkdir(parents=True, exist_ok=True)

    if dry_run:
        # Use local sample tasks for a quick smoke-test
        sample_path = Path("evaluation/sample_tasks.json")
        if not sample_path.exists():
            print("ERROR: sample_tasks.json not found. Run without --dry-run to use HF dataset.")
            return
        raw = json.loads(sample_path.read_text())
        tasks = [
            {
                "task_id": t.get("id", f"sample_{i}"),
                "Question": t.get("question", ""),
                "Final answer": t.get("expected_answer", ""),
                "Level": 1,
            }
            for i, t in enumerate(raw)
        ]
        print(f"DRY RUN: {len(tasks)} sample tasks")
    else:
        ds = load_gaia_dataset(split=split, level=level)
        tasks = list(ds)

    agent = GAIAAgent()
    results = []
    quota_exhausted = False

    for idx, task in enumerate(tasks):
        if quota_exhausted:
            # Pad remaining tasks with empty answers
            task_id = task.get("task_id", task.get("id", f"task_{idx}"))
            results.append({
                "task_id": task_id,
                "model_answer": "",
                "_question": task.get("Question", "")[:200],
                "_expected": str(task.get("Final answer", "")),
                "_correct": False,
                "_elapsed_s": 0,
                "_steps": 0,
                "_status": "quota_exhausted",
                "_level": task.get("Level", "?"),
            })
            continue

        row = await run_task(agent, task, idx, len(tasks))
        results.append(row)

        if "quota_exhausted" in row["_status"] or "RESOURCE_EXHAUSTED" in row["_status"]:
            quota_exhausted = True
            print(f"\n[!] Daily quota exhausted after {idx+1} tasks.")
            print(f"    Free tier limit: 20 requests/day on gemini-3.8-flash")
            print(f"    Upgrade at: https://aistudio.google.com/app/apikey")
            print(f"    Remaining {len(tasks)-idx-1} tasks will have empty answers.")
            continue

        # Polite delay between tasks to respect rate limits
        if idx < len(tasks) - 1:
            await asyncio.sleep(args_delay)


    # ── Save submission file (leaderboard format) ─────────────────────────
    level_tag = f"_level{level}" if level else "_all"
    submission_path = output_dir / f"submission_{split}{level_tag}.jsonl"
    with submission_path.open("w", encoding="utf-8") as f:
        for row in results:
            # Only include the two fields the leaderboard expects
            f.write(json.dumps({"task_id": row["task_id"], "model_answer": row["model_answer"]}) + "\n")
    print(f"\n✅ Submission file: {submission_path}")

    # ── Save full results (for analysis) ─────────────────────────────────
    full_path = output_dir / f"results_{split}{level_tag}.json"
    full_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   Full results:     {full_path}")

    # ── Summary ───────────────────────────────────────────────────────────
    scored = [r for r in results if r["_correct"] is not None]
    if scored:
        correct = sum(1 for r in scored if r["_correct"])
        accuracy = round(correct / len(scored) * 100, 1)
        avg_time = round(sum(r["_elapsed_s"] for r in results) / len(results), 1)
        print(f"\n{'='*55}")
        print(f"  GAIA EVALUATION SUMMARY ({split}, level={level or 'all'})")
        print(f"{'='*55}")
        print(f"  Tasks:    {len(results)}")
        print(f"  Correct:  {correct} / {len(scored)}")
        print(f"  Accuracy: {accuracy}%")
        print(f"  Avg time: {avg_time}s per task")
        print(f"{'='*55}")

    print(f"\n📤 Upload  {submission_path.name}  to the GAIA leaderboard:")
    print(f"   https://huggingface.co/spaces/gaia-benchmark/leaderboard")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GAIA Leaderboard Submission Generator")
    parser.add_argument("--split", default="validation", choices=["validation", "test"],
                        help="Dataset split (use 'validation' to see scores, 'test' for final submission)")
    parser.add_argument("--level", type=int, default=None, choices=[1, 2, 3],
                        help="Only run a specific difficulty level (default: all)")
    parser.add_argument("--output-dir", default="evaluation/submissions",
                        help="Directory to save submission and results files")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use local sample_tasks.json instead of the HF dataset (quick test)")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="Seconds to wait between tasks (default: 5, use higher on free tier)")
    args = parser.parse_args()

    asyncio.run(main(
        split=args.split,
        level=args.level,
        output_dir=Path(args.output_dir),
        dry_run=args.dry_run,
        args_delay=args.delay,
    ))
