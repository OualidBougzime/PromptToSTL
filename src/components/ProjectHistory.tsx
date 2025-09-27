// src/components/ProjectHistory.tsx - Version corrigée
import React, { useState, useEffect, useCallback, useRef } from 'react'
import { CADProject, ProjectFilter } from '../types/project'
import { ProjectManager } from '../utils/projectManager'

interface ProjectHistoryProps {
    onLoadProject: (project: CADProject) => void
    onSaveCurrentProject: () => CADProject | null
    currentProject?: {
        name: string
        prompt: string
        code: string
        parameters: Record<string, number>
    }
}

export function ProjectHistory({
    onLoadProject,
    onSaveCurrentProject,
    currentProject
}: ProjectHistoryProps) {
    const [projects, setProjects] = useState<CADProject[]>([])
    const [filter, setFilter] = useState<ProjectFilter>({
        searchTerm: '',
        selectedTag: ''
    })
    const [showSaveDialog, setShowSaveDialog] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)

    useEffect(() => {
        loadProjects()
    }, [])

    const loadProjects = useCallback(() => {
        setIsLoading(true)
        try {
            const loadedProjects = ProjectManager.getProjects()
            setProjects(loadedProjects)
        } catch (error) {
            console.error('Error loading projects:', error)
        } finally {
            setIsLoading(false)
        }
    }, [])

    const handleSaveProject = useCallback((customName?: string) => {
        try {
            const saved = onSaveCurrentProject()
            if (saved) {
                if (customName) {
                    ProjectManager.updateProject(saved.id, { name: customName })
                }
                loadProjects()
                setShowSaveDialog(false)
                return true
            }
            return false
        } catch (error) {
            console.error('Error saving project:', error)
            return false
        }
    }, [onSaveCurrentProject, loadProjects])

    const handleDeleteProject = useCallback((id: string, name: string) => {
        if (confirm(`Supprimer le projet "${name}" ?`)) {
            if (ProjectManager.deleteProject(id)) {
                loadProjects()
            }
        }
    }, [loadProjects])

    const handleDuplicateProject = useCallback((id: string) => {
        try {
            const duplicated = ProjectManager.duplicateProject(id)
            if (duplicated) {
                loadProjects()
            }
        } catch (error) {
            console.error('Error duplicating project:', error)
        }
    }, [loadProjects])

    const handleExportProjects = useCallback(() => {
        try {
            const data = ProjectManager.exportProjects()
            const blob = new Blob([data], { type: 'application/json' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `cad_projects_${new Date().toISOString().split('T')[0]}.json`
            a.click()
            URL.revokeObjectURL(url)
        } catch (error) {
            console.error('Error exporting projects:', error)
            alert('Erreur lors de l\'export')
        }
    }, [])

    const handleImportProjects = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (!file) return

        const reader = new FileReader()
        reader.onload = (e) => {
            try {
                const jsonData = e.target?.result as string
                const result = ProjectManager.importProjects(jsonData)

                if (result.success) {
                    loadProjects()
                    alert(`${result.imported} projets importés avec succès!`)
                    if (result.errors.length > 0) {
                        console.warn('Import warnings:', result.errors)
                    }
                } else {
                    alert(`Erreur lors de l'import:\n${result.errors.join('\n')}`)
                }
            } catch (error) {
                alert('Erreur lors de la lecture du fichier')
            }
        }
        reader.readAsText(file)

        // Reset l'input
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }, [loadProjects])

    const handleClearAll = useCallback(() => {
        if (confirm('Supprimer TOUS les projets ? Cette action est irréversible.')) {
            if (ProjectManager.clearAllProjects()) {
                loadProjects()
            }
        }
    }, [loadProjects])

    // Filtrage des projets
    const filteredProjects = projects.filter(project => {
        const matchesSearch = project.name.toLowerCase().includes(filter.searchTerm.toLowerCase()) ||
            project.prompt.toLowerCase().includes(filter.searchTerm.toLowerCase())
        const matchesTag = !filter.selectedTag || project.tags.includes(filter.selectedTag)
        return matchesSearch && matchesTag
    })

    const allTags = ProjectManager.getAllTags()
    const stats = ProjectManager.getProjectStats()

    return (
        <div className="panel project-history">
            <ProjectHeader
                onSave={() => setShowSaveDialog(true)}
                onExport={handleExportProjects}
                onImport={() => fileInputRef.current?.click()}
                onClear={handleClearAll}
                stats={stats}
                canSave={!!currentProject}
            />

            <ProjectFilterView
                filter={filter}
                onFilterChange={setFilter}
                allTags={allTags}
            />

            <div className="project-list">
                {isLoading ? (
                    <div className="loading-indicator">Chargement...</div>
                ) : filteredProjects.length === 0 ? (
                    <EmptyState hasFilter={!!(filter.searchTerm || filter.selectedTag)} />
                ) : (
                    <ProjectList
                        projects={filteredProjects}
                        onLoad={onLoadProject}
                        onDelete={handleDeleteProject}
                        onDuplicate={handleDuplicateProject}
                    />
                )}
            </div>

            {showSaveDialog && (
                <SaveProjectDialog
                    currentProject={currentProject}
                    onSave={handleSaveProject}
                    onCancel={() => setShowSaveDialog(false)}
                />
            )}

            <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                style={{ display: 'none' }}
                onChange={handleImportProjects}
            />
        </div>
    )
}

// Composant en-tête
function ProjectHeader({
    onSave,
    onExport,
    onImport,
    onClear,
    stats,
    canSave
}: {
    onSave: () => void
    onExport: () => void
    onImport: () => void
    onClear: () => void
    stats: any
    canSave: boolean
}) {
    return (
        <div className="project-header">
            <div className="header-title">
                <h3>Projets ({stats.totalProjects})</h3>
                <small>Complexité moy.: {stats.averageComplexity}</small>
            </div>

            <div className="header-actions">
                <button
                    className="button small primary"
                    onClick={onSave}
                    disabled={!canSave}
                    title={canSave ? "Sauvegarder le projet actuel" : "Aucun projet à sauvegarder"}
                >
                    💾 Sauver
                </button>

                <button className="button small" onClick={onExport}>
                    📤 Export
                </button>

                <button className="button small" onClick={onImport}>
                    📥 Import
                </button>

                <button
                    className="button small secondary"
                    onClick={onClear}
                    title="Supprimer tous les projets"
                >
                    🗑️
                </button>
            </div>
        </div>
    )
}

// Composant filtre (RENOMMÉ)
function ProjectFilterView({
    filter,
    onFilterChange,
    allTags
}: {
    filter: ProjectFilter
    onFilterChange: (filter: ProjectFilter) => void
    allTags: string[]
}) {
    return (
        <div className="project-filter">
            <input
                type="text"
                className="input"
                placeholder="🔍 Rechercher un projet..."
                value={filter.searchTerm}
                onChange={(e) => onFilterChange({ ...filter, searchTerm: e.target.value })}
            />

            {allTags.length > 0 && (
                <select
                    className="input"
                    value={filter.selectedTag}
                    onChange={(e) => onFilterChange({ ...filter, selectedTag: e.target.value })}
                >
                    <option value="">🏷️ Tous les tags</option>
                    {allTags.map(tag => (
                        <option key={tag} value={tag}>{tag}</option>
                    ))}
                </select>
            )}
        </div>
    )
}

// Composant liste des projets
function ProjectList({
    projects,
    onLoad,
    onDelete,
    onDuplicate
}: {
    projects: CADProject[]
    onLoad: (project: CADProject) => void
    onDelete: (id: string, name: string) => void
    onDuplicate: (id: string) => void
}) {
    return (
        <div className="projects-container">
            {projects.map((project) => (
                <ProjectItem
                    key={project.id}
                    project={project}
                    onLoad={() => onLoad(project)}
                    onDelete={() => onDelete(project.id, project.name)}
                    onDuplicate={() => onDuplicate(project.id)}
                />
            ))}
        </div>
    )
}

// Composant élément de projet
function ProjectItem({
    project,
    onLoad,
    onDelete,
    onDuplicate
}: {
    project: CADProject
    onLoad: () => void
    onDelete: () => void
    onDuplicate: () => void
}) {
    const formatDate = (timestamp: number) => {
        return new Date(timestamp).toLocaleDateString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            year: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const truncateText = (text: string, maxLength: number) => {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
    }

    return (
        <div className="project-item">
            <div className="project-content">
                <div className="project-main">
                    <h4 className="project-name">{project.name}</h4>
                    <p className="project-prompt">
                        {truncateText(project.prompt, 80)}
                    </p>
                    <div className="project-meta">
                        <span className="project-date">{formatDate(project.timestamp)}</span>
                        {project.analytics && (
                            <span className="project-complexity">
                                {project.analytics.complexity}
                            </span>
                        )}
                    </div>
                </div>

                <div className="project-tags">
                    {project.tags.slice(0, 3).map(tag => (
                        <span key={tag} className="project-tag">{tag}</span>
                    ))}
                    {project.tags.length > 3 && (
                        <span className="project-tag-more">+{project.tags.length - 3}</span>
                    )}
                </div>
            </div>

            <div className="project-actions">
                <button
                    className="button small primary"
                    onClick={onLoad}
                    title="Charger ce projet"
                >
                    📂
                </button>
                <button
                    className="button small"
                    onClick={onDuplicate}
                    title="Dupliquer ce projet"
                >
                    📋
                </button>
                <button
                    className="button small secondary"
                    onClick={onDelete}
                    title="Supprimer ce projet"
                >
                    🗑️
                </button>
            </div>
        </div>
    )
}

// État vide
function EmptyState({ hasFilter }: { hasFilter: boolean }) {
    if (hasFilter) {
        return (
            <div className="empty-state">
                <p>🔍 Aucun projet trouvé</p>
                <small>Essayez avec d'autres mots-clés</small>
            </div>
        )
    }

    return (
        <div className="empty-state">
            <p>📁 Aucun projet sauvegardé</p>
            <small>Générez et sauvegardez votre premier modèle !</small>
        </div>
    )
}

// Dialog de sauvegarde
function SaveProjectDialog({
    currentProject,
    onSave,
    onCancel
}: {
    currentProject?: any
    onSave: (name?: string) => boolean
    onCancel: () => void
}) {
    const [projectName, setProjectName] = useState('')
    const [isSaving, setIsSaving] = useState(false)

    useEffect(() => {
        if (currentProject) {
            // Générer un nom automatique basé sur le prompt
            const autoName = generateProjectName(currentProject.prompt)
            setProjectName(autoName)
        }
    }, [currentProject])

    const handleSave = async () => {
        setIsSaving(true)
        try {
            const success = onSave(projectName.trim() || undefined)
            if (success) {
                onCancel()
            }
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h3>Sauvegarder le projet</h3>
                    <button className="modal-close" onClick={onCancel}>×</button>
                </div>

                <div className="modal-content">
                    <div className="form-group">
                        <label>Nom du projet:</label>
                        <input
                            type="text"
                            className="input"
                            value={projectName}
                            onChange={(e) => setProjectName(e.target.value)}
                            placeholder="Mon super projet CAD"
                            autoFocus
                            maxLength={100}
                        />
                    </div>

                    {currentProject && (
                        <div className="project-preview">
                            <small>Prompt: {currentProject.prompt.substring(0, 100)}...</small>
                        </div>
                    )}
                </div>

                <div className="modal-actions">
                    <button
                        className="button"
                        onClick={onCancel}
                        disabled={isSaving}
                    >
                        Annuler
                    </button>
                    <button
                        className="button primary"
                        onClick={handleSave}
                        disabled={isSaving || !projectName.trim()}
                    >
                        {isSaving ? 'Sauvegarde...' : 'Sauvegarder'}
                    </button>
                </div>
            </div>
        </div>
    )
}

function generateProjectName(prompt: string): string {
    const words = prompt.toLowerCase().split(' ')
    const importantWords = words.filter(word =>
        word.length > 3 &&
        !['create', 'make', 'build', 'with', 'that', 'this', 'and', 'for'].includes(word)
    )

    const name = importantWords.slice(0, 3).join(' ')
    return name.charAt(0).toUpperCase() + name.slice(1)
}