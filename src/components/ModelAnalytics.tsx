// src/components/ModelAnalytics.tsx
import React, { useState, useEffect } from 'react'
import { ModelAnalytics as ModelAnalyticsType } from '../types/parameters'
import { ModelValidator } from '../utils/modelValidator'

interface ModelAnalyticsProps {
    meshes: THREE.Mesh[]
    isVisible?: boolean
}

export function ModelAnalytics({ meshes, isVisible = true }: ModelAnalyticsProps) {
    const [analytics, setAnalytics] = useState<ModelAnalyticsType | null>(null)
    const [qualityReport, setQualityReport] = useState<any>(null)
    const [isLoading, setIsLoading] = useState(false)
    const [selectedTab, setSelectedTab] = useState<'overview' | 'quality' | 'printability'>('overview')

    useEffect(() => {
        if (meshes.length > 0) {
            analyzeModel()
        } else {
            setAnalytics(null)
            setQualityReport(null)
        }
    }, [meshes])

    const analyzeModel = async () => {
        setIsLoading(true)
        try {
            // Petit délai pour ne pas bloquer l'UI
            await new Promise(resolve => setTimeout(resolve, 50))

            const modelAnalytics = ModelValidator.generateAnalytics(meshes)
            const quality = ModelValidator.generateQualityReport(meshes)

            setAnalytics(modelAnalytics)
            setQualityReport(quality)
        } catch (error) {
            console.error('Erreur analyse modèle:', error)
        } finally {
            setIsLoading(false)
        }
    }

    if (!isVisible) return null

    if (meshes.length === 0) {
        return (
            <div className="analytics-panel">
                <div className="analytics-empty">
                    <p>📊 Aucun modèle à analyser</p>
                    <small>Générez un modèle pour voir les statistiques</small>
                </div>
            </div>
        )
    }

    if (isLoading || !analytics) {
        return (
            <div className="analytics-panel">
                <div className="analytics-loading">
                    <p>🔍 Analyse en cours...</p>
                </div>
            </div>
        )
    }

    return (
        <div className="analytics-panel">
            <div className="analytics-header">
                <h3>📊 Analytics du Modèle</h3>
                <div className="analytics-tabs">
                    <button
                        className={`tab-button ${selectedTab === 'overview' ? 'active' : ''}`}
                        onClick={() => setSelectedTab('overview')}
                    >
                        Vue d'ensemble
                    </button>
                    <button
                        className={`tab-button ${selectedTab === 'quality' ? 'active' : ''}`}
                        onClick={() => setSelectedTab('quality')}
                    >
                        Qualité
                    </button>
                    <button
                        className={`tab-button ${selectedTab === 'printability' ? 'active' : ''}`}
                        onClick={() => setSelectedTab('printability')}
                    >
                        Impression
                    </button>
                </div>
            </div>

            <div className="analytics-content">
                {selectedTab === 'overview' && (
                    <OverviewTab analytics={analytics} />
                )}
                {selectedTab === 'quality' && qualityReport && (
                    <QualityTab qualityReport={qualityReport} />
                )}
                {selectedTab === 'printability' && (
                    <PrintabilityTab printability={analytics.printability} dimensions={analytics.dimensions} />
                )}
            </div>
        </div>
    )
}

// Onglet Vue d'ensemble
function OverviewTab({ analytics }: { analytics: ModelAnalyticsType }) {
    const formatNumber = (num: number) => {
        return num.toLocaleString('fr-FR')
    }

    const getComplexityColor = (complexity: string) => {
        switch (complexity) {
            case 'Simple': return '#22c55e'
            case 'Moyen': return '#eab308'
            case 'Complexe': return '#f97316'
            case 'Très complexe': return '#ef4444'
            default: return '#6b7280'
        }
    }

    const estimatedPrintTime = Math.round(analytics.totalTriangles / 1000 * 5) // Estimation simplifiée

    return (
        <div className="overview-tab">
            <div className="stats-grid">
                <StatCard
                    icon="🔢"
                    title="Meshes"
                    value={analytics.meshCount.toString()}
                    subtitle="objets 3D"
                />
                <StatCard
                    icon="📐"
                    title="Vertices"
                    value={formatNumber(analytics.totalVertices)}
                    subtitle="points"
                />
                <StatCard
                    icon="🔺"
                    title="Triangles"
                    value={formatNumber(analytics.totalTriangles)}
                    subtitle="faces"
                />
                <StatCard
                    icon="📏"
                    title="Volume"
                    value={`${analytics.estimatedVolume.toFixed(1)}`}
                    subtitle="mm³"
                />
            </div>

            <div className="dimensions-section">
                <h4>🎯 Dimensions</h4>
                <div className="dimensions-grid">
                    <div className="dimension-item">
                        <span className="dimension-label">Largeur:</span>
                        <span className="dimension-value">{analytics.dimensions.width}mm</span>
                    </div>
                    <div className="dimension-item">
                        <span className="dimension-label">Hauteur:</span>
                        <span className="dimension-value">{analytics.dimensions.height}mm</span>
                    </div>
                    <div className="dimension-item">
                        <span className="dimension-label">Profondeur:</span>
                        <span className="dimension-value">{analytics.dimensions.depth}mm</span>
                    </div>
                </div>
            </div>

            <div className="complexity-section">
                <h4>⚡ Complexité</h4>
                <div className="complexity-indicator">
                    <div
                        className="complexity-badge"
                        style={{ backgroundColor: getComplexityColor(analytics.complexity) }}
                    >
                        {analytics.complexity}
                    </div>
                    <div className="complexity-details">
                        <p>Basé sur {formatNumber(analytics.totalTriangles)} triangles</p>
                        <p>Temps d'impression estimé: ~{estimatedPrintTime}min</p>
                    </div>
                </div>
            </div>
        </div>
    )
}

// Onglet Qualité
function QualityTab({ qualityReport }: { qualityReport: any }) {
    const { validation, recommendations, overallScore } = qualityReport

    const getScoreColor = (score: number) => {
        if (score >= 80) return '#22c55e'
        if (score >= 60) return '#eab308'
        if (score >= 40) return '#f97316'
        return '#ef4444'
    }

    return (
        <div className="quality-tab">
            <div className="quality-score">
                <div className="score-circle">
                    <div
                        className="score-value"
                        style={{ color: getScoreColor(overallScore) }}
                    >
                        {overallScore}
                    </div>
                    <div className="score-label">Score</div>
                </div>
                <div className="score-description">
                    {overallScore >= 80 && "✅ Excellente qualité"}
                    {overallScore >= 60 && overallScore < 80 && "⚠️ Qualité correcte"}
                    {overallScore >= 40 && overallScore < 60 && "⚠️ Qualité moyenne"}
                    {overallScore < 40 && "❌ Qualité faible"}
                </div>
            </div>

            {validation.issues.length > 0 && (
                <div className="issues-section">
                    <h4>⚠️ Problèmes détectés</h4>
                    <ul className="issues-list">
                        {validation.issues.map((issue, index) => (
                            <li key={index} className="issue-item">
                                {issue}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {validation.suggestions.length > 0 && (
                <div className="suggestions-section">
                    <h4>💡 Suggestions</h4>
                    <ul className="suggestions-list">
                        {validation.suggestions.map((suggestion, index) => (
                            <li key={index} className="suggestion-item">
                                {suggestion}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {recommendations.length > 0 && (
                <div className="recommendations-section">
                    <h4>🎯 Recommandations</h4>
                    <ul className="recommendations-list">
                        {recommendations.map((rec, index) => (
                            <li key={index} className="recommendation-item">
                                {rec}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    )
}

// Onglet Imprimabilité
function PrintabilityTab({
    printability,
    dimensions
}: {
    printability: any
    dimensions: any
}) {
    const getScoreColor = (score: number) => {
        if (score >= 80) return '#22c55e'
        if (score >= 60) return '#eab308'
        if (score >= 40) return '#f97316'
        return '#ef4444'
    }

    const maxDimension = Math.max(dimensions.width, dimensions.height, dimensions.depth)
    const bedSizeOk = maxDimension <= 200 // Lit d'impression standard
    const minDetailOk = Math.min(dimensions.width, dimensions.height, dimensions.depth) >= 0.4

    return (
        <div className="printability-tab">
            <div className="printability-score">
                <div className="score-circle">
                    <div
                        className="score-value"
                        style={{ color: getScoreColor(printability.score) }}
                    >
                        {printability.score}
                    </div>
                    <div className="score-label">Score 3D</div>
                </div>
            </div>

            <div className="print-checks">
                <h4>🔍 Vérifications</h4>

                <div className="check-list">
                    <CheckItem
                        label="Taille compatible"
                        passed={bedSizeOk}
                        details={`Max: ${maxDimension.toFixed(1)}mm (limite: 200mm)`}
                    />
                    <CheckItem
                        label="Détails imprimables"
                        passed={minDetailOk}
                        details="Épaisseur minimale: 0.4mm"
                    />
                    <CheckItem
                        label="Géométrie stable"
                        passed={printability.score > 60}
                        details="Pas de surplombs excessifs"
                    />
                </div>
            </div>

            {printability.issues.length > 0 && (
                <div className="print-issues">
                    <h4>⚠️ Problèmes d'impression</h4>
                    <ul className="print-issues-list">
                        {printability.issues.map((issue: string, index: number) => (
                            <li key={index} className="print-issue">
                                {issue}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {printability.suggestions.length > 0 && (
                <div className="print-suggestions">
                    <h4>🛠️ Suggestions</h4>
                    <ul className="print-suggestions-list">
                        {printability.suggestions.map((suggestion: string, index: number) => (
                            <li key={index} className="print-suggestion">
                                {suggestion}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            <div className="print-settings">
                <h4>⚙️ Paramètres suggérés</h4>
                <div className="settings-grid">
                    <SettingItem label="Hauteur de couche" value="0.2mm" />
                    <SettingItem label="Remplissage" value="20%" />
                    <SettingItem label="Supports" value={printability.score < 70 ? "Oui" : "Non"} />
                    <SettingItem label="Radeau" value={maxDimension > 50 ? "Recommandé" : "Non"} />
                </div>
            </div>
        </div>
    )
}

// Composants utilitaires
function StatCard({
    icon,
    title,
    value,
    subtitle
}: {
    icon: string
    title: string
    value: string
    subtitle: string
}) {
    return (
        <div className="stat-card">
            <div className="stat-icon">{icon}</div>
            <div className="stat-content">
                <div className="stat-value">{value}</div>
                <div className="stat-title">{title}</div>
                <div className="stat-subtitle">{subtitle}</div>
            </div>
        </div>
    )
}

function CheckItem({
    label,
    passed,
    details
}: {
    label: string
    passed: boolean
    details: string
}) {
    return (
        <div className="check-item">
            <div className="check-status">
                {passed ? '✅' : '❌'}
            </div>
            <div className="check-content">
                <div className="check-label">{label}</div>
                <div className="check-details">{details}</div>
            </div>
        </div>
    )
}

function SettingItem({
    label,
    value
}: {
    label: string
    value: string
}) {
    return (
        <div className="setting-item">
            <span className="setting-label">{label}:</span>
            <span className="setting-value">{value}</span>
        </div>
    )
}