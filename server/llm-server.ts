// server/llm-server.ts
import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import fetch from 'node-fetch'

const app = express()
app.use(cors())
app.use(express.json({ limit: '10mb' }))

const PORT = process.env.PORT || 8787
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434'
const MODEL = process.env.OLLAMA_MODEL || 'llama3.1'

const CAD_SYSTEM_PROMPT = `You are an advanced CAD code generator. Generate VALID JavaScript that creates 3D models.

CRITICAL RULES:
1. ALWAYS push meshes to the 'meshes' array
2. Variables declared in loops cannot be used outside
3. Create individual meshes and add them separately
4. NEVER combine all into one CSG operation at the end
5. Test your JavaScript logic before outputting

CORRECT PATTERN for complex objects:
// Create main part
const mainGeo = new THREE.BoxGeometry(10, 10, 10)
const mainMesh = new THREE.Mesh(mainGeo, new THREE.MeshStandardMaterial({ color: 0x666666 }))
meshes.push(mainMesh)

// Add multiple parts with loops
for(let i = 0; i < 5; i++) {
  const partGeo = new THREE.SphereGeometry(1, 8, 8)
  const partMesh = new THREE.Mesh(partGeo, new THREE.MeshStandardMaterial({ color: 0x00ff00 }))
  partMesh.position.set(i * 2, 5, 0)
  meshes.push(partMesh) // ADD EACH MESH TO ARRAY
}

TREE EXAMPLE:
// Trunk
const trunkGeo = new THREE.CylinderGeometry(1, 2, 8, 8)
const trunkMesh = new THREE.Mesh(trunkGeo, new THREE.MeshStandardMaterial({ color: 0x8B4513 }))
trunkMesh.position.y = 4
meshes.push(trunkMesh)

// Branches (created in loop but added individually)
for(let i = 0; i < 6; i++) {
  const angle = (i / 6) * Math.PI * 2
  const branchGeo = new THREE.CylinderGeometry(0.2, 0.4, 3, 6)
  const branchMesh = new THREE.Mesh(branchGeo, new THREE.MeshStandardMaterial({ color: 0x8B4513 }))
  branchMesh.position.set(Math.cos(angle) * 1.5, 6 + i * 0.3, Math.sin(angle) * 1.5)
  branchMesh.rotation.z = Math.PI / 6
  meshes.push(branchMesh)
}

// Leaves
for(let i = 0; i < 12; i++) {
  const leafGeo = new THREE.SphereGeometry(0.8, 6, 6)
  const leafMesh = new THREE.Mesh(leafGeo, new THREE.MeshStandardMaterial({ color: 0x228B22 }))
  leafMesh.position.set(
    (Math.random() - 0.5) * 6, 
    7 + Math.random() * 3, 
    (Math.random() - 0.5) * 6
  )
  meshes.push(leafMesh)
}

HUMAN EXAMPLE:
// Head
const headGeo = new THREE.SphereGeometry(1.5, 12, 12)
const headMesh = new THREE.Mesh(headGeo, new THREE.MeshStandardMaterial({ color: 0xFFDBB3 }))
headMesh.position.y = 12
meshes.push(headMesh)

// Body  
const bodyGeo = new THREE.CylinderGeometry(1.5, 2, 6, 8)
const bodyMesh = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({ color: 0x0000FF }))
bodyMesh.position.y = 6
meshes.push(bodyMesh)

// Arms and legs
for(let i = 0; i < 2; i++) {
  // Arms
  const armGeo = new THREE.CylinderGeometry(0.4, 0.4, 4, 6)
  const armMesh = new THREE.Mesh(armGeo, new THREE.MeshStandardMaterial({ color: 0xFFDBB3 }))
  armMesh.position.set((i * 2 - 1) * 2.5, 8, 0)
  armMesh.rotation.z = (i * 2 - 1) * 0.3
  meshes.push(armMesh)
  
  // Legs
  const legGeo = new THREE.CylinderGeometry(0.5, 0.5, 5, 6)
  const legMesh = new THREE.Mesh(legGeo, new THREE.MeshStandardMaterial({ color: 0x000080 }))
  legMesh.position.set((i * 2 - 1) * 1, 1.5, 0)
  meshes.push(legMesh)
}

REMEMBER: 
- Each mesh must be added individually to meshes array
- No undefined variables
- No complex CSG at the end
- Create working, valid JavaScript

Return ONLY valid JavaScript code that adds meshes to the array.`

app.post('/api/generate', async (req, res) => {
    try {
        const natural: string = String(req.body?.natural || '')
        if (!natural.trim()) return res.status(400).json({ error: 'natural prompt is empty' })

        const body = {
            model: MODEL,
            stream: false,
            messages: [
                { role: 'system', content: CAD_SYSTEM_PROMPT },
                { role: 'user', content: natural }
            ]
        }

        const r = await fetch(`${OLLAMA_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })

        if (!r.ok) {
            const txt = await r.text()
            return res.status(502).json({ error: 'ollama_error', detail: txt })
        }

        const data: any = await r.json()
        const content: string = data?.message?.content || ''

        // Clean up the response to extract just the JavaScript code
        let jsCode = content.trim()

        // Remove markdown backticks if present
        jsCode = jsCode.replace(/^```javascript\n?/, '').replace(/^```js\n?/, '').replace(/```$/, '')

        // If the code doesn't include the function wrapper, add it
        if (!jsCode.includes('function generateModel')) {
            jsCode = `function generateModel() {
  const meshes = []
  
  ${jsCode}
  
  return meshes
}`
        }

        return res.json({
            code: jsCode,
            success: true
        })

    } catch (e: any) {
        console.error('Server error:', e)
        return res.status(500).json({ error: e?.message || 'server_error' })
    }
})

// Health check endpoint
app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', model: MODEL, ollama_url: OLLAMA_URL })
})

app.listen(PORT, () => {
    console.log(`[CAD LLM Server] listening on http://localhost:${PORT}`)
    console.log(`Using Ollama at: ${OLLAMA_URL}`)
    console.log(`Using model: ${MODEL}`)
})