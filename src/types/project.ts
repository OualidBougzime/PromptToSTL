// src/types/project.ts

export interface CADProject {
    id: string
    name: string
    prompt: string
    code: string
    parameters: Record<string, number>
    timestamp: number
    thumbnail?: string
    tags: string[]
    version: string
    analytics?: {
        meshCount: number
        triangleCount: number
        complexity: string
    }
}

export interface ProjectFilter {
    searchTerm: string
    selectedTag: string
    dateRange?: {
        start: Date
        end: Date
    }
}

export interface ProjectStats {
    totalProjects: number
    totalGenerations: number
    averageComplexity: string
    mostUsedTags: string[]
}