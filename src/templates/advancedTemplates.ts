// src/templates/advancedTemplates.ts

export interface TemplateCategory {
    name: string
    icon: string
    description: string
    templates: Template[]
}

export interface Template {
    id: string
    name: string
    description: string
    prompt: string
    tags: string[]
    difficulty: 'Débutant' | 'Intermédiaire' | 'Avancé'
    estimatedTime: string
    parameters?: TemplateParameter[]
}

export interface TemplateParameter {
    name: string
    description: string
    defaultValue: number | string
    type: 'number' | 'string' | 'boolean'
    min?: number
    max?: number
    unit?: string
}

export const ADVANCED_TEMPLATES: TemplateCategory[] = [
    {
        name: 'Mécanique',
        icon: '⚙️',
        description: 'Pièces mécaniques et engrenages',
        templates: [
            {
                id: 'gear-basic',
                name: 'Engrenage Simple',
                description: 'Engrenage droit avec paramètres ajustables',
                prompt: 'Create a gear with {teeth} teeth, outer radius {outerRadius}mm, inner radius {innerRadius}mm, thickness {thickness}mm, and center hole radius {holeRadius}mm',
                tags: ['engrenage', 'mécanique', 'rotation'],
                difficulty: 'Débutant',
                estimatedTime: '2 min',
                parameters: [
                    { name: 'teeth', description: 'Nombre de dents', defaultValue: 12, type: 'number', min: 6, max: 60 },
                    { name: 'outerRadius', description: 'Rayon extérieur', defaultValue: 15, type: 'number', min: 5, max: 50, unit: 'mm' },
                    { name: 'innerRadius', description: 'Rayon intérieur', defaultValue: 8, type: 'number', min: 3, max: 30, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 4, type: 'number', min: 1, max: 20, unit: 'mm' },
                    { name: 'holeRadius', description: 'Rayon du trou central', defaultValue: 3, type: 'number', min: 0.5, max: 15, unit: 'mm' }
                ]
            },
            {
                id: 'gear-planetary',
                name: 'Système Planétaire',
                description: 'Engrenage planétaire complet avec solaire et couronne',
                prompt: 'Create a planetary gear system with sun gear {sunTeeth} teeth radius {sunRadius}mm, {planetCount} planet gears with {planetTeeth} teeth radius {planetRadius}mm, and ring gear {ringTeeth} teeth inner radius {ringRadius}mm, thickness {thickness}mm',
                tags: ['engrenage', 'planétaire', 'complexe'],
                difficulty: 'Avancé',
                estimatedTime: '5 min',
                parameters: [
                    { name: 'sunTeeth', description: 'Dents engrenage solaire', defaultValue: 8, type: 'number', min: 6, max: 20 },
                    { name: 'sunRadius', description: 'Rayon solaire', defaultValue: 8, type: 'number', min: 4, max: 15, unit: 'mm' },
                    { name: 'planetCount', description: 'Nombre de planètes', defaultValue: 3, type: 'number', min: 2, max: 6 },
                    { name: 'planetTeeth', description: 'Dents par planète', defaultValue: 12, type: 'number', min: 8, max: 25 },
                    { name: 'planetRadius', description: 'Rayon des planètes', defaultValue: 12, type: 'number', min: 6, max: 20, unit: 'mm' },
                    { name: 'ringTeeth', description: 'Dents couronne', defaultValue: 32, type: 'number', min: 20, max: 60 },
                    { name: 'ringRadius', description: 'Rayon couronne', defaultValue: 32, type: 'number', min: 20, max: 60, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 6, type: 'number', min: 2, max: 15, unit: 'mm' }
                ]
            },
            {
                id: 'bearing-housing',
                name: 'Logement de Roulement',
                description: 'Boîtier pour roulement à billes avec trous de montage',
                prompt: 'Create a bearing housing for {bearingDiameter}mm bearing, outer diameter {outerDiameter}mm, height {height}mm, wall thickness {wallThickness}mm, with {boltHoles} mounting holes of {boltDiameter}mm diameter on {boltCircleDiameter}mm bolt circle',
                tags: ['roulement', 'logement', 'montage'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'pulley-timing',
                name: 'Poulie de Distribution',
                description: 'Poulie crantée pour courroie de distribution',
                prompt: 'Create a timing pulley with {teeth} teeth, {pitch}mm pitch, outer diameter {outerDiameter}mm, inner diameter {innerDiameter}mm, width {width}mm, and hub diameter {hubDiameter}mm with keyway',
                tags: ['poulie', 'courroie', 'transmission'],
                difficulty: 'Avancé',
                estimatedTime: '4 min'
            }
        ]
    },
    {
        name: 'Supports & Fixations',
        icon: '🔧',
        description: 'Équerres, supports et pièces de fixation',
        templates: [
            {
                id: 'l-bracket-basic',
                name: 'Équerre Simple',
                description: 'Équerre en L avec trous de montage',
                prompt: 'Create an L-bracket {width}mm x {height}mm, thickness {thickness}mm, with {holeCount} mounting holes of {holeDiameter}mm diameter, spaced {holeSpacing}mm apart',
                tags: ['équerre', 'support', 'montage'],
                difficulty: 'Débutant',
                estimatedTime: '2 min',
                parameters: [
                    { name: 'width', description: 'Largeur', defaultValue: 50, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'height', description: 'Hauteur', defaultValue: 40, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'thickness', description: 'Épaisseur', defaultValue: 4, type: 'number', min: 2, max: 10, unit: 'mm' },
                    { name: 'holeCount', description: 'Nombre de trous', defaultValue: 4, type: 'number', min: 2, max: 12 },
                    { name: 'holeDiameter', description: 'Diamètre des trous', defaultValue: 4, type: 'number', min: 2, max: 12, unit: 'mm' },
                    { name: 'holeSpacing', description: 'Espacement des trous', defaultValue: 15, type: 'number', min: 8, max: 50, unit: 'mm' }
                ]
            },
            {
                id: 'corner-bracket',
                name: 'Équerre d\'Angle',
                description: 'Équerre pour assemblage à 90° avec nervures',
                prompt: 'Create a corner bracket for {angle}° joint, {size}mm sides, thickness {thickness}mm, with {ribCount} reinforcement ribs and {holeCount} mounting holes',
                tags: ['angle', 'assemblage', 'nervures'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'universal-mount',
                name: 'Support Universel',
                description: 'Support réglable multi-positions',
                prompt: 'Create a universal mounting bracket with base {baseLength}mm x {baseWidth}mm, adjustable arm length {armLength}mm, {adjustmentSlots} adjustment slots, and universal joint',
                tags: ['réglable', 'universel', 'articulé'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            }
        ]
    },
    {
        name: 'Boîtiers & Enclosures',
        icon: '📦',
        description: 'Boîtiers électroniques et enclosures',
        templates: [
            {
                id: 'electronics-box',
                name: 'Boîtier Électronique',
                description: 'Boîtier avec couvercle et ventilation',
                prompt: 'Create an electronics enclosure {width}mm x {height}mm x {depth}mm, wall thickness {wallThickness}mm, lid height {lidHeight}mm, with ventilation holes and {standoffCount} PCB standoffs',
                tags: ['électronique', 'boîtier', 'ventilation'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min',
                parameters: [
                    { name: 'width', description: 'Largeur', defaultValue: 80, type: 'number', min: 40, max: 200, unit: 'mm' },
                    { name: 'height', description: 'Hauteur', defaultValue: 50, type: 'number', min: 20, max: 100, unit: 'mm' },
                    { name: 'depth', description: 'Profondeur', defaultValue: 60, type: 'number', min: 30, max: 150, unit: 'mm' },
                    { name: 'wallThickness', description: 'Épaisseur parois', defaultValue: 2.5, type: 'number', min: 1.5, max: 5, unit: 'mm' },
                    { name: 'lidHeight', description: 'Hauteur couvercle', defaultValue: 8, type: 'number', min: 5, max: 20, unit: 'mm' },
                    { name: 'standoffCount', description: 'Nombre de supports PCB', defaultValue: 4, type: 'number', min: 2, max: 8 }
                ]
            },
            {
                id: 'din-rail-case',
                name: 'Boîtier Rail DIN',
                description: 'Enclosure pour montage sur rail DIN',
                prompt: 'Create a DIN rail enclosure, {modules} modules wide, height {height}mm, depth {depth}mm, with DIN rail clips, terminal openings and cable entries',
                tags: ['DIN', 'rail', 'industriel'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            },
            {
                id: 'weatherproof-box',
                name: 'Boîtier Étanche',
                description: 'Enclosure résistant aux intempéries avec joint',
                prompt: 'Create a weatherproof enclosure {width}mm x {height}mm x {depth}mm, IP65 rating, with gasket groove, cable glands for {cableCount} cables, and locking mechanism',
                tags: ['étanche', 'extérieur', 'IP65'],
                difficulty: 'Avancé',
                estimatedTime: '7 min'
            }
        ]
    },
    {
        name: 'Connecteurs & Raccords',
        icon: '🔌',
        description: 'Connecteurs, raccords et pièces de jonction',
        templates: [
            {
                id: 'pipe-connector',
                name: 'Raccord de Tuyau',
                description: 'Connecteur pour tuyaux avec filetage',
                prompt: 'Create a pipe connector for {pipeDiameter}mm pipes, total length {totalLength}mm, with {threadPitch}mm thread pitch, flange diameter {flangeDiameter}mm, and {sealGrooves} seal grooves',
                tags: ['tuyau', 'raccord', 'étanchéité'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'quick-connect',
                name: 'Raccord Rapide',
                description: 'Connecteur rapide push-to-connect',
                prompt: 'Create a quick-connect fitting for {tubeDiameter}mm tube, body diameter {bodyDiameter}mm, release collar diameter {collarDiameter}mm, with internal gripping ring and O-ring seals',
                tags: ['rapide', 'pneumatique', 'étanchéité'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'cable-gland',
                name: 'Presse-étoupe',
                description: 'Presse-étoupe pour passage de câbles',
                prompt: 'Create a cable gland M{threadSize} thread, for cable diameter {cableDiameterMin}mm to {cableDiameterMax}mm, with compression nut, sealing ring and strain relief',
                tags: ['câble', 'étanchéité', 'métrique'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            }
        ]
    },
    {
        name: 'Outillage',
        icon: '🔨',
        description: 'Outils et accessoires d\'atelier',
        templates: [
            {
                id: 'custom-wrench',
                name: 'Clé Sur Mesure',
                description: 'Clé plate ou à fourche personnalisée',
                prompt: 'Create a custom wrench for {nutSize}mm nut, handle length {handleLength}mm, thickness {thickness}mm, with ergonomic grip and hanging hole',
                tags: ['clé', 'outil', 'personnalisé'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min'
            },
            {
                id: 'drill-jig',
                name: 'Guide de Perçage',
                description: 'Gabarit pour perçage précis',
                prompt: 'Create a drilling jig for {holeSpacing}mm spacing, {holeCount} holes of {holeDiameter}mm diameter, base {baseLength}mm x {baseWidth}mm, with alignment features',
                tags: ['perçage', 'gabarit', 'précision'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'go-no-go-gauge',
                name: 'Calibre Passe/Ne-passe-pas',
                description: 'Calibre de contrôle dimensionnel',
                prompt: 'Create a go/no-go gauge for {dimension}mm ± {tolerance}mm, length {length}mm, with clear marking and handling area',
                tags: ['calibre', 'contrôle', 'qualité'],
                difficulty: 'Avancé',
                estimatedTime: '3 min'
            }
        ]
    },
    {
        name: 'Artistique & Déco',
        icon: '🎨',
        description: 'Objets décoratifs et artistiques',
        templates: [
            {
                id: 'parametric-vase',
                name: 'Vase Paramétrique',
                description: 'Vase avec forme paramétrable',
                prompt: 'Create a parametric vase {height}mm tall, base diameter {baseDiameter}mm, top diameter {topDiameter}mm, with {twistAngle}° twist, {wallThickness}mm wall thickness and decorative pattern',
                tags: ['vase', 'décoratif', 'paramétrique'],
                difficulty: 'Intermédiaire',
                estimatedTime: '3 min',
                parameters: [
                    { name: 'height', description: 'Hauteur', defaultValue: 150, type: 'number', min: 50, max: 300, unit: 'mm' },
                    { name: 'baseDiameter', description: 'Diamètre base', defaultValue: 60, type: 'number', min: 30, max: 150, unit: 'mm' },
                    { name: 'topDiameter', description: 'Diamètre sommet', defaultValue: 80, type: 'number', min: 20, max: 200, unit: 'mm' },
                    { name: 'twistAngle', description: 'Angle de torsion', defaultValue: 45, type: 'number', min: 0, max: 180, unit: '°' },
                    { name: 'wallThickness', description: 'Épaisseur paroi', defaultValue: 2, type: 'number', min: 1, max: 5, unit: 'mm' }
                ]
            },
            {
                id: 'geometric-sculpture',
                name: 'Sculpture Géométrique',
                description: 'Sculpture abstraite basée sur des formes géométriques',
                prompt: 'Create an abstract geometric sculpture with {elementCount} elements, overall size {size}mm, based on {geometryType} geometry with {complexityLevel} complexity level',
                tags: ['sculpture', 'abstrait', 'géométrie'],
                difficulty: 'Avancé',
                estimatedTime: '5 min'
            },
            {
                id: 'voronoi-lamp',
                name: 'Abat-jour Voronoi',
                description: 'Abat-jour avec motif voronoi',
                prompt: 'Create a lamp shade {diameter}mm diameter, {height}mm height, with Voronoi pattern, {cellCount} cells, wall thickness {wallThickness}mm, and mounting ring',
                tags: ['luminaire', 'voronoi', 'motif'],
                difficulty: 'Avancé',
                estimatedTime: '6 min'
            }
        ]
    },
    {
        name: 'Automobile',
        icon: '🚗',
        description: 'Pièces et accessoires automobiles',
        templates: [
            {
                id: 'phone-car-mount',
                name: 'Support Téléphone Auto',
                description: 'Support de téléphone pour tableau de bord',
                prompt: 'Create a car phone mount for dashboard, adjustable angle {minAngle}° to {maxAngle}°, phone width {minPhoneWidth}mm to {maxPhoneWidth}mm, with suction cup base and cable routing',
                tags: ['téléphone', 'voiture', 'support'],
                difficulty: 'Intermédiaire',
                estimatedTime: '4 min'
            },
            {
                id: 'cup-holder-adapter',
                name: 'Adaptateur Porte-gobelet',
                description: 'Adaptateur pour porte-gobelet de taille différente',
                prompt: 'Create a cup holder adapter from {originalDiameter}mm to {targetDiameter}mm, height {height}mm, with flexible fit and non-slip bottom',
                tags: ['porte-gobelet', 'adaptateur', 'ergonomie'],
                difficulty: 'Débutant',
                estimatedTime: '2 min'
            }
        ]
    }
]

export class TemplateManager {
    static getAllTemplates(): Template[] {
        return ADVANCED_TEMPLATES.flatMap(category => category.templates)
    }

    static getTemplatesByCategory(categoryName: string): Template[] {
        const category = ADVANCED_TEMPLATES.find(cat => cat.name === categoryName)
        return category ? category.templates : []
    }

    static getTemplateById(id: string): Template | null {
        return this.getAllTemplates().find(template => template.id === id) || null
    }

    static getTemplatesByDifficulty(difficulty: 'Débutant' | 'Intermédiaire' | 'Avancé'): Template[] {
        return this.getAllTemplates().filter(template => template.difficulty === difficulty)
    }

    static searchTemplates(query: string): Template[] {
        const lowerQuery = query.toLowerCase()
        return this.getAllTemplates().filter(template =>
            template.name.toLowerCase().includes(lowerQuery) ||
            template.description.toLowerCase().includes(lowerQuery) ||
            template.tags.some(tag => tag.toLowerCase().includes(lowerQuery))
        )
    }

    static getRandomTemplate(): Template {
        const allTemplates = this.getAllTemplates()
        return allTemplates[Math.floor(Math.random() * allTemplates.length)]
    }

    static interpolateTemplate(template: Template, parameters: Record<string, any>): string {
        let interpolated = template.prompt

        // Remplacer les paramètres {param} par leurs valeurs
        Object.entries(parameters).forEach(([key, value]) => {
            const regex = new RegExp(`\\{${key}\\}`, 'g')
            interpolated = interpolated.replace(regex, value.toString())
        })

        return interpolated
    }

    static validateParameters(template: Template, parameters: Record<string, any>): {
        isValid: boolean
        errors: string[]
    } {
        const errors: string[] = []

        if (!template.parameters) {
            return { isValid: true, errors: [] }
        }

        template.parameters.forEach(param => {
            const value = parameters[param.name]

            if (value === undefined || value === null) {
                errors.push(`Paramètre manquant: ${param.name}`)
                return
            }

            if (param.type === 'number') {
                const numValue = Number(value)
                if (isNaN(numValue)) {
                    errors.push(`${param.name}: doit être un nombre`)
                    return
                }

                if (param.min !== undefined && numValue < param.min) {
                    errors.push(`${param.name}: minimum ${param.min}`)
                }

                if (param.max !== undefined && numValue > param.max) {
                    errors.push(`${param.name}: maximum ${param.max}`)
                }
            }
        })

        return {
            isValid: errors.length === 0,
            errors
        }
    }
}