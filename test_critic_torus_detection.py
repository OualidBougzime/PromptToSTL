#!/usr/bin/env python3
"""
Test if Critic detects torus missing moveTo
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent


async def test_critic_torus_detection():
    """Test that Critic detects torus code missing moveTo"""
    print("\n" + "="*80)
    print("TEST: Critic detection of torus missing moveTo")
    print("="*80)

    # Prompt for torus
    prompt = "Create a torus major radius 50 mm minor radius 8 mm"

    # Code with revolve but NO moveTo - should be detected by Critic
    bad_code = """import cadquery as cq
from pathlib import Path

result = (cq.Workplane("XZ")
          .circle(8)
          .revolve(360))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated.stl"
cq.exporters.export(result, str(output_path))
"""

    print("\nCODE (has revolve but NO moveTo):")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)
    print(f"\nChecking: 'moveTo' in code = {'moveTo' in bad_code}")
    print(f"Checking: 'revolve' in code = {'revolve' in bad_code}")

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect torus missing moveTo
    result = await critic.critique_code(bad_code, prompt)
    errors = result.errors

    print("\n" + "="*80)
    print("CRITIC RESULT:")
    print("="*80)

    if errors:
        print(f"\n✅ Critic detected {len(errors)} error(s):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

        # Check if torus-specific error
        torus_error = any("torus" in err.lower() or "moveTo" in err for err in errors)
        if torus_error:
            print("\n✅ Critic correctly detected TORUS missing moveTo issue!")
            return True
        else:
            print("\n⚠️  Critic detected errors but NOT torus-specific")
            return False
    else:
        print("\n❌ Critic FAILED - no errors detected!")
        print("   Expected: SEMANTIC ERROR about torus missing moveTo")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_critic_torus_detection())
    sys.exit(0 if success else 1)
