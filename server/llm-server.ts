import 'dotenv/config'
import express from 'express'
import cors from 'cors'
import fetch from 'node-fetch'
import { TEMPLATES, selectTemplate } from './templates'

const app = express()
app.use(cors())
app.use(express.json({ limit: '10mb' }))

const PORT = process.env.PORT || 8787
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434'
const MODEL = process.env.OLLAMA_MODEL || 'qwen2.5-coder:14b'

// ============================================
// EXTRACTION DE PARAMÈTRES PAR LLM
// ============================================
function extractParameters(prompt: string, templateName: string): Record<string, number | string> {
    const template = TEMPLATES[templateName]
    const params: Record<string, number | string> = {}

    console.log(`\n📊 Extracting parameters for: ${templateName}`)

    // Cas spécial: dimensions carrées
    const squareMatch = prompt.match(/(\d+)mm\s*x\s*\1mm/i)
    if (squareMatch) {
        params.size = parseFloat(squareMatch[1])
        console.log(`  ✓ size: ${params.size} (square)`)
    }

    const boxMatch = prompt.match(/(\d+)mm\s*x\s*(\d+)mm(?:\s*x\s*(\d+)mm)?/i)
    if (boxMatch) {
        if (!params.length) params.length = parseFloat(boxMatch[1])
        if (!params.width) params.width = parseFloat(boxMatch[2])
        if (boxMatch[3] && !params.thickness && !params.height) {
            if (prompt.toLowerCase().includes('thick')) {
                params.thickness = parseFloat(boxMatch[3])
            } else {
                params.height = parseFloat(boxMatch[3])
            }
        }
        console.log(`  ✓ box dimensions: ${boxMatch[1]} x ${boxMatch[2]} x ${boxMatch[3] || 'N/A'}`)
    }

    const mountingHoleMatch = prompt.match(/(\d+)\s+M(\d+)\s+(?:mounting\s+)?holes?/i)
    if (mountingHoleMatch) {
        params.holeCount = parseFloat(mountingHoleMatch[1])
        params.holeDiameter = parseFloat(mountingHoleMatch[2])
        console.log(`  ✓ mounting holes: ${mountingHoleMatch[1]} x M${mountingHoleMatch[2]}`)
    }

    // Pattern spécifique pour COMPTEURS (nombre AVANT le mot)
    const counterPatterns: Record<string, RegExp> = {
        nodeCount: /(\d+)\s+(?:rotating\s+)?nodes?/i,
        segmentCount: /(\d+)\s+(?:annular\s+)?segments?/i,
        channelCount: /(\d+)\s+(?:micro[- ]release\s+)?channels?/i,
        filamentCount: /(\d+)\s+(?:braided\s+)?(?:filaments?|wires?)/i,
        ringCount: /(\d+)\s+(?:circumferential\s+)?rings?/i,
        chamberCount: /(\d+)\s+(?:expandable\s+)?chambers?/i,
        strapCount: /(\d+)\s+(?:adjustable\s+)?straps?/i,
        holeCount: /(\d+)\s+(?:mounting\s+)?holes?/i,
        teeth: /(\d+)\s+teeth/i,
        cellCount: /(\d+)\s+cells?/i,
        ribCount: /(\d+)\s+(?:reinforcement\s+)?ribs?/i
    }

    // Extraire les compteurs en priorité
    for (const [paramName, pattern] of Object.entries(counterPatterns)) {
        const match = prompt.match(pattern)
        if (match) {
            params[paramName] = parseFloat(match[1])
            console.log(`  ✓ ${paramName}: ${match[1]} (counter)`)
        }
    }

    // Pattern pour dimensions (nombre APRÈS le mot avec unité)
    const dimensionPatterns: Record<string, RegExp> = {
        length: /(?:length|long)\s+(\d+(?:\.\d+)?)\s*mm/i,
        diameter: /diameter\s+(\d+(?:\.\d+)?)\s*mm/i,
        width: /width\s+(\d+(?:\.\d+)?)\s*mm/i,
        height: /height\s+(\d+(?:\.\d+)?)\s*mm/i,
        thickness: /(?:thickness|thick)\s+(\d+(?:\.\d+)?)\s*mm/i,
        wallThickness: /wall\s+thickness\s+(\d+(?:\.\d+)?)\s*mm/i,
        nodeDiameter: /node\s+diameter\s+(\d+(?:\.\d+)?)\s*mm/i,
        ligamentThickness: /ligaments?\s+(\d+(?:\.\d+)?)\s*mm\s+thick/i,
        strutThickness: /strut\s+thickness\s+(\d+(?:\.\d+)?)\s*mm/i,
        proximalDiameter: /proximal\s+diameter\s+(\d+(?:\.\d+)?)\s*mm/i,
        distalDiameter: /distal\s+diameter\s+(\d+(?:\.\d+)?)\s*mm/i,
        size: /(\d+(?:\.\d+)?)\s*mm\s+size/i,  
        cellSize: /unit\s+cell\s+(\d+(?:\.\d+)?)\s*mm/i,
        depth: /depth\s+(\d+(?:\.\d+)?)\s*mm/i,
        plenumLength: /plenum.*?(\d+(?:\.\d+)?)\s*mm/i,
        runnerDiameter: /runner.*?(\d+(?:\.\d+)?)\s*mm.*?diameter/i,
        runnerLength: /runner.*?(\d+(?:\.\d+)?)\s*mm.*?length/i,
        runnerSpacing: /spaced\s+(\d+(?:\.\d+)?)\s*mm.*?apart/i,
        diameterFrom: /from\s+(\d+(?:\.\d+)?)\s*mm.*?diameter/i,
        diameterTo: /to\s+(\d+(?:\.\d+)?)\s*mm.*?diameter/i,
        insertDiameter: /insert\s+(\d+(?:\.\d+)?)\s*mm/i,
        drainDiameter: /drain.*?(\d+(?:\.\d+)?)\s*mm/i,
        sensorDiameter: /sensor.*?(\d+(?:\.\d+)?)\s*mm/i,
        finCount: /(\d+)\s+(?:internal\s+)?(?:cooling\s+)?fins?/i,
        finThickness: /fins?\s+(\d+(?:\.\d+)?)\s*mm.*?thick/i,
        portDiameter: /port\s+(\d+(?:\.\d+)?)\s*mm/i,
        filterDiameter: /filter.*?(\d+(?:\.\d+)?)\s*mm/i,
        tubeDiameter: /tube\s+(\d+(?:\.\d+)?)\s*mm/i,
        portSpacingX: /rectangle\s+(\d+(?:\.\d+)?)\s*mm/i,
        portSpacingY: /rectangle.*?x\s+(\d+(?:\.\d+)?)\s*mm/i,
        curveRadius: /radius\s+(\d+(?:\.\d+)?)\s*mm/i,
        injectorCount: /(\d+)\s+injector/i,
        injectorDiameter: /injector.*?(\d+(?:\.\d+)?)\s*mm/i,
        pilotDiameter: /pilot.*?(\d+(?:\.\d+)?)\s*mm/i,
        outerDiameter: /outer\s+diameter\s+(\d+(?:\.\d+)?)\s*mm/i,
        innerDiameter: /inner\s+diameter\s+(\d+(?:\.\d+)?)\s*mm/i
    }

    for (const [paramName, pattern] of Object.entries(dimensionPatterns)) {
        if (params[paramName]) continue // Déjà extrait
        const match = prompt.match(pattern)
        if (match) {
            params[paramName] = parseFloat(match[1])
            console.log(`  ✓ ${paramName}: ${match[1]}`)
        }
    }

    // Fallback: extraire tous les nombres
    if (!template.requiredParams) {
        console.log('  ⚠ No required params')
        return params
    }

    const missing = template.requiredParams.filter(p => params[p] === undefined)
    if (missing.length > 0) {
        const allNumbers = [...prompt.matchAll(/\b(\d+(?:\.\d+)?)\b/g)]
            .map(m => parseFloat(m[1]))
            .filter(n => !isNaN(n) && n > 0)

        console.log(`  ⚠ Missing: ${missing.join(', ')} - using fallback: ${allNumbers.slice(0, missing.length).join(', ')}`)

        let idx = 0
        for (const param of missing) {
            if (idx < allNumbers.length) {
                params[param] = allNumbers[idx++]
            }
        }
    }

    // Détection du type de cellule unitaire
    const cellTypePatterns: Record<string, RegExp[]> = {
        cubic: [/\bcubic\b/i, /\bcube\b/i, /simple cubic/i],
        bcc: [/\bbcc\b/i, /body.centered/i],
        fcc: [/\bfcc\b/i, /face.centered/i],
        octet: [/octet/i, /octahedral/i],
        tetrahedral: [/tetrahedral/i, /tetra\b/i],
        kelvin: [/kelvin/i, /tetrakaidecahedron/i],
        diamond: [/diamond/i],
        gyroid: [/gyroid/i, /TPMS/i]
    }

    for (const [type, patterns] of Object.entries(cellTypePatterns)) {
        for (const pattern of patterns) {
            if (pattern.test(prompt)) {
                params.cellType = type
                console.log(`  ✓ cellType: ${type}`)
                break
            }
        }
        if (params.cellType) break
    }

    console.log(`✅ Final: ${JSON.stringify(params)}\n`)
    return params
}

// ============================================
// GÉNÉRATION DE CODE PAR LLM (Fallback)
// ============================================
async function generateCodeWithLLM(prompt: string): Promise<string> {
    const systemPrompt = `You are a THREE.js code generator. Generate simple, working code.

Rules:
- Define all variables
- Use basic geometries (Cylinder, Box, Sphere)
- Center at origin
- Return complete code

Format:
\`\`\`javascript
const size = 20
function generateModel() {
  const meshes = []
  // ... code
  return meshes
}
\`\`\``

    const response = await fetch(`${OLLAMA_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            model: MODEL,
            stream: false,
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: prompt }
            ],
            options: { temperature: 0.2, num_predict: 1500 }
        })
    })

    if (!response.ok) throw new Error('Ollama error')
    const data: any = await response.json()
    return data.message.content
}

// ============================================
// EXTRACTION & VALIDATION
// ============================================
function extractCode(text: string): string {
    const match = text.match(/```(?:javascript|js)?\s*\n([\s\S]*?)\n```/)
    if (match) return match[1].trim()
    return text.trim()
}

function isValidCode(code: string): boolean {
    return code.length > 30 &&
        code.includes('function generateModel') &&
        code.includes('return meshes')
}

// ============================================
// FALLBACK UNIVERSEL
// ============================================
const UNIVERSAL_FALLBACK = `
const size = 20
const radius = size / 2

function generateModel() {
  const meshes = []
  const geo = new THREE.CylinderGeometry(radius, radius, size, 32)
  const mat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const mesh = new THREE.Mesh(geo, mat)
  mesh.position.y = size / 2
  meshes.push(mesh)
  return meshes
}
`.trim()

// ============================================
// ENDPOINT PRINCIPAL
// ============================================
app.post('/api/generate', async (req, res) => {
    const start = Date.now()

    try {
        const prompt = String(req.body?.natural || '').trim()
        if (!prompt) return res.status(400).json({ error: 'Empty prompt' })

        console.log('\n' + '='.repeat(80))
        console.log('PROMPT:', prompt.substring(0, 80) + '...')

        // Sélection template
        const templateName = selectTemplate(prompt)

        if (templateName) {
            console.log(`✓ Template matched: ${templateName}`)
            console.log('Extracting parameters...')

            const params = await extractParameters(prompt, templateName)

            // Vérification: si aucun paramètre extrait, logger un avertissement
            if (Object.keys(params).length === 0) {
                console.log('⚠️ No parameters extracted, using template defaults')
            }

            const code = TEMPLATES[templateName].generate(params)
            console.log('✓ Code generated from template')
            console.log('='.repeat(80))

            return res.json({
                code,
                success: true,
                method: 'template',
                template: templateName,
                parameters: params,  // Renvoyer les params pour debug
                generationTime: Date.now() - start
            })
        }

        // Pas de template → LLM génère
        console.log('No template matched, trying LLM generation...')
        const rawResponse = await generateCodeWithLLM(prompt)
        const code = extractCode(rawResponse)

        if (isValidCode(code)) {
            console.log('✓ LLM generation successful')
            console.log('='.repeat(80))
            return res.json({
                code,
                success: true,
                method: 'llm',
                generationTime: Date.now() - start
            })
        }

        console.log('LLM failed, using fallback')
        console.log('='.repeat(80))
        return res.json({
            code: UNIVERSAL_FALLBACK,
            success: true,
            method: 'fallback',
            generationTime: Date.now() - start
        })

    } catch (error: any) {
        console.error('Error:', error.message)
        return res.json({
            code: UNIVERSAL_FALLBACK,
            success: true,
            method: 'error_fallback',
            error: error.message
        })
    }
})

app.get('/api/health', (req, res) => {
    res.json({
        status: 'ok',
        model: MODEL,
        version: '12.0-template-based',
        templates: Object.keys(TEMPLATES)
    })
})

app.listen(PORT, () => {
    console.log('\n' + '='.repeat(80))
    console.log('CAD SERVER v12.0 - TEMPLATE-BASED SYSTEM')
    console.log('='.repeat(80))
    console.log(`URL: http://localhost:${PORT}`)
    console.log(`Model: ${MODEL}`)
    console.log(`Templates: ${Object.keys(TEMPLATES).length}`)
    console.log('  - ellipsoid_implant')
    console.log('  - hemispherical_capsule')
    console.log('  - zigzag_stent')
    console.log('  - soft_actuator')
    console.log('  - lattice_cube')
    console.log('='.repeat(80))
    console.log('\nReady - Template-based + LLM fallback\n')
})