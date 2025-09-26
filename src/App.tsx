import * as React from 'react'
import type * as THREE from 'three'
import { CADEngine } from './cad/cadEngine'
import { CADCanvas } from './scene/CADCanvas'
import { exportComplexSTL } from './export/complexSTL'

export default function App() {
    const [naturalPrompt, setNaturalPrompt] = React.useState(
        'Create a gear with 8 teeth and a center hole'
    )
    const [generatedCode, setGeneratedCode] = React.useState('')
    const [meshes, setMeshes] = React.useState<THREE.Mesh[]>([])
    const [isGenerating, setIsGenerating] = React.useState(false)
    const [error, setError] = React.useState('')
    const cadEngine = React.useRef(new CADEngine())

    // Initialize CAD engine on mount
    React.useEffect(() => {
        cadEngine.current.initialize()
    }, [])

    const generateFromNatural = async () => {
        if (!naturalPrompt.trim()) {
            setError('Please enter a description')
            return
        }

        setIsGenerating(true)
        setError('')

        try {
            // Call the LLM API to generate CAD code
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ natural: naturalPrompt })
            })

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`)
            }

            const result = await response.json()

            if (!result.success || !result.code) {
                throw new Error('No code generated from prompt')
            }

            setGeneratedCode(result.code)

            // Execute the generated code
            const newMeshes = await cadEngine.current.executeCADCode(result.code)
            const validatedMeshes = cadEngine.current.validateMeshes(newMeshes)
            const optimizedMeshes = cadEngine.current.optimizeMeshes(validatedMeshes)

            setMeshes(optimizedMeshes)

            if (optimizedMeshes.length === 0) {
                setError('No valid geometry was generated')
            }

        } catch (err) {
            console.error('Generation error:', err)
            setError(err instanceof Error ? err.message : 'Generation failed')

            // Show fallback shape on error
            const fallbackMesh = cadEngine.current.createFallbackShape()
            setMeshes([fallbackMesh])
        } finally {
            setIsGenerating(false)
        }
    }

    const exportSTL = React.useCallback(() => {
        if (meshes.length === 0) {
            alert('No geometry to export')
            return
        }

        try {
            const stl = exportComplexSTL(meshes)
            const blob = new Blob([stl], { type: 'model/stl' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'generated_model.stl'
            a.click()
            URL.revokeObjectURL(url)
        } catch (err) {
            console.error('Export error:', err)
            alert('Export failed: ' + (err instanceof Error ? err.message : 'Unknown error'))
        }
    }, [meshes])

    const saveCode = React.useCallback(() => {
        if (!generatedCode) {
            alert('No code to save')
            return
        }

        const blob = new Blob([generatedCode], { type: 'text/javascript' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'generated_cad_code.js'
        a.click()
        URL.revokeObjectURL(url)
    }, [generatedCode])

    const loadCode = React.useCallback((file: File) => {
        const reader = new FileReader()
        reader.onload = async () => {
            try {
                const code = String(reader.result)
                setGeneratedCode(code)

                // Execute the loaded code
                const newMeshes = await cadEngine.current.executeCADCode(code)
                const validatedMeshes = cadEngine.current.validateMeshes(newMeshes)
                const optimizedMeshes = cadEngine.current.optimizeMeshes(validatedMeshes)

                setMeshes(optimizedMeshes)
                setError('')
            } catch (e) {
                console.error('Code loading error:', e)
                setError('Failed to execute loaded code')
            }
        }
        reader.readAsText(file)
    }, [])

    const clearAll = () => {
        setNaturalPrompt('')
        setGeneratedCode('')
        setMeshes([])
        setError('')
    }

    const useTemplate = (template: string) => {
        const templates = {
            'gear': 'Create a gear with 8 teeth and a center hole',
            'bracket': 'Create a mounting bracket with screw holes',
            'enclosure': 'Create a rectangular enclosure with a lid',
            'connector': 'Create a pipe connector with threads',
            'housing': 'Create a motor housing with mounting flanges',
            'tree': 'Create a tree with trunk, branches and leaves using multiple meshes',
            'human': 'Create a human figure with head, body, arms and legs',
            'car': 'Create a simple car with body, cabin and wheels',
            'house': 'Create a house with walls, roof and windows'
        }
        setNaturalPrompt(templates[template as keyof typeof templates] || template)
    }

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: '350px 1fr',
            height: '100vh',
            gap: '1px',
            backgroundColor: '#ddd'
        }}>
            {/* Left Panel - Controls */}
            <div style={{
                backgroundColor: 'white',
                padding: '16px',
                overflowY: 'auto',
                display: 'grid',
                gap: '16px',
                gridTemplateRows: 'auto auto auto 1fr auto'
            }}>
                {/* Natural Language Input */}
                <div className="panel">
                    <label>Describe what you want to create:</label>
                    <textarea
                        className="textarea"
                        rows={4}
                        value={naturalPrompt}
                        onChange={(e) => setNaturalPrompt(e.target.value)}
                        placeholder="e.g., Create a gear with 12 teeth and a square center hole"
                        disabled={isGenerating}
                    />
                </div>

                {/* Template Buttons */}
                <div className="panel">
                    <label>Quick Templates:</label>
                    <div style={{ display: 'grid', gap: '4px', gridTemplateColumns: '1fr 1fr' }}>
                        <button
                            className="button small"
                            onClick={() => useTemplate('gear')}
                            disabled={isGenerating}
                        >
                            Gear
                        </button>
                        <button
                            className="button small"
                            onClick={() => useTemplate('bracket')}
                            disabled={isGenerating}
                        >
                            Bracket
                        </button>
                        <button
                            className="button small"
                            onClick={() => useTemplate('enclosure')}
                            disabled={isGenerating}
                        >
                            Enclosure
                        </button>
                        <button
                            className="button small"
                            onClick={() => useTemplate('connector')}
                            disabled={isGenerating}
                        >
                            Connector
                        </button>
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="toolbar" style={{ flexDirection: 'column', gap: '8px' }}>
                    <button
                        className="button primary"
                        onClick={generateFromNatural}
                        disabled={isGenerating || !naturalPrompt.trim()}
                        style={{ width: '100%' }}
                    >
                        {isGenerating ? 'Generating...' : 'Generate 3D Model'}
                    </button>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                        <button
                            className="button"
                            onClick={exportSTL}
                            disabled={meshes.length === 0}
                        >
                            Export STL
                        </button>
                        <button
                            className="button"
                            onClick={saveCode}
                            disabled={!generatedCode}
                        >
                            Save Code
                        </button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                        <label className="button" style={{ textAlign: 'center' }}>
                            Load Code
                            <input
                                type="file"
                                accept=".js,.txt"
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                    const f = e.target.files?.[0]
                                    if (f) loadCode(f)
                                }}
                            />
                        </label>
                        <button
                            className="button secondary"
                            onClick={clearAll}
                        >
                            Clear All
                        </button>
                    </div>
                </div>

                {/* Generated Code Display */}
                <div className="panel" style={{ flex: 1, minHeight: 0 }}>
                    <details open={!!generatedCode}>
                        <summary>Generated Code ({generatedCode ? generatedCode.split('\n').length : 0} lines)</summary>
                        <pre style={{
                            fontSize: '11px',
                            backgroundColor: '#f5f5f5',
                            padding: '8px',
                            borderRadius: '4px',
                            overflow: 'auto',
                            maxHeight: '200px',
                            whiteSpace: 'pre-wrap'
                        }}>
                            {generatedCode || 'No code generated yet'}
                        </pre>
                    </details>
                </div>

                {/* Status/Error Display */}
                {error && (
                    <div style={{
                        padding: '8px',
                        backgroundColor: '#ffebee',
                        border: '1px solid #ffcdd2',
                        borderRadius: '4px',
                        fontSize: '14px',
                        color: '#c62828'
                    }}>
                        {error}
                    </div>
                )}

                {meshes.length > 0 && !error && (
                    <div style={{
                        padding: '8px',
                        backgroundColor: '#e8f5e8',
                        border: '1px solid #c8e6c9',
                        borderRadius: '4px',
                        fontSize: '14px',
                        color: '#2e7d32'
                    }}>
                        Generated {meshes.length} mesh{meshes.length !== 1 ? 'es' : ''}
                    </div>
                )}
            </div>

            {/* Right Panel - 3D View */}
            <div style={{ backgroundColor: 'white' }}>
                <CADCanvas meshes={meshes} />
            </div>
        </div>
    )
}