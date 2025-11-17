#!/usr/bin/env python3
"""
Test that Critic detects torus missing .moveTo() even if "moveTo" is in a comment
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from multi_agent_system import CriticAgent


async def test_critic_torus_with_comment():
    """Test that Critic detects torus missing .moveTo() when "moveTo" is in comment"""
    print("\n" + "="*80)
    print("TEST: Critic with 'moveTo' in comment but not in code")
    print("="*80)

    # Prompt for torus
    prompt = "Create a torus major radius 50 mm minor radius 8 mm"

    # Code with "moveTo" in comment but NOT in actual code
    # This should still be detected as missing .moveTo()
    bad_code = """import cadquery as cq
from pathlib import Path

# Note: Should use moveTo to position the circle before revolving
result = (cq.Workplane("XZ")
          .circle(8)
          .revolve(360))

# Export
output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
output_path = output_dir / "generated.stl"
cq.exporters.export(result, str(output_path))
"""

    print("\nCODE (has 'moveTo' in comment but NO .moveTo() call):")
    print("-" * 80)
    print(bad_code)
    print("-" * 80)
    print(f"\nChecking: 'moveTo' in code = {'moveTo' in bad_code}")
    print(f"Checking: '.moveTo(' in code = {'.moveTo(' in bad_code}")
    print(f"Checking: 'revolve' in code = {'revolve' in bad_code}")

    # Create Critic agent
    critic = CriticAgent()

    # Critic should detect torus missing .moveTo()
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
        torus_error = any("torus" in err.lower() and "moveTo" in err for err in errors)
        if torus_error:
            print("\n✅ SUCCESS: Critic correctly detected missing .moveTo() despite comment!")
            print("   (Old version would have been fooled by 'moveTo' in comment)")
            return True
        else:
            print("\n⚠️  Critic detected errors but NOT torus-specific")
            return False
    else:
        print("\n❌ FAILED: Critic did not detect missing .moveTo()")
        print("   The comment containing 'moveTo' should NOT satisfy the requirement")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_critic_torus_with_comment())
    sys.exit(0 if success else 1)
