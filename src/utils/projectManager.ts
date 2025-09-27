// src/utils/projectManager.ts
import { CADProject, ProjectStats } from '../types/project'

export class ProjectManager {
    private static readonly STORAGE_KEY = 'cad_projects_v2'
    private static readonly MAX_PROJECTS = 100
    private static readonly VERSION = '2.0.0'

    static saveProject(project: Omit<CADProject, 'id' | 'timestamp'>): CADProject {
        const projects = this.getProjects()

        const newProject: CADProject = {
            ...project,
            id: this.generateId(),
            timestamp: Date.now(),
            version: this.VERSION,
            tags: project.tags || this.generateAutoTags(project.prompt)
        }

        projects.unshift(newProject)

        // Limiter le nombre de projets
        if (projects.length > this.MAX_PROJECTS) {
            projects.splice(this.MAX_PROJECTS)
        }

        this.saveToStorage(projects)
        return newProject
    }

    static getProjects(): CADProject[] {
        try {
            const stored = localStorage.getItem(this.STORAGE_KEY)
            if (!stored) return []

            const projects = JSON.parse(stored)

            // Migration des anciens projets
            return projects.map((p: any) => ({
                ...p,
                version: p.version || '1.0.0',
                tags: p.tags || [],
                parameters: p.parameters || {}
            }))
        } catch (error) {
            console.error('Error loading projects:', error)
            return []
        }
    }

    static getProject(id: string): CADProject | null {
        const projects = this.getProjects()
        return projects.find(p => p.id === id) || null
    }

    static updateProject(id: string, updates: Partial<CADProject>): boolean {
        const projects = this.getProjects()
        const index = projects.findIndex(p => p.id === id)

        if (index === -1) return false

        projects[index] = {
            ...projects[index],
            ...updates,
            timestamp: Date.now()
        }

        this.saveToStorage(projects)
        return true
    }

    static deleteProject(id: string): boolean {
        const projects = this.getProjects()
        const filtered = projects.filter(p => p.id !== id)

        if (filtered.length === projects.length) return false

        this.saveToStorage(filtered)
        return true
    }

    static duplicateProject(id: string): CADProject | null {
        const original = this.getProject(id)
        if (!original) return null

        const duplicate: Omit<CADProject, 'id' | 'timestamp'> = {
            ...original,
            name: `${original.name} (Copie)`,
            tags: [...original.tags, 'copie']
        }

        return this.saveProject(duplicate)
    }

    static searchProjects(query: string): CADProject[] {
        const projects = this.getProjects()
        const lowerQuery = query.toLowerCase()

        return projects.filter(project =>
            project.name.toLowerCase().includes(lowerQuery) ||
            project.prompt.toLowerCase().includes(lowerQuery) ||
            project.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
        )
    }

    static getProjectsByTag(tag: string): CADProject[] {
        const projects = this.getProjects()
        return projects.filter(project =>
            project.tags.includes(tag)
        )
    }

    static getAllTags(): string[] {
        const projects = this.getProjects()
        const allTags = new Set<string>()

        projects.forEach(project => {
            project.tags.forEach(tag => allTags.add(tag))
        })

        return Array.from(allTags).sort()
    }

    static getProjectStats(): ProjectStats {
        const projects = this.getProjects()

        const tagCounts = new Map<string, number>()
        let totalTriangles = 0

        projects.forEach(project => {
            project.tags.forEach(tag => {
                tagCounts.set(tag, (tagCounts.get(tag) || 0) + 1)
            })

            if (project.analytics?.triangleCount) {
                totalTriangles += project.analytics.triangleCount
            }
        })

        const mostUsedTags = Array.from(tagCounts.entries())
            .sort(([, a], [, b]) => b - a)
            .slice(0, 5)
            .map(([tag]) => tag)

        return {
            totalProjects: projects.length,
            totalGenerations: projects.length, // Simplified
            averageComplexity: this.calculateAverageComplexity(projects),
            mostUsedTags
        }
    }

    static exportProjects(): string {
        const projects = this.getProjects()
        const exportData = {
            version: this.VERSION,
            exportDate: new Date().toISOString(),
            projects
        }

        return JSON.stringify(exportData, null, 2)
    }

    static importProjects(jsonData: string): { success: boolean; imported: number; errors: string[] } {
        try {
            const data = JSON.parse(jsonData)
            const errors: string[] = []
            let imported = 0

            if (!Array.isArray(data.projects)) {
                // Format legacy
                if (Array.isArray(data)) {
                    data.projects = data
                } else {
                    throw new Error('Format de données invalide')
                }
            }

            const existingProjects = this.getProjects()
            const existingIds = new Set(existingProjects.map(p => p.id))

            for (const project of data.projects) {
                try {
                    // Valider la structure du projet
                    if (!this.validateProjectStructure(project)) {
                        errors.push(`Projet invalide: ${project.name || 'Sans nom'}`)
                        continue
                    }

                    // Éviter les doublons
                    if (existingIds.has(project.id)) {
                        project.id = this.generateId()
                    }

                    // Migrer si nécessaire
                    const migratedProject = this.migrateProject(project)
                    existingProjects.push(migratedProject)
                    imported++

                } catch (error) {
                    errors.push(`Erreur import projet: ${error}`)
                }
            }

            // Limiter le nombre total
            if (existingProjects.length > this.MAX_PROJECTS) {
                existingProjects.splice(this.MAX_PROJECTS)
            }

            this.saveToStorage(existingProjects)

            return {
                success: true,
                imported,
                errors
            }

        } catch (error) {
            return {
                success: false,
                imported: 0,
                errors: [`Erreur parsing JSON: ${error}`]
            }
        }
    }

    static clearAllProjects(): boolean {
        try {
            localStorage.removeItem(this.STORAGE_KEY)
            return true
        } catch (error) {
            console.error('Error clearing projects:', error)
            return false
        }
    }

    private static generateId(): string {
        return Date.now().toString(36) + Math.random().toString(36).substr(2)
    }

    private static generateAutoTags(prompt: string): string[] {
        const tags: string[] = ['auto']
        const lowerPrompt = prompt.toLowerCase()

        // Tags basés sur les mots-clés
        const tagMap = {
            'gear': 'engrenage',
            'bracket': 'support',
            'enclosure': 'boîtier',
            'box': 'boîte',
            'connector': 'connecteur',
            'housing': 'logement',
            'mount': 'montage',
            'clamp': 'serre-joint',
            'tool': 'outil',
            'screw': 'visserie',
            'bolt': 'boulon',
            'nut': 'écrou',
            'washer': 'rondelle',
            'spring': 'ressort',
            'bearing': 'roulement',
            'pulley': 'poulie',
            'wheel': 'roue',
            'shaft': 'arbre',
            'pipe': 'tuyau',
            'tube': 'tube',
            'cylinder': 'cylindre',
            'sphere': 'sphère',
            'cube': 'cube',
            'cone': 'cône'
        }

        for (const [english, french] of Object.entries(tagMap)) {
            if (lowerPrompt.includes(english)) {
                tags.push(french)
            }
        }

        // Tags de complexité
        if (lowerPrompt.length > 100) tags.push('complexe')
        if (lowerPrompt.includes('thread') || lowerPrompt.includes('screw')) tags.push('visserie')
        if (lowerPrompt.includes('hole') || lowerPrompt.includes('mount')) tags.push('montage')

        return tags
    }

    private static calculateAverageComplexity(projects: CADProject[]): string {
        if (projects.length === 0) return 'Simple'

        const complexityScores = { 'Simple': 1, 'Moyen': 2, 'Complexe': 3, 'Très complexe': 4 }
        let totalScore = 0
        let counted = 0

        projects.forEach(project => {
            if (project.analytics?.complexity) {
                totalScore += complexityScores[project.analytics.complexity as keyof typeof complexityScores] || 1
                counted++
            }
        })

        if (counted === 0) return 'Simple'

        const average = totalScore / counted
        if (average < 1.5) return 'Simple'
        if (average < 2.5) return 'Moyen'
        if (average < 3.5) return 'Complexe'
        return 'Très complexe'
    }

    private static validateProjectStructure(project: any): boolean {
        return (
            typeof project.name === 'string' &&
            typeof project.prompt === 'string' &&
            typeof project.code === 'string' &&
            typeof project.id === 'string'
        )
    }

    private static migrateProject(project: any): CADProject {
        return {
            ...project,
            version: this.VERSION,
            tags: project.tags || [],
            parameters: project.parameters || {},
            timestamp: project.timestamp || Date.now()
        }
    }

    private static saveToStorage(projects: CADProject[]): void {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(projects))
        } catch (error) {
            console.error('Error saving projects:', error)

            // Si quota dépassé, supprimer les plus anciens
            if (error instanceof DOMException && error.code === 22) {
                const reducedProjects = projects.slice(0, Math.floor(projects.length * 0.8))
                localStorage.setItem(this.STORAGE_KEY, JSON.stringify(reducedProjects))
            }
        }
    }
}