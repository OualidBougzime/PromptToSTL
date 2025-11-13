#!/bin/bash
# Test script for fixed CoT pipeline

cd "$(dirname "$0")/backend"

echo "🧪 Testing fixed CoT pipeline with problematic prompts..."
echo ""

# Test 1: VASE (was cube)
echo "1️⃣  Testing VASE (loft pattern)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a vase by lofting circles: radius 30 mm at base (Z=0), radius 22 mm at mid-height 60 mm, radius 35 mm at top 120 mm. Hollow with 3 mm wall thickness."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

# Test 2: GLASS (was solid)
echo "2️⃣  Testing GLASS (hollow cylinder)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a drinking glass: outer cylinder radius 35 mm height 100 mm, subtract inner cylinder radius 32.5 mm depth 92 mm from top. Fillet rim 1 mm."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

# Test 3: SPRING (was appearing as cylinder)
echo "3️⃣  Testing SPRING (helical sweep)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a helical spring by sweeping a circle radius 1.5 mm along a helix with pitch 8 mm, total height 80 mm, major radius 20 mm."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

# Test 4: BOWL (was BRep_API error)
echo "4️⃣  Testing BOWL (sphere method)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a hemispherical bowl: sphere radius 40 mm, keep bottom half, shell 3 mm thickness, fillet rim 1 mm."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

# Test 5: SCREW (was chamfer error)
echo "5️⃣  Testing SCREW (shaft + hex head)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a screw: cylindrical shaft radius 4 mm height 50 mm, hexagonal head circumradius 6 mm height 5 mm, union them."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

# Test 6: PIPE (was warning)
echo "6️⃣  Testing PIPE (hollow cylinder)..."
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a pipe: outer cylinder radius 20 mm length 150 mm, subtract inner cylinder radius 15 mm. Chamfer rims 1 mm."}' \
  | jq -r '.status, .errors[]?' || true
echo ""

echo "✅ All tests completed!"
