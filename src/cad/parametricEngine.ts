// src/cad/parametricEngine.ts
import * as THREE from 'three'
import { Parameter, ParametricModel } from '../types/parameters'

export class ParametricEngine {

    // Extrait les paramètres du code généré
    extractParameters(code: string): Parameter[] {
        const parameters: Parameter[] = []

        // Regex pour détecter les constantes avec commentaires
        const constRegex = /const\s+(\w+)\s*=\s*([0-9.]+)(?:\s*\/\/\s*(.+?)(?:\s+en\s+(\w+))?)?/g

        let match
        while ((match = constRegex.exec(code)) !== null) {
            const [, name, value, description, unit] = match

            // Skip variables qui ne sont pas des paramètres géométriques
            if (this.isGeometricParameter(name)) {
                const numValue = parseFloat(value)

                parameters.push({
                    name,
                    value: numValue,
                    min: this.getMinValue(name, numValue),
                    max: this.getMaxValue(name, numValue),
                    step: this.getStep(name, numValue),
                    unit: unit || this.guessUnit(name),
                    description: description || this.generateDescription(name),
                    category: this.getCategory(name)
                })
            }
        }

        // Si pas assez de paramètres détectés, essayer une méthode alternative
        if (parameters.length === 0) {
            return this.extractParametersAlternative(code)
        }

        return this.deduplicateParameters(parameters)
    }

    private isGeometricParameter(name: string): boolean {
        const geometricTerms = [
            'width', 'height', 'depth', 'length', 'radius', 'diameter',
            'thickness', 'size', 'spacing', 'count', 'angle', 'distance',
            'outerRadius', 'innerRadius', 'holeRadius', 'flangeRadius',
            'tubeLength', 'pillarHeight', 'baseWidth', 'baseLength'
        ]

        return geometricTerms.some(term =>
            name.toLowerCase().includes(term.toLowerCase())
        )
    }

    private extractParametersAlternative(code: string): Parameter[] {
        const parameters: Parameter[] = []

        // Chercher les valeurs numériques dans les géométries
        const geometryRegex = /new THREE\.(\w+Geometry)\(([^)]+)\)/g
        const paramMap = new Map<number, string>()

        let match
        while ((match = geometryRegex.exec(code)) !== null) {
            const [, geometryType, params] = match
            const paramValues = params.split(',').map(p => p.trim())

            paramValues.forEach((param, index) => {
                const numMatch = param.match(/^([0-9.]+)$/)
                if (numMatch) {
                    const value = parseFloat(numMatch[1])
                    const paramName = this.getParameterNameFromGeometry(geometryType, index)

                    if (!paramMap.has(value)) {
                        paramMap.set(value, paramName)

                        parameters.push({
                            name: paramName,
                            value,
                            min: Math.max(0.1, value * 0.1),
                            max: value * 5,
                            step: value > 10 ? 1 : 0.1,
                            unit: this.guessUnit(paramName),
                            description: `${geometryType} - ${paramName}`,
                            category: 'geometry'
                        })
                    }
                }
            })
        }

        return parameters
    }

    private getParameterNameFromGeometry(geometryType: string, index: number): string {
        const paramNames: Record<string, string[]> = {
            'BoxGeometry': ['width', 'height', 'depth'],
            'SphereGeometry': ['radius', 'widthSegments', 'heightSegments'],
            'CylinderGeometry': ['radiusTop', 'radiusBottom', 'height', 'radialSegments'],
            'ConeGeometry': ['radius', 'height', 'radialSegments'],
            'TorusGeometry': ['radius', 'tube', 'radialSegments', 'tubularSegments']
        }

        const names = paramNames[geometryType] || []
        return names[index] || `param${index}`
    }

    private getMinValue(name: string, currentValue: number): number {
        if (name.toLowerCase().includes('count') || name.toLowerCase().includes('segments')) {
            return Math.max(3, Math.floor(currentValue * 0.5))
        }
        if (name.toLowerCase().includes('angle')) {
            return 0
        }
        return Math.max(0.1, currentValue * 0.1)
    }

    private getMaxValue(name: string, currentValue: number): number {
        if (name.toLowerCase().includes('count') || name.toLowerCase().includes('segments')) {
            return currentValue * 3
        }
        if (name.toLowerCase().includes('angle')) {
            return 360
        }
        return currentValue * 10
    }

    private getStep(name: string, currentValue: number): number {
        if (name.toLowerCase().includes('count') || name.toLowerCase().includes('segments')) {
            return 1
        }
        if (name.toLowerCase().includes('angle')) {
            return 1
        }
        return currentValue > 10 ? 0.5 : 0.1
    }

    private guessUnit(name: string): string {
        if (name.toLowerCase().includes('angle')) return '°'
        if (name.toLowerCase().includes('count') ||
            name.toLowerCase().includes('segments')) return ''
        return 'mm'
    }

    private generateDescription(name: string): string {
        const descriptions: Record<string, string> = {
            'width': 'Largeur',
            'height': 'Hauteur',
            'depth': 'Profondeur',
            'length': 'Longueur',
            'radius': 'Rayon',
            'thickness': 'Épaisseur',
            'diameter': 'Diamètre',
            'spacing': 'Espacement',
            'count': 'Nombre',
            'angle': 'Angle'
        }

        for (const [key, desc] of Object.entries(descriptions)) {
            if (name.toLowerCase().includes(key)) {
                return desc
            }
        }

        return `Paramètre ${name}`
    }

    private getCategory(name: string): string {
        if (name.toLowerCase().includes('count') || name.toLowerCase().includes('segments')) {
            return 'Qualité'
        }
        if (name.toLowerCase().includes('angle')) {
            return 'Rotation'
        }
        if (name.toLowerCase().includes('hole') || name.toLowerCase().includes('inner')) {
            return 'Trous/Cavités'
        }
        return 'Dimensions'
    }

    private deduplicateParameters(params: Parameter[]): Parameter[] {
        const seen = new Set<string>()
        return params.filter(param => {
            if (seen.has(param.name)) return false
            seen.add(param.name)
            return true
        })
    }

    // Génère du code paramétrique réutilisable
    generateParametricCode(originalCode: string, parameters: Parameter[]): ParametricModel {
        const paramDefaults = parameters.map(p =>
            `    ${p.name}: ${p.value}`
        ).join(',\n')

        const modifiedCode = this.replaceHardcodedValues(originalCode, parameters)

        const parametricCode = `// Code paramétrique généré automatiquement
function generateModel(customParams = {}) {
  // Paramètres par défaut
  const defaultParams = {
${paramDefaults}
  }
  
  // Fusion avec les paramètres personnalisés
  const params = { ...defaultParams, ...customParams }
  
  // Extraction des paramètres pour utilisation
${parameters.map(p => `  const ${p.name} = params.${p.name}`).join('\n')}
  
  // Génération du modèle
  const meshes = []
  
${this.extractModelLogic(modifiedCode)}
  
  return meshes
}

// Fonction de compatibilité
function generateModelWithDefaults() {
  return generateModel()
}`

        return {
            originalCode,
            parametricCode,
            parameters,
            generateFunction: 'generateModel'
        }
    }

    private replaceHardcodedValues(code: string, parameters: Parameter[]): string {
        let modifiedCode = code

        parameters.forEach(param => {
            // Remplace les valeurs numériques exactes par les paramètres
            const regex = new RegExp(`\\b${param.value}\\b`, 'g')
            modifiedCode = modifiedCode.replace(regex, `${param.name}`)
        })

        return modifiedCode
    }

    private extractModelLogic(code: string): string {
        // Extrait la logique principale du modèle (sans la déclaration de fonction)
        const lines = code.split('\n')
        const modelLines: string[] = []
        let inFunction = false
        let braceCount = 0

        for (const line of lines) {
            if (line.includes('function generateModel') || inFunction) {
                if (line.includes('{')) braceCount++
                if (line.includes('}')) braceCount--

                if (inFunction && braceCount > 0) {
                    // Skip function declaration line and final return
                    if (!line.includes('function generateModel') &&
                        !line.trim().startsWith('return meshes')) {
                        modelLines.push(line)
                    }
                }

                if (line.includes('function generateModel')) {
                    inFunction = true
                }

                if (inFunction && braceCount === 0 && line.includes('}')) {
                    break
                }
            }
        }

        return modelLines.join('\n')
    }

    // Régénère le modèle avec de nouveaux paramètres
    executeParametricModel(
        parametricModel: ParametricModel,
        customParameters: Record<string, number>
    ): THREE.Mesh[] {
        try {
            // Créer une fonction exécutable
            const executeFunction = new Function('THREE', 'customParams', `
        ${parametricModel.parametricCode}
        return generateModel(customParams);
      `)

            const result = executeFunction(THREE, customParameters)

            if (!Array.isArray(result)) {
                console.warn('Parametric model did not return array')
                return []
            }

            return result.filter(item => item && (item.isMesh || item.isGroup))

        } catch (error) {
            console.error('Error executing parametric model:', error)
            return []
        }
    }

    // Génère une prévisualisation rapide avec paramètres réduits
    generatePreview(
        parametricModel: ParametricModel,
        customParameters: Record<string, number>
    ): THREE.Mesh[] {
        // Créer des paramètres optimisés pour la prévisualisation
        const previewParams = { ...customParameters }

        // Réduire la qualité pour performance
        Object.keys(previewParams).forEach(key => {
            if (key.toLowerCase().includes('segments')) {
                previewParams[key] = Math.min(previewParams[key], 16)
            }
        })

        return this.executeParametricModel(parametricModel, previewParams)
    }

    // Valide les paramètres avant exécution
    validateParameters(parameters: Parameter[], values: Record<string, number>): {
        isValid: boolean
        errors: string[]
    } {
        const errors: string[] = []

        parameters.forEach(param => {
            const value = values[param.name]

            if (value === undefined || value === null) {
                errors.push(`Paramètre manquant: ${param.name}`)
                return
            }

            if (typeof value !== 'number' || !isFinite(value)) {
                errors.push(`Valeur invalide pour ${param.name}: ${value}`)
                return
            }

            if (value < param.min) {
                errors.push(`${param.name} trop petit (min: ${param.min})`)
            }

            if (value > param.max) {
                errors.push(`${param.name} trop grand (max: ${param.max})`)
            }
        })

        return {
            isValid: errors.length === 0,
            errors
        }
    }
}