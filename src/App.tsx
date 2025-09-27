// src/App.tsx - Version Améliorée
import * as React from 'react'
import type * as THREE from 'three'
import { CADEngine } from './cad/cadEngine'
import { CADCanvas } from './scene/CADCanvas'
import { OptimizedSTLExporter, downloadSTL } from './export/complexSTL'
import { ParameterSliders } from './components/ParameterSliders'
import { ProjectHistory } from './components/ProjectHistory'
import { ModelAnalytics } from './components/ModelAnalytics'
import { ParametricEngine } from './cad/parametricEngine'
import { ModelValidator } from './utils/modelValidator'
import { ProjectManager } from './utils/projectManager'
import { ADVANCED_TEMPLATES, TemplateManager } from './templates/advancedTemplates'
import { Parameter, ParametricModel } from './types/parameters'
import { CADProject } from './types/project'

interface AppState {
    naturalPrompt: string
    generatedCode: string
    meshes: THREE.Mesh[]
    parameters: Parameter[]
    parameterValues: Record<string, number>
    parametricModel: ParametricModel | null
    isGenerating: boolean
    error: string
    selectedTemplate: string
    showAdvancedMode: boolean
    activePanel: 'templates' | 'parameters' | 'history' | 'analytics'
}

export default function App() {
    // État principal de l'application
    const [state, setState] = React.useState<AppState>({
        naturalPrompt: 'Create a gear with 12 teeth and a center hole',
        generatedCode: '',
        meshes: [],
        parameters: [],
        parameterValues: {},
        parametricModel: null,
        isGenerating: false,
        error: '',
        selectedTemplate: '',
        showAdvancedMode: false,
        activePanel: 'templates'
    })

    // Refs pour les moteurs
    const cadEngine = React.useRef(new CADEngine({
        enableCSG: true,
        enableAdvancedShapes: true,
        enableParametricExtraction: true,
        autoOptimize: true
    }))
    const parametricEngine = React.useRef(new ParametricEngine())

    // Initialisation au montage
    React.useEffect(() => {
        cadEngine.current.initialize()
    }, [])

    // Génération à partir du prompt naturel
    const generateFromNatural = async () => {
        if (!state.naturalPrompt.trim()) {
            updateState({ error: 'Veuillez entrer une description' })
            return
        }

        updateState({ isGenerating: true, error: '' })

        try {
            // Appel à l'API LLM
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ natural: state.naturalPrompt })
            })

            if (!response.ok) {
                throw new Error(`Erreur serveur: ${response.status}`)
            }

            const result = await response.json()

            if (!result.success || !result.code) {
                throw new Error('Aucun code généré')
            }

            updateState({ generatedCode: result.code })

            // Exécution du code et extraction des paramètres
            await executeGeneratedCode(result.code)

        } catch (err) {
            console.error('Erreur génération:', err)
            const errorMessage = err instanceof Error ? err.message : 'Génération échouée'
            updateState({
                error: errorMessage,
                meshes: [cadEngine.current.createFallbackShape()]
            })
        } finally {
            updateState({ isGenerating: false })
        }
    }

    // Exécution du code généré
    const executeGeneratedCode = async (code: string) => {
        try {
            // Exécution du code
            const newMeshes = await cadEngine.current.executeCADCode(code)
            const validatedMeshes = cadEngine.current.validateMeshes(newMeshes)
            const optimizedMeshes = cadEngine.current.optimizeMeshes(validatedMeshes)

            // Extraction des paramètres
            const extractedParameters = cadEngine.current.extractParameters(code)
            const defaultValues = extractedParameters.reduce((acc, param) => {
                acc[param.name] = param.value
                return acc
            }, {} as Record<string, number>)

            // Génération du modèle paramétrique
            let parametricModel: ParametricModel | null = null
            try {
                parametricModel = cadEngine.current.generateParametricModel(code)
            } catch (error) {
                console.warn('Impossible de créer le modèle paramétrique:', error)
            }

            updateState({
                meshes: optimizedMeshes,
                parameters: extractedParameters,
                parameterValues: defaultValues,
                parametricModel,
                error: optimizedMeshes.length === 0 ? 'Aucune géométrie valide générée' : ''
            })

        } catch (error) {
            console.error('Erreur exécution code:', error)
            updateState({
                error: 'Erreur lors de l\'exécution du code',
                meshes: [cadEngine.current.createFallbackShape()]
            })
        }
    }

    // Changement de paramètre
    const handleParameterChange = async (name: string, value: number) => {
        const newValues = { ...state.parameterValues, [name]: value }
        updateState({ parameterValues: newValues })

        // Régénération en temps réel si modèle paramétrique disponible
        if (state.parametricModel) {
            try {
                const newMeshes = await cadEngine.current.executeWithParameters(
                    state.parametricModel,
                    newValues
                )
                updateState({ meshes: newMeshes })
            } catch (error) {
                console.error('Erreur régénération paramétrique:', error)
            }
        }
    }

    // Application en lot des changements de paramètres
    const handleBatchParameterChange = async (newValues: Record<string, number>) => {
        updateState({ parameterValues: newValues, isGenerating: true })

        if (state.parametricModel) {
            try {
                const newMeshes = await cadEngine.current.executeWithParameters(
                    state.parametricModel,
                    newValues
                )
                updateState({ meshes: newMeshes })
            } catch (error) {
                console.error('Erreur régénération batch:', error)
            }
        }

        updateState({ isGenerating: false })
    }

    // Sélection de template
    const handleTemplateSelect = (templateId: string) => {
        const template = TemplateManager.getTemplateById(templateId)
        if (template) {
            updateState({
                selectedTemplate: templateId,
                naturalPrompt: template.prompt
            })
        }
    }

    // Utilisation d'un template avec paramètres
    const useTemplateWithParams = (templateId: string, params: Record<string, any>) => {
        const template = TemplateManager.getTemplateById(templateId)
        if (template) {
            const interpolatedPrompt = TemplateManager.interpolateTemplate(template, params)
            updateState({
                naturalPrompt: interpolatedPrompt,
                selectedTemplate: templateId
            })
        }
    }

    // Export STL
    const exportSTL = React.useCallback((format: 'binary' | 'ascii' = 'binary') => {
        if (state.meshes.length === 0) {
            alert('Aucune géométrie à exporter')
            return
        }

        try {
            const filename = `model_${Date.now()}.stl`
            downloadSTL(state.meshes, filename, {
                binary: format === 'binary',
                mergeVertices: true,
                smoothNormals: false,
                scale: 1,
                units: 'mm'
            })
        } catch (err) {
            console.error('Erreur export:', err)
            alert('Erreur lors de l\'export: ' + (err instanceof Error ? err.message : 'Erreur inconnue'))
        }
    }, [state.meshes])

    // Sauvegarde du code
    const saveCode = React.useCallback(() => {
        if (!state.generatedCode) {
            alert('Aucun code à sauvegarder')
            return
        }

        const blob = new Blob([state.generatedCode], { type: 'text/javascript' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `cad_model_${Date.now()}.js`
        a.click()
        URL.revokeObjectURL(url)
    }, [state.generatedCode])

    // Chargement d'un fichier de code
    const loadCode = React.useCallback((file: File) => {
        const reader = new FileReader()
        reader.onload = async () => {
            try {
                const code = String(reader.result)
                updateState({ generatedCode: code })
                await executeGeneratedCode(code)
            } catch (e) {
                console.error('Erreur chargement code:', e)
                updateState({ error: 'Échec du chargement du code' })
            }
        }
        reader.readAsText(file)
    }, [])

    // Gestion des projets
    const handleSaveProject = (): CADProject | null => {
        if (!state.generatedCode || !state.naturalPrompt) {
            alert('Aucun projet à sauvegarder')
            return null
        }

        try {
            const analytics = ModelValidator.generateAnalytics(state.meshes)

            const project = ProjectManager.saveProject({
                name: generateProjectName(state.naturalPrompt),
                prompt: state.naturalPrompt,
                code: state.generatedCode,
                parameters: state.parameterValues,
                tags: generateProjectTags(state.naturalPrompt),
                analytics: {
                    meshCount: analytics.meshCount,
                    triangleCount: analytics.totalTriangles,
                    complexity: analytics.complexity
                }
            })

            return project
        } catch (error) {
            console.error('Erreur sauvegarde projet:', error)
            alert('Erreur lors de la sauvegarde')
            return null
        }
    }

    const handleLoadProject = (project: CADProject) => {
        updateState({
            naturalPrompt: project.prompt,
            generatedCode: project.code,
            parameterValues: project.parameters || {}
        })

        executeGeneratedCode(project.code)
    }

    // Remise à zéro
    const clearAll = () => {
        updateState({
            naturalPrompt: '',
            generatedCode: '',
            meshes: [],
            parameters: [],
            parameterValues: {},
            parametricModel: null,
            error: '',
            selectedTemplate: ''
        })
    }

    // Fonction utilitaire pour mise à jour d'état
    const updateState = (newState: Partial<AppState>) => {
        setState(prevState => ({ ...prevState, ...newState }))
    }

    return (
        <div className="app-container">
            {/* Barre de navigation */}
            <nav className="app-nav">
                <div className="nav-brand">
                    <h1>🏗️ CAD Generator Pro</h1>
                    <span className="version">v2.0</span>
                </div>

                <div className="nav-stats">
                    {state.meshes.length > 0 && (
                        <span className="mesh-count">
                            {state.meshes.length} mesh{state.meshes.length > 1 ? 'es' : ''}
                        </span>
                    )}
                </div>

                <div className="nav-actions">
                    <button
                        className={`nav-button ${state.showAdvancedMode ? 'active' : ''}`}
                        onClick={() => updateState({ showAdvancedMode: !state.showAdvancedMode })}
                    >
                        Mode Avancé
                    </button>
                </div>
            </nav>

            <div className="app-layout">
                {/* Panneau gauche */}
                <div className="left-panel">
                    <div className="panel-tabs">
                        <button
                            className={`tab-button ${state.activePanel === 'templates' ? 'active' : ''}`}
                            onClick={() => updateState({ activePanel: 'templates' })}
                        >
                            📋 Templates
                        </button>
                        <button
                            className={`tab-button ${state.activePanel === 'parameters' ? 'active' : ''}`}
                            onClick={() => updateState({ activePanel: 'parameters' })}
                        >
                            🎛️ Paramètres
                        </button>
                        <button
                            className={`tab-button ${state.activePanel === 'history' ? 'active' : ''}`}
                            onClick={() => updateState({ activePanel: 'history' })}
                        >
                            📁 Historique
                        </button>
                        {state.showAdvancedMode && (
                            <button
                                className={`tab-button ${state.activePanel === 'analytics' ? 'active' : ''}`}
                                onClick={() => updateState({ activePanel: 'analytics' })}
                            >
                                📊 Analytics
                            </button>
                        )}
                    </div>

                    <div className="panel-content">
                        {state.activePanel === 'templates' && (
                            <TemplatesPanel
                                selectedTemplate={state.selectedTemplate}
                                onSelectTemplate={handleTemplateSelect}
                                onUseTemplate={useTemplateWithParams}
                            />
                        )}

                        {state.activePanel === 'parameters' && (
                            <ParameterSliders
                                parameters={state.parameters}
                                values={state.parameterValues}
                                onParameterChange={handleParameterChange}
                                onBatchChange={handleBatchParameterChange}
                                isGenerating={state.isGenerating}
                            />
                        )}

                        {state.activePanel === 'history' && (
                            <ProjectHistory
                                onLoadProject={handleLoadProject}
                                onSaveCurrentProject={handleSaveProject}
                                currentProject={{
                                    name: generateProjectName(state.naturalPrompt),
                                    prompt: state.naturalPrompt,
                                    code: state.generatedCode,
                                    parameters: state.parameterValues
                                }}
                            />
                        )}

                        {state.activePanel === 'analytics' && (
                            <ModelAnalytics
                                meshes={state.meshes}
                                isVisible={true}
                            />
                        )}
                    </div>
                </div>

                {/* Panneau central */}
                <div className="center-panel">
                    {/* Zone de prompt */}
                    <div className="prompt-section">
                        <div className="prompt-input-container">
                            <textarea
                                className="prompt-input"
                                rows={3}
                                value={state.naturalPrompt}
                                onChange={(e) => updateState({ naturalPrompt: e.target.value })}
                                placeholder="Décrivez ce que vous voulez créer... (ex: Create a gear with 12 teeth and a center hole)"
                                disabled={state.isGenerating}
                            />

                            <button
                                className="generate-button"
                                onClick={generateFromNatural}
                                disabled={state.isGenerating || !state.naturalPrompt.trim()}
                            >
                                {state.isGenerating ? (
                                    <>⏳ Génération...</>
                                ) : (
                                    <>🚀 Générer Modèle 3D</>
                                )}
                            </button>
                        </div>

                        {/* Barre d'actions */}
                        <div className="action-bar">
                            <div className="action-group">
                                <button
                                    className="action-button primary"
                                    onClick={() => exportSTL('binary')}
                                    disabled={state.meshes.length === 0}
                                    title="Exporter en STL binaire (recommandé)"
                                >
                                    📤 Export STL
                                </button>

                                {state.showAdvancedMode && (
                                    <button
                                        className="action-button"
                                        onClick={() => exportSTL('ascii')}
                                        disabled={state.meshes.length === 0}
                                        title="Exporter en STL texte"
                                    >
                                        📄 STL ASCII
                                    </button>
                                )}
                            </div>

                            <div className="action-group">
                                <button
                                    className="action-button"
                                    onClick={saveCode}
                                    disabled={!state.generatedCode}
                                >
                                    💾 Code
                                </button>

                                <label className="action-button">
                                    📁 Charger
                                    <input
                                        type="file"
                                        accept=".js,.txt"
                                        style={{ display: 'none' }}
                                        onChange={(e) => {
                                            const file = e.target.files?.[0]
                                            if (file) loadCode(file)
                                        }}
                                    />
                                </label>

                                <button
                                    className="action-button secondary"
                                    onClick={clearAll}
                                >
                                    🗑️ Reset
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Vue 3D */}
                    <div className="viewport-container">
                        <CADCanvas meshes={state.meshes} />

                        {/* Overlay d'informations */}
                        {state.meshes.length === 0 && !state.isGenerating && (
                            <div className="viewport-overlay">
                                <div className="welcome-message">
                                    <div className="welcome-icon">🏗️</div>
                                    <h2>CAD Generator Pro</h2>
                                    <p>Générez des modèles 3D à partir de descriptions textuelles</p>
                                    <div className="welcome-features">
                                        <span>✨ Paramètres ajustables</span>
                                        <span>📊 Analytics avancées</span>
                                        <span>💾 Historique des projets</span>
                                        <span>🎯 Templates prédéfinis</span>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Code généré */}
                    {state.showAdvancedMode && state.generatedCode && (
                        <div className="code-panel">
                            <details open={false}>
                                <summary>
                                    Code généré ({state.generatedCode.split('\n').length} lignes)
                                </summary>
                                <pre className="code-display">
                                    <code>{state.generatedCode}</code>
                                </pre>
                            </details>
                        </div>
                    )}
                </div>
            </div>

            {/* Messages d'état */}
            {state.error && (
                <div className="status-message error">
                    <span>❌ {state.error}</span>
                    <button onClick={() => updateState({ error: '' })}>×</button>
                </div>
            )}

            {state.meshes.length > 0 && !state.error && (
                <div className="status-message success">
                    <span>✅ {state.meshes.length} objet{state.meshes.length > 1 ? 's' : ''} généré{state.meshes.length > 1 ? 's' : ''}</span>
                </div>
            )}
        </div>
    )
}

// Composant des templates
function TemplatesPanel({
    selectedTemplate,
    onSelectTemplate,
    onUseTemplate
}: {
    selectedTemplate: string
    onSelectTemplate: (id: string) => void
    onUseTemplate: (id: string, params: Record<string, any>) => void
}) {
    const [selectedCategory, setSelectedCategory] = React.useState(ADVANCED_TEMPLATES[0]?.name || '')
    const [searchQuery, setSearchQuery] = React.useState('')

    const filteredTemplates = React.useMemo(() => {
        if (searchQuery) {
            return TemplateManager.searchTemplates(searchQuery)
        }
        return TemplateManager.getTemplatesByCategory(selectedCategory)
    }, [selectedCategory, searchQuery])

    return (
        <div className="templates-panel">
            <div className="templates-header">
                <h3>📋 Templates</h3>
                <input
                    type="text"
                    className="template-search"
                    placeholder="🔍 Rechercher..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                />
            </div>

            {!searchQuery && (
                <div className="template-categories">
                    {ADVANCED_TEMPLATES.map(category => (
                        <button
                            key={category.name}
                            className={`category-button ${selectedCategory === category.name ? 'active' : ''}`}
                            onClick={() => setSelectedCategory(category.name)}
                            title={category.description}
                        >
                            {category.icon} {category.name}
                        </button>
                    ))}
                </div>
            )}

            <div className="templates-list">
                {filteredTemplates.map(template => (
                    <div
                        key={template.id}
                        className={`template-item ${selectedTemplate === template.id ? 'selected' : ''}`}
                    >
                        <div className="template-info">
                            <h4 className="template-name">{template.name}</h4>
                            <p className="template-description">{template.description}</p>
                            <div className="template-meta">
                                <span className={`difficulty ${template.difficulty.toLowerCase()}`}>
                                    {template.difficulty}
                                </span>
                                <span className="estimated-time">⏱️ {template.estimatedTime}</span>
                            </div>
                        </div>

                        <div className="template-actions">
                            <button
                                className="template-action-button"
                                onClick={() => onSelectTemplate(template.id)}
                            >
                                Utiliser
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// Fonctions utilitaires
function generateProjectName(prompt: string): string {
    const words = prompt.toLowerCase().split(' ')
    const importantWords = words.filter(word =>
        word.length > 3 &&
        !['create', 'make', 'build', 'with', 'that', 'this', 'and', 'for'].includes(word)
    )

    const name = importantWords.slice(0, 3).join(' ')
    return name.charAt(0).toUpperCase() + name.slice(1) || 'Nouveau Projet'
}

function generateProjectTags(prompt: string): string[] {
    const tags = ['auto-généré']
    const lowerPrompt = prompt.toLowerCase()

    if (lowerPrompt.includes('gear')) tags.push('engrenage')
    if (lowerPrompt.includes('bracket')) tags.push('support')
    if (lowerPrompt.includes('enclosure') || lowerPrompt.includes('box')) tags.push('boîtier')
    if (lowerPrompt.includes('connector')) tags.push('connecteur')
    if (lowerPrompt.includes('tool')) tags.push('outil')

    return tags
}