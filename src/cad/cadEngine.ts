// src/cad/cadEngine.ts - Version Améliorée
import * as THREE from 'three'
import { CSG } from 'three-csg-ts'
import { ParametricEngine } from './parametricEngine'
import { ModelValidator } from '../utils/modelValidator'
import { extendCADEngineWithAdvancedShapes } from './advancedShapes'

export interface CADEngineOptions {
    enableCSG?: boolean
    enableAdvancedShapes?: boolean
    enableParametricExtraction?: boolean
    maxComplexity?: number
    autoOptimize?: boolean
}

export class CADEngine {
    private initialized = false
    private parametricEngine: ParametricEngine
    private options: CADEngineOptions
    private executionHistory: Array<{
        code: string
        timestamp: number
        success: boolean
        meshCount: number
    }> = []

    constructor(options: CADEngineOptions = {}) {
        this.options = {
            enableCSG: true,
            enableAdvancedShapes: true,
            enableParametricExtraction: true,
            maxComplexity: 100000, // Max triangles
            autoOptimize: true,
            ...options
        }

        this.parametricEngine = new ParametricEngine()

        // Étendre avec les formes avancées si activé
        if (this.options.enableAdvancedShapes) {
            extendCADEngineWithAdvancedShapes(this)
        }
    }

    async initialize(): Promise<void> {
        if (this.initialized) return

        console.log('[CAD Engine] Initialisation...')
        console.log('[CAD Engine] Options:', this.options)

        this.initialized = true
        console.log('[CAD Engine] Initialisé avec succès')
    }

    async executeCADCode(code: string): Promise<THREE.Mesh[]> {
        if (!this.initialized) {
            await this.initialize()
        }

        console.log('[CAD Engine] Exécution du code CAD')
        const startTime = Date.now()

        try {
            // Nettoyage et validation préalable du code
            const cleanedCode = this.sanitizeCode(code)
            console.log('[CAD Engine] Code nettoyé')

            // Détection des patterns dangereux
            if (this.hasDangerousPatterns(cleanedCode)) {
                console.warn('[CAD Engine] Code potentiellement dangereux détecté')
                return [this.createFallbackShape('sphere')]
            }

            // Création du contexte d'exécution sécurisé
            const executionContext = this.createExecutionContext()

            // Wrapping du code si nécessaire
            const wrappedCode = this.wrapCode(cleanedCode)

            // Exécution avec timeout
            const result = await this.executeWithTimeout(wrappedCode, executionContext, 10000)

            // Validation et traitement du résultat
            if (!Array.isArray(result)) {
                console.warn('[CAD Engine] Le code n\'a pas retourné un tableau')
                return [this.createFallbackShape()]
            }

            // Filtrage et validation des meshes
            let validMeshes = this.filterValidMeshes(result)

            if (validMeshes.length === 0) {
                console.warn('[CAD Engine] Aucun mesh valide généré')
                return [this.createFallbackShape()]
            }

            // Application des optimisations automatiques
            if (this.options.autoOptimize) {
                validMeshes = this.optimizeMeshes(validMeshes)
            }

            // Validation de la complexité
            const totalTriangles = this.calculateTotalTriangles(validMeshes)
            if (totalTriangles > this.options.maxComplexity!) {
                console.warn(`[CAD Engine] Complexité trop élevée: ${totalTriangles} triangles`)
                validMeshes = this.simplifyMeshes(validMeshes)
            }

            // Enregistrement dans l'historique
            this.executionHistory.push({
                code,
                timestamp: Date.now(),
                success: true,
                meshCount: validMeshes.length
            })

            const executionTime = Date.now() - startTime
            console.log(`[CAD Engine] Exécution réussie: ${validMeshes.length} meshes en ${executionTime}ms`)

            return validMeshes

        } catch (error) {
            console.error('[CAD Engine] Erreur d\'exécution:', error)

            // Enregistrement de l'échec
            this.executionHistory.push({
                code,
                timestamp: Date.now(),
                success: false,
                meshCount: 0
            })

            // Retour d'un shape de fallback au lieu de crasher
            return [this.createFallbackShape('cube')]
        }
    }

    // Extraction des paramètres d'un code généré
    extractParameters(code: string) {
        if (!this.options.enableParametricExtraction) {
            return []
        }

        try {
            return this.parametricEngine.extractParameters(code)
        } catch (error) {
            console.error('[CAD Engine] Erreur extraction paramètres:', error)
            return []
        }
    }

    // Génération d'un modèle paramétrique
    generateParametricModel(code: string) {
        if (!this.options.enableParametricExtraction) {
            throw new Error('Extraction paramétrique désactivée')
        }

        const parameters = this.extractParameters(code)
        return this.parametricEngine.generateParametricCode(code, parameters)
    }

    // Exécution avec paramètres personnalisés
    async executeWithParameters(
        parametricModel: any,
        customParameters: Record<string, number>
    ): Promise<THREE.Mesh[]> {
        try {
            const meshes = this.parametricEngine.executeParametricModel(
                parametricModel,
                customParameters
            )

            return this.validateMeshes(meshes)
        } catch (error) {
            console.error('[CAD Engine] Erreur exécution paramétrique:', error)
            return []
        }
    }

    private createExecutionContext() {
        const context = {
            THREE,
            CSG: this.options.enableCSG ? CSG : undefined,
            Math,
            console: {
                log: (...args: any[]) => console.log('[CAD Code]', ...args),
                warn: (...args: any[]) => console.warn('[CAD Code]', ...args),
                error: (...args: any[]) => console.error('[CAD Code]', ...args)
            },
            // Fonctions d'aide pour la génération
            createParametricShape: this.createParametricShape.bind(this),
            optimizeGeometry: this.optimizeGeometry.bind(this),

            // Formes avancées (si activées)
            ...(this.options.enableAdvancedShapes ? {
                createGear: (this as any).createGear?.bind(this),
                createSpring: (this as any).createSpring?.bind(this),
                createRibbledBracket: (this as any).createRibbledBracket?.bind(this),
                createVentilatedEnclosure: (this as any).createVentilatedEnclosure?.bind(this),
                createThreadedConnector: (this as any).createThreadedConnector?.bind(this),
                createToolHolder: (this as any).createToolHolder?.bind(this)
            } : {}),

            // Utilitaires
            randomInRange: (min: number, max: number) => Math.random() * (max - min) + min,
            clamp: (value: number, min: number, max: number) => Math.min(Math.max(value, min), max),
            lerp: (a: number, b: number, t: number) => a + (b - a) * t
        }

        return context
    }

    private async executeWithTimeout(
        code: string,
        context: any,
        timeout: number
    ): Promise<any> {
        return new Promise((resolve, reject) => {
            const timer = setTimeout(() => {
                reject(new Error('Timeout d\'exécution dépassé'))
            }, timeout)

            try {
                const functionBody = `
          const { THREE, CSG, Math, console, createParametricShape, optimizeGeometry, 
                  createGear, createSpring, createRibbledBracket, createVentilatedEnclosure,
                  createThreadedConnector, createToolHolder, randomInRange, clamp, lerp } = this;
          
          try {
            ${code}
            
            // Si fonction generateModel existe, l'appeler
            if (typeof generateModel === 'function') {
              return generateModel();
            }
            
            // Sinon chercher un tableau meshes
            if (typeof meshes !== 'undefined' && Array.isArray(meshes)) {
              return meshes;
            }
            
            console.warn('Aucune fonction generateModel ou variable meshes trouvée');
            return [];
            
          } catch (error) {
            console.error('Erreur dans le code utilisateur:', error);
            return [];
          }
        `

                const executeFunction = new Function(functionBody)
                const result = executeFunction.call(context)

                clearTimeout(timer)
                resolve(result)

            } catch (error) {
                clearTimeout(timer)
                reject(error)
            }
        })
    }

    private sanitizeCode(code: string): string {
        // NE RIEN NETTOYER - Le code du serveur est maintenant propre
        console.log('Code original:', code)
        console.log('Code nettoyé:', code) // Pas de nettoyage
        return code.trim()
    }

    private hasDangerousPatterns(code: string): boolean {
        const dangerousPatterns = [
            /while\s*\(\s*true\s*\)/, // Boucles infinies
            /for\s*\([^)]*;\s*true\s*;/, // Boucles infinies
            /eval\s*\(/, // eval
            /Function\s*\(/, // Constructor Function
            /setTimeout|setInterval/, // Timers
            /XMLHttpRequest|fetch/, // Requêtes réseau
            /localStorage|sessionStorage/, // Storage
            /\.innerHTML\s*=/, // Manipulation DOM
            /alert\s*\(|confirm\s*\(|prompt\s*\(/ // Dialogs
        ]

        return dangerousPatterns.some(pattern => pattern.test(code))
    }

    private wrapCode(code: string): string {
        // Si le code contient déjà une fonction generateModel, pas besoin de wrapper
        if (code.includes('function generateModel')) {
            return code
        }

        // Sinon, wrapper le code
        return `
      function generateModel() {
        const meshes = []
        
        try {
          ${code}
          return meshes
        } catch (error) {
          console.error('Erreur dans la génération:', error)
          return []
        }
      }
    `
    }

    private filterValidMeshes(result: any[]): THREE.Mesh[] {
        return result.filter((item: any) => {
            // Vérifier si c'est un mesh valide
            if (!item) return false

            if (item.isMesh || (item.geometry && item.material)) {
                return true
            }

            // Vérifier si c'est un Group contenant des meshes
            if (item.isGroup) {
                let hasMeshes = false
                item.traverse((child: any) => {
                    if (child.isMesh) hasMeshes = true
                })
                return hasMeshes
            }

            return false
        }).map((item: any) => {
            // Convertir en mesh si nécessaire
            if (item.isMesh) {
                return item
            }

            if (item.isGroup) {
                // Pour les groupes, créer un mesh combiné (simplification)
                const geometry = new THREE.BufferGeometry()
                const material = new THREE.MeshStandardMaterial({ color: 0x888888 })
                return new THREE.Mesh(geometry, material)
            }

            // Créer un mesh à partir d'une géométrie
            const material = item.material || new THREE.MeshStandardMaterial({ color: 0x888888 })
            return new THREE.Mesh(item.geometry, material)
        })
    }

    private calculateTotalTriangles(meshes: THREE.Mesh[]): number {
        return meshes.reduce((total, mesh) => {
            if (!mesh.geometry) return total

            const geometry = mesh.geometry as THREE.BufferGeometry
            const position = geometry.getAttribute('position')
            if (!position) return total

            if (geometry.index) {
                return total + geometry.index.count / 3
            } else {
                return total + position.count / 3
            }
        }, 0)
    }

    private simplifyMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        console.log('[CAD Engine] Simplification des meshes pour réduire la complexité')

        return meshes.map((mesh, index) => {
            try {
                // Simplification basique - réduction du niveau de détail
                if (mesh.geometry) {
                    const geometry = mesh.geometry as THREE.BufferGeometry

                    // Si trop de vertices, créer une version simplifiée
                    const position = geometry.getAttribute('position')
                    if (position && position.count > 3000) {
                        // Créer une version LOD (Level of Detail) réduite
                        const simplifiedGeometry = this.createLODGeometry(geometry)
                        mesh.geometry = simplifiedGeometry
                    }
                }

                return mesh
            } catch (error) {
                console.warn(`[CAD Engine] Erreur simplification mesh ${index}:`, error)
                return mesh
            }
        })
    }

    private createLODGeometry(originalGeometry: THREE.BufferGeometry): THREE.BufferGeometry {
        // Implémentation simplifiée - dans la pratique, utiliser une lib de simplification
        originalGeometry.computeBoundingBox()
        if (!originalGeometry.boundingBox) return originalGeometry

        const size = originalGeometry.boundingBox.getSize(new THREE.Vector3())
        const maxDim = Math.max(size.x, size.y, size.z)

        // Créer une géométrie simplifiée basée sur la forme générale
        if (maxDim > 0) {
            const segments = Math.max(8, Math.min(32, Math.floor(maxDim / 10)))
            return new THREE.BoxGeometry(size.x, size.y, size.z, segments, segments, segments)
        }

        return originalGeometry
    }

    private createParametricShape(type: string, params: any): THREE.Mesh {
        switch (type.toLowerCase()) {
            case 'box':
                return new THREE.Mesh(
                    new THREE.BoxGeometry(params.width || 10, params.height || 10, params.depth || 10),
                    new THREE.MeshStandardMaterial({ color: params.color || 0x666666 })
                )

            case 'sphere':
                return new THREE.Mesh(
                    new THREE.SphereGeometry(params.radius || 5, params.segments || 16, params.segments || 16),
                    new THREE.MeshStandardMaterial({ color: params.color || 0x666666 })
                )

            case 'cylinder':
                return new THREE.Mesh(
                    new THREE.CylinderGeometry(
                        params.radiusTop || 5,
                        params.radiusBottom || 5,
                        params.height || 10,
                        params.segments || 16
                    ),
                    new THREE.MeshStandardMaterial({ color: params.color || 0x666666 })
                )

            default:
                return this.createFallbackShape()
        }
    }

    private optimizeGeometry(geometry: THREE.BufferGeometry): THREE.BufferGeometry {
        if (!geometry) return geometry

        // Calculer les normales si manquantes
        if (!geometry.getAttribute('normal')) {
            geometry.computeVertexNormals()
        }

        // Calculer les bounding box/sphere
        geometry.computeBoundingBox()
        geometry.computeBoundingSphere()

        return geometry
    }

    // Méthodes publiques pour la validation et l'optimisation
    validateMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        return ModelValidator.autoFixMeshes(meshes)
    }

    optimizeMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        return meshes.map(mesh => {
            try {
                // Optimisation de la géométrie
                if (mesh.geometry) {
                    mesh.geometry = this.optimizeGeometry(mesh.geometry as THREE.BufferGeometry)
                }

                // Assurer un matériau valide
                if (!mesh.material) {
                    mesh.material = new THREE.MeshStandardMaterial({
                        color: 0x666666,
                        metalness: 0.3,
                        roughness: 0.7
                    })
                }

                return mesh
            } catch (error) {
                console.warn('[CAD Engine] Erreur optimisation mesh:', error)
                return mesh
            }
        })
    }

    createFallbackShape(type: 'cube' | 'sphere' | 'cylinder' = 'cube'): THREE.Mesh {
        let geometry: THREE.BufferGeometry

        switch (type) {
            case 'sphere':
                geometry = new THREE.SphereGeometry(10, 16, 16)
                break
            case 'cylinder':
                geometry = new THREE.CylinderGeometry(5, 5, 20, 16)
                break
            default:
                geometry = new THREE.BoxGeometry(20, 20, 20)
        }

        const material = new THREE.MeshStandardMaterial({
            color: 0xff6b6b,
            transparent: true,
            opacity: 0.8,
            metalness: 0.1,
            roughness: 0.8
        })

        const mesh = new THREE.Mesh(geometry, material)
        mesh.position.set(0, 10, 0)

        return mesh
    }

    // Méthodes pour les statistiques et le debugging
    getExecutionStats() {
        const recent = this.executionHistory.slice(-10)
        const successRate = recent.filter(h => h.success).length / recent.length * 100

        return {
            totalExecutions: this.executionHistory.length,
            recentSuccessRate: successRate,
            averageExecutionTime: this.calculateAverageExecutionTime(),
            lastExecution: this.executionHistory[this.executionHistory.length - 1]
        }
    }

    private calculateAverageExecutionTime(): number {
        if (this.executionHistory.length < 2) return 0

        const recent = this.executionHistory.slice(-5)
        let totalTime = 0

        for (let i = 1; i < recent.length; i++) {
            totalTime += recent[i].timestamp - recent[i - 1].timestamp
        }

        return totalTime / (recent.length - 1)
    }

    clearHistory() {
        this.executionHistory = []
    }

    // Diagnostic et debug
    diagnoseCode(code: string): {
        issues: string[]
        suggestions: string[]
        complexity: 'low' | 'medium' | 'high'
        estimatedExecutionTime: number
    } {
        const issues: string[] = []
        const suggestions: string[] = []

        // Analyse de la complexité
        const loopCount = (code.match(/for\s*\(|while\s*\(/g) || []).length
        const geometryCount = (code.match(/new THREE\.\w+Geometry/g) || []).length
        const meshCount = (code.match(/new THREE\.Mesh/g) || []).length

        let complexity: 'low' | 'medium' | 'high' = 'low'

        if (loopCount > 5 || geometryCount > 10 || meshCount > 10) {
            complexity = 'high'
            suggestions.push('Considérer la réduction du nombre de boucles ou d\'objets')
        } else if (loopCount > 2 || geometryCount > 5 || meshCount > 5) {
            complexity = 'medium'
        }

        // Vérifications spécifiques
        if (!code.includes('meshes.push')) {
            issues.push('Aucun objet n\'est ajouté au tableau meshes')
            suggestions.push('Utiliser meshes.push(votreObject) pour ajouter des objets')
        }

        if (code.includes('CSG') && !this.options.enableCSG) {
            issues.push('Opérations CSG utilisées mais désactivées')
            suggestions.push('Activer les opérations CSG dans les options')
        }

        const estimatedExecutionTime = loopCount * 10 + geometryCount * 5 + meshCount * 2

        return {
            issues,
            suggestions,
            complexity,
            estimatedExecutionTime
        }
    }
}