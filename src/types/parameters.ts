// src/types/parameters.ts

export interface Parameter {
    name: string
    value: number
    min: number
    max: number
    step: number
    unit?: string
    description?: string
    category?: string
}

export interface ParametricModel {
    originalCode: string
    parametricCode: string
    parameters: Parameter[]
    generateFunction: string
}

export interface ModelValidation {
    isValid: boolean
    issues: string[]
    suggestions: string[]
    triangleCount: number
    vertexCount: number
}

export interface ModelAnalytics {
    meshCount: number
    totalVertices: number
    totalTriangles: number
    estimatedVolume: number
    dimensions: {
        width: number
        height: number
        depth: number
    }
    complexity: 'Simple' | 'Moyen' | 'Complexe' | 'Très complexe'
    printability: {
        score: number
        issues: string[]
        suggestions: string[]
    }
}