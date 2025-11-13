#!/usr/bin/env python3
"""
Batch runner for executing multiple CAD prompts automatically.
Saves logs and generated code for each prompt to a JSON file.

Usage:
    python batch_runner.py                    # Run with prompts.json or defaults
    python batch_runner.py custom_prompts.json # Run with custom file
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import logging

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import OrchestratorAgent
from agents import AnalystAgent, GeneratorAgent, ValidatorAgent


# Default list of CAD prompts (used if prompts.json doesn't exist)
DEFAULT_PROMPTS = [
    "Create a table: make a rectangular top 200 mm × 100 mm × 15 mm, add four cylindrical legs diameter 12 mm height 120 mm inset 15 mm from each corner under the top, and union all parts.",

    "Create a vase by revolving a smooth profile with radius 30 mm at base, 22 mm at mid-height 60 mm, and 35 mm at top height 120 mm, then shell to 3 mm wall thickness and keep a flat 3 mm bottom.",

    "Create a drinking glass: make an outer cylinder radius 35 mm height 100 mm, subtract an inner cylinder radius 32.5 mm height 92 mm to leave an 8 mm solid bottom, then fillet the rim 1 mm.",

    "Create a helical spring by sweeping a circle radius 1.5 mm along a right-hand helix with major radius 20 mm, pitch 8 mm, and 10 turns, then trim both ends flat.",

    "Create a pipe by subtracting an inner cylinder radius 15 mm length 150 mm from an outer cylinder radius 20 mm length 150 mm, then optionally chamfer both rim edges 1 mm.",

    "Create a hemispherical bowl by revolving a semicircle radius 40 mm to form a hemisphere, then shell to 3 mm wall thickness while keeping a 3 mm bottom and fillet the rim 1 mm.",

    "Create a screw: make a cylindrical shaft radius 4 mm height 50 mm, place a hexagonal head circumradius 6 mm height 5 mm on top, and union the head and shaft (optional 0.5 mm chamfer on head edges).",

    "Create the Stanford Bunny mesh, scale to overall height 70 mm, fix non-manifold edges and unify normals, then remesh to about 18 000 triangles."
]


def load_prompts(prompts_file: str = "prompts.json") -> List[str]:
    """
    Load prompts from JSON file. Falls back to default prompts if file doesn't exist.

    Args:
        prompts_file: Path to JSON file containing prompts

    Returns:
        List of prompt strings to execute
    """
    prompts_path = Path(prompts_file)

    if prompts_path.exists():
        try:
            with open(prompts_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                prompts = [
                    p['prompt']
                    for p in config.get('prompts', [])
                    if p.get('enabled', True)
                ]
                print(f"✅ Loaded {len(prompts)} prompts from {prompts_file}")
                return prompts
        except Exception as e:
            print(f"⚠️  Error loading {prompts_file}: {e}")
            print(f"   Falling back to default prompts")
            return DEFAULT_PROMPTS
    else:
        print(f"ℹ️  {prompts_file} not found, using default prompts")
        return DEFAULT_PROMPTS


class BatchRunner:
    """Runs multiple CAD prompts and saves results."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path(__file__).parent / "batch_results"
        self.output_dir.mkdir(exist_ok=True)

        # Initialize the three base agents
        analyst = AnalystAgent()
        generator = GeneratorAgent()
        validator = ValidatorAgent()

        # Create orchestrator with the required agents
        self.orchestrator = OrchestratorAgent(analyst, generator, validator)
        self.results = []

        # Configure logging
        self.setup_logging()

    def setup_logging(self):
        """Configure logging to console and file."""
        log_file = self.output_dir / f"batch_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Batch runner initialized. Logs will be saved to: {log_file}")

    async def run_single_prompt(self, prompt: str, index: int, total: int) -> Dict[str, Any]:
        """Execute a single prompt and return results."""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"[{index + 1}/{total}] Processing prompt:")
        self.logger.info(f"  {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        self.logger.info(f"{'='*80}\n")

        start_time = datetime.now()
        result = {
            "index": index + 1,
            "prompt": prompt,
            "start_time": start_time.isoformat(),
            "success": False,
            "code": None,
            "stl_path": None,
            "error": None,
            "logs": [],
            "execution_time_seconds": 0
        }

        # Progress callback to capture logs
        def progress_callback(message: str, progress: int):
            log_entry = f"[Progress {progress}%] {message}"
            result["logs"].append(log_entry)
            self.logger.info(f"  {log_entry}")

        try:
            # Execute the workflow
            workflow_result = await self.orchestrator.execute_workflow(
                prompt=prompt,
                progress_callback=progress_callback
            )

            # Extract results
            result["success"] = workflow_result.get("success", False)
            result["code"] = workflow_result.get("code", "")
            result["stl_path"] = workflow_result.get("stl_path", "")

            if not result["success"]:
                result["error"] = workflow_result.get("error", "Unknown error")
                self.logger.error(f"  ❌ Failed: {result['error']}")
            else:
                self.logger.info(f"  ✅ Success! STL saved to: {result['stl_path']}")

                # Save the generated code to a separate file
                if result["code"]:
                    code_file = self.output_dir / f"prompt_{index + 1:02d}_code.py"
                    code_file.write_text(result["code"])
                    self.logger.info(f"  📝 Code saved to: {code_file}")

        except Exception as e:
            result["error"] = str(e)
            self.logger.error(f"  ❌ Exception: {e}", exc_info=True)

        # Calculate execution time
        end_time = datetime.now()
        result["end_time"] = end_time.isoformat()
        result["execution_time_seconds"] = (end_time - start_time).total_seconds()

        self.logger.info(f"  ⏱️  Execution time: {result['execution_time_seconds']:.2f}s\n")

        return result

    async def run_all(self, prompts: List[str]):
        """Run all prompts sequentially."""
        self.logger.info(f"Starting batch run with {len(prompts)} prompts...")
        self.logger.info(f"Results will be saved to: {self.output_dir}\n")

        overall_start = datetime.now()
        total_prompts = len(prompts)

        # Execute each prompt
        for i, prompt in enumerate(prompts):
            result = await self.run_single_prompt(prompt, i, total_prompts)
            self.results.append(result)

        overall_end = datetime.now()
        total_time = (overall_end - overall_start).total_seconds()

        # Generate summary
        self.generate_summary(total_time)

        # Save results to JSON
        self.save_results()

    def generate_summary(self, total_time: float):
        """Generate and display summary of results."""
        successful = sum(1 for r in self.results if r["success"])
        failed = len(self.results) - successful

        self.logger.info(f"\n{'='*80}")
        self.logger.info("BATCH RUN SUMMARY")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"Total prompts: {len(self.results)}")
        self.logger.info(f"Successful:    {successful} ✅")
        self.logger.info(f"Failed:        {failed} ❌")
        self.logger.info(f"Total time:    {total_time:.2f}s")
        self.logger.info(f"Average time:  {total_time / len(self.results):.2f}s per prompt")
        self.logger.info(f"{'='*80}\n")

        if failed > 0:
            self.logger.info("Failed prompts:")
            for r in self.results:
                if not r["success"]:
                    self.logger.info(f"  [{r['index']}] {r['prompt'][:60]}...")
                    self.logger.info(f"       Error: {r['error']}")

    def save_results(self):
        """Save all results to a JSON file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = self.output_dir / f"batch_results_{timestamp}.json"

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": timestamp,
                "total_prompts": len(self.results),
                "successful": sum(1 for r in self.results if r["success"]),
                "failed": sum(1 for r in self.results if not r["success"]),
                "results": self.results
            }, f, indent=2, ensure_ascii=False)

        self.logger.info(f"📊 Results saved to: {results_file}")


async def main():
    """Main entry point."""
    # Load prompts from JSON file or command line argument
    prompts_file = sys.argv[1] if len(sys.argv) > 1 else "prompts.json"
    prompts = load_prompts(prompts_file)

    if not prompts:
        print("❌ No prompts to execute!")
        return

    # Run batch
    runner = BatchRunner()
    await runner.run_all(prompts)

    # Print final message
    print("\n" + "="*80)
    print("✨ Batch run complete! Check the 'batch_results' folder for:")
    print("  - batch_run_*.log     : Full execution logs")
    print("  - batch_results_*.json: Structured results with all data")
    print("  - prompt_*_code.py    : Generated Python code for each prompt")
    print("  - STL files in backend/output/")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
