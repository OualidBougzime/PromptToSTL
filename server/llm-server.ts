// Remplacez COMPLÈTEMENT le contenu de server/llm-server.ts

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

// PROMPT AVEC LOGIQUE STRUCTURÉE ET DÉCOMPOSITION
const STRUCTURED_CAD_PROMPT = `Tu es un ingénieur CAD expert. Pour CHAQUE demande, tu dois suivre cette méthodologie structurée:

1. ANALYSER le problème et le décomposer en composants de base
2. DÉFINIR les paramètres géométriques principaux  
3. CRÉER chaque composant individuellement
4. ASSEMBLER les composants avec des positions calculées

STRUCTURE OBLIGATOIRE de ta réponse:

\`\`\`javascript
// ÉTAPE 1: ANALYSE ET PARAMÈTRES
// [Décris brièvement les composants identifiés]
const param1 = valeur1    // Description
const param2 = valeur2    // Description  
// etc.

// ÉTAPE 2: FONCTIONS HELPER (si nécessaire)
function createComponent1(params) {
  // Logique pour composant complexe
  return mesh
}

// ÉTAPE 3: FONCTION PRINCIPALE
function generateModel() {
  const meshes = []
  
  // Composant 1: Description
  const comp1Geo = new THREE.GeometryType(params...)
  const comp1Mat = new THREE.MeshStandardMaterial({ color: 0xCOLOR })
  const comp1 = new THREE.Mesh(comp1Geo, comp1Mat)
  comp1.position.set(x_calculé, y_calculé, z_calculé)
  meshes.push(comp1)
  
  // Composant 2: Description
  // [même pattern]
  
  // Assemblages multiples (boucles si nécessaire)
  for (let i = 0; i < count; i++) {
    // Logique de positionnement calculée
    const angle = (i / count) * Math.PI * 2
    const x = Math.cos(angle) * radius
    const z = Math.sin(angle) * radius
    // etc.
  }
  
  return meshes
}
\`\`\`

EXEMPLES DE DÉCOMPOSITION:

USER: Create a 3D printer extruder assembly
ANALYSE: Extruder = moteur + réducteur + bloc chauffant + ventilateur + connecteurs
ASSISTANT: \`\`\`javascript
// ÉTAPE 1: ANALYSE ET PARAMÈTRES  
// Composants: stepper motor mount, gear housing, heated block, fan shroud, bowden connector
const motorWidth = 42        // Taille moteur NEMA17
const motorDepth = 40        // Profondeur moteur
const gearRatio = 3          // Réduction 3:1
const blockWidth = 20        // Bloc chauffant
const blockHeight = 20       // Hauteur bloc
const fanDiameter = 40       // Ventilateur 40mm
const bowdenDiameter = 6     // Connecteur bowden

function generateModel() {
  const meshes = []
  
  // Composant 1: Support moteur
  const motorMountGeo = new THREE.BoxGeometry(motorWidth + 4, motorDepth + 4, 8)
  const motorMountMat = new THREE.MeshStandardMaterial({ color: 0x444444 })
  const motorMount = new THREE.Mesh(motorMountGeo, motorMountMat)
  motorMount.position.set(0, motorDepth/2 + 2, 0)
  meshes.push(motorMount)
  
  // Composant 2: Moteur (simulation)
  const motorGeo = new THREE.BoxGeometry(motorWidth, motorWidth, motorDepth)
  const motorMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
  const motor = new THREE.Mesh(motorGeo, motorMat)
  motor.position.set(0, motorDepth/2, motorWidth/2 + 4)
  meshes.push(motor)
  
  // Composant 3: Boîtier d'engrenages
  const gearHousingGeo = new THREE.BoxGeometry(30, 30, 15)
  const gearHousingMat = new THREE.MeshStandardMaterial({ color: 0x666666 })
  const gearHousing = new THREE.Mesh(gearHousingGeo, gearHousingMat)
  gearHousing.position.set(0, -20, 0)
  meshes.push(gearHousing)
  
  // Composant 4: Bloc chauffant
  const heatedBlockGeo = new THREE.BoxGeometry(blockWidth, blockHeight, blockWidth)
  const heatedBlockMat = new THREE.MeshStandardMaterial({ color: 0xFF4444 })
  const heatedBlock = new THREE.Mesh(heatedBlockGeo, heatedBlockMat)
  heatedBlock.position.set(0, -35, 0)
  meshes.push(heatedBlock)
  
  // Composant 5: Carénage ventilateur
  const fanShroudGeo = new THREE.CylinderGeometry(fanDiameter/2, fanDiameter/2 - 2, 10, 16)
  const fanShroudMat = new THREE.MeshStandardMaterial({ color: 0x0088FF })
  const fanShroud = new THREE.Mesh(fanShroudGeo, fanShroudMat)
  fanShroud.position.set(30, -20, 0)
  fanShroud.rotation.z = Math.PI/2
  meshes.push(fanShroud)
  
  // Composant 6: Connecteur bowden
  const bowdenGeo = new THREE.CylinderGeometry(bowdenDiameter/2, bowdenDiameter/2, 20, 16)
  const bowdenMat = new THREE.MeshStandardMaterial({ color: 0xFFFFFF })
  const bowden = new THREE.Mesh(bowdenGeo, bowdenMat)
  bowden.position.set(0, 20, 0)
  meshes.push(bowden)
  
  return meshes
}
\`\`\`

USER: Create a mechanical watch escapement
ANALYSE: Escapement = escape wheel + pallet fork + balance wheel + jewel bearings
ASSISTANT: \`\`\`javascript
// ÉTAPE 1: ANALYSE ET PARAMÈTRES
// Composants: escape wheel (roue d'échappement), pallet fork (ancre), balance wheel (balancier), jewel bearings
const escapeWheelRadius = 8     // Rayon roue d'échappement
const escapeTeethCount = 15     // Nombre de dents
const palletLength = 12         // Longueur de l'ancre  
const balanceRadius = 10        // Rayon du balancier
const jewelRadius = 0.8         // Rayon des rubis

function generateModel() {
  const meshes = []
  
  // Composant 1: Roue d'échappement avec dents
  const escapeWheelGeo = new THREE.CylinderGeometry(escapeWheelRadius, escapeWheelRadius, 1, escapeTeethCount * 2)
  const escapeWheelMat = new THREE.MeshStandardMaterial({ color: 0xGOLD })
  const escapeWheel = new THREE.Mesh(escapeWheelGeo, escapeWheelMat)
  escapeWheel.position.set(0, 0, 0)
  meshes.push(escapeWheel)
  
  // Dents d'échappement (créées individuellement)
  for (let i = 0; i < escapeTeethCount; i++) {
    const angle = (i / escapeTeethCount) * Math.PI * 2
    const toothGeo = new THREE.BoxGeometry(0.5, 2, 1)
    const toothMat = new THREE.MeshStandardMaterial({ color: 0xGOLD })
    const tooth = new THREE.Mesh(toothGeo, toothMat)
    
    const x = Math.cos(angle) * escapeWheelRadius
    const z = Math.sin(angle) * escapeWheelRadius
    tooth.position.set(x, 0, z)
    tooth.rotation.y = angle
    meshes.push(tooth)
  }
  
  // Composant 2: Ancre (pallet fork)
  const palletForkGeo = new THREE.BoxGeometry(palletLength, 1, 2)
  const palletForkMat = new THREE.MeshStandardMaterial({ color: 0x888888 })
  const palletFork = new THREE.Mesh(palletForkGeo, palletForkMat)
  palletFork.position.set(escapeWheelRadius + 5, 0, 0)
  meshes.push(palletFork)
  
  // Composant 3: Balancier
  const balanceWheelGeo = new THREE.TorusGeometry(balanceRadius, 1, 8, 32)
  const balanceWheelMat = new THREE.MeshStandardMaterial({ color: 0x444444 })
  const balanceWheel = new THREE.Mesh(balanceWheelGeo, balanceWheelMat)
  balanceWheel.position.set(0, 8, 0)
  meshes.push(balanceWheel)
  
  // Composant 4: Rubis (jewel bearings) aux points critiques
  const jewelPositions = [
    [0, -2, 0],                          // Centre roue d'échappement
    [escapeWheelRadius + 5, -2, 0],      // Centre ancre
    [0, 6, 0],                           // Centre balancier
    [escapeWheelRadius + 2, 1, 1],       // Contact ancre-roue 1
    [escapeWheelRadius + 2, 1, -1]       // Contact ancre-roue 2
  ]
  
  jewelPositions.forEach(([x, y, z]) => {
    const jewelGeo = new THREE.SphereGeometry(jewelRadius, 8, 8)
    const jewelMat = new THREE.MeshStandardMaterial({ 
      color: 0xFF0088, 
      transparent: true, 
      opacity: 0.8 
    })
    const jewel = new THREE.Mesh(jewelGeo, jewelMat)
    jewel.position.set(x, y, z)
    meshes.push(jewel)
  })
  
  return meshes
}
\`\`\`

RÈGLES IMPORTANTES:
1. TOUJOURS décomposer en composants logiques
2. CALCULER les positions relativement aux paramètres
3. UTILISER des boucles for pour les éléments répétitifs
4. POSITIONNER les composants de manière cohérente
5. CHOISIR des couleurs qui différencient les fonctions

RÉPONDS UNIQUEMENT avec du code JavaScript structuré comme dans les exemples.`

app.post('/api/generate', async (req, res) => {
    try {
        const natural: string = String(req.body?.natural || '')
        if (!natural.trim()) return res.status(400).json({ error: 'natural prompt is empty' })

        console.log('[CAD SERVER] Requête complexe:', natural)

        const body = {
            model: MODEL,
            stream: false,
            messages: [
                { role: 'system', content: STRUCTURED_CAD_PROMPT },
                { role: 'user', content: natural }
            ]
        }

        console.log('[CAD SERVER] Envoi vers LLM...')
        const r = await fetch(`${OLLAMA_URL}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        })

        if (!r.ok) {
            const txt = await r.text()
            console.error('[CAD SERVER] Erreur Ollama:', txt)
            return res.status(502).json({ error: 'ollama_error', detail: txt })
        }

        const data: any = await r.json()
        let jsCode: string = data?.message?.content || ''

        console.log('[CAD SERVER] Réponse LLM brute:', jsCode.substring(0, 200) + '...')

        // Extraction ultra-stricte du code JavaScript
        jsCode = extractJavaScriptCode(jsCode)

        if (!jsCode || !jsCode.includes('function generateModel')) {
            console.log('[CAD SERVER] Extraction échouée, fallback')
            return res.json({
                code: createFallbackCode(natural),
                success: true,
                method: 'fallback'
            })
        }

        console.log('[CAD SERVER] Code extrait avec succès')
        return res.json({
            code: jsCode,
            success: true,
            method: 'structured_generation'
        })

    } catch (e: any) {
        console.error('[CAD SERVER] Erreur:', e)
        return res.json({
            code: createFallbackCode(natural),
            success: true,
            method: 'error_fallback'
        })
    }
})

// Extracteur de code JavaScript ultra-strict
function extractJavaScriptCode(text: string): string {
    console.log('[EXTRACTOR] Début extraction...')

    // Supprimer les blocs markdown
    let cleaned = text.replace(/```javascript/g, '').replace(/```/g, '')

    // Extraire seulement les lignes de code valides
    const lines = cleaned.split('\n')
    const codeLines: string[] = []
    let inCodeSection = false

    for (const line of lines) {
        const trimmed = line.trim()

        // Détecter le début du code
        if (trimmed.startsWith('//') ||
            trimmed.startsWith('const ') ||
            trimmed.startsWith('function ') ||
            trimmed.startsWith('let ')) {
            inCodeSection = true
        }

        // Garder seulement les lignes de code JavaScript valides
        if (inCodeSection) {
            if (trimmed === '' ||
                trimmed.startsWith('//') ||
                trimmed.startsWith('const ') ||
                trimmed.startsWith('let ') ||
                trimmed.startsWith('function ') ||
                trimmed.includes('new THREE.') ||
                trimmed.includes('meshes.push') ||
                trimmed.includes('return meshes') ||
                trimmed.includes('.position') ||
                trimmed.includes('.rotation') ||
                trimmed.includes('.scale') ||
                trimmed.includes('for (') ||
                trimmed.includes('forEach') ||
                trimmed.includes('Math.') ||
                trimmed === '}' ||
                trimmed === '{' ||
                /^\s*[\}\{]/.test(line)) {
                codeLines.push(line)
            }
        }
    }

    const result = codeLines.join('\n')
    console.log('[EXTRACTOR] Code extrait:', result.length, 'caractères')
    return result
}

// Fallback intelligent basé sur le prompt
function createFallbackCode(prompt: string): string {
    const lowerPrompt = prompt.toLowerCase()

    if (lowerPrompt.includes('gear') || lowerPrompt.includes('cog')) {
        return `// Engrenage simple
const radius = 10
const teeth = 12
const thickness = 3

function generateModel() {
  const meshes = []
  
  const gearGeo = new THREE.CylinderGeometry(radius, radius, thickness, teeth * 2)
  const gearMat = new THREE.MeshStandardMaterial({ color: 0x888888 })
  const gear = new THREE.Mesh(gearGeo, gearMat)
  gear.position.y = thickness/2
  meshes.push(gear)
  
  return meshes
}`
    }

    if (lowerPrompt.includes('spring') || lowerPrompt.includes('coil')) {
        return `// Ressort simple
const radius = 8
const height = 30
const coils = 8

function generateModel() {
  const meshes = []
  
  const springGeo = new THREE.TorusGeometry(radius, 1, 8, 32)
  const springMat = new THREE.MeshStandardMaterial({ color: 0x666666 })
  
  for (let i = 0; i < coils; i++) {
    const spring = new THREE.Mesh(springGeo, springMat)
    spring.position.y = (i / coils) * height
    meshes.push(spring)
  }
  
  return meshes
}`
    }

    // Fallback générique
    return `// Forme de base
const size = 10

function generateModel() {
  const meshes = []
  
  const cubeGeo = new THREE.BoxGeometry(size, size, size)
  const cubeMat = new THREE.MeshStandardMaterial({ color: 0xff6b6b })
  const cube = new THREE.Mesh(cubeGeo, cubeMat)
  cube.position.y = size/2
  meshes.push(cube)
  
  return meshes
}`
}

// Health check
app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        model: MODEL,
        version: '3.0.0-structured',
        approach: 'chain_of_thought_decomposition'
    })
})

app.listen(PORT, () => {
    console.log(`[CAD LLM Server v3.0-STRUCTURED] listening on http://localhost:${PORT}`)
    console.log(`Using model: ${MODEL}`)
    console.log('Approach: Structured problem decomposition with Chain-of-Thought')
})