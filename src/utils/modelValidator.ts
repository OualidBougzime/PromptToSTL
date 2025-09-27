// src/utils/modelValidator.ts
import * as THREE from 'three'
import { ModelValidation, ModelAnalytics } from '../types/parameters'

export class ModelValidator {

    static validateMeshes(meshes: THREE.Mesh[]): ModelValidation {
        const issues: string[] = []
        const suggestions: string[] = []
        let totalTriangles = 0
        let totalVertices = 0

        if (meshes.length === 0) {
            return {
                isValid: false,
                issues: ['Aucun mesh généré'],
                suggestions: ['Vérifiez le code généré'],
                triangleCount: 0,
                vertexCount: 0
            }
        }

        meshes.forEach((mesh, index) => {
            const meshIssues = this.validateSingleMesh(mesh, index)
            issues.push(...meshIssues.issues)
            suggestions.push(...meshIssues.suggestions)
            totalTriangles += meshIssues.triangleCount
            totalVertices += meshIssues.vertexCount
        })

        // Validation globale
        if (totalTriangles > 100000) {
            issues.push('Modèle très complexe (>100k triangles)')
            suggestions.push('Réduire le niveau de détail pour de meilleures performances')
        }

        if (totalTriangles < 12) {
            issues.push('Modèle très simple (<12 triangles)')
            suggestions.push('Le modèle pourrait manquer de détails')
        }

        return {
            isValid: issues.length === 0,
            issues,
            suggestions,
            triangleCount: totalTriangles,
            vertexCount: totalVertices
        }
    }

    private static validateSingleMesh(mesh: THREE.Mesh, index: number): {
        issues: string[]
        suggestions: string[]
        triangleCount: number
        vertexCount: number
    } {
        const issues: string[] = []
        const suggestions: string[] = []
        let triangleCount = 0
        let vertexCount = 0

        if (!mesh) {
            issues.push(`Mesh ${index}: null ou undefined`)
            return { issues, suggestions, triangleCount, vertexCount }
        }

        if (!mesh.geometry) {
            issues.push(`Mesh ${index}: géométrie manquante`)
            return { issues, suggestions, triangleCount, vertexCount }
        }

        const geometry = mesh.geometry as THREE.BufferGeometry
        const position = geometry.getAttribute('position')

        if (!position) {
            issues.push(`Mesh ${index}: attribut position manquant`)
            return { issues, suggestions, triangleCount, vertexCount }
        }

        vertexCount = position.count

        if (vertexCount === 0) {
            issues.push(`Mesh ${index}: géométrie vide`)
            return { issues, suggestions, triangleCount, vertexCount }
        }

        // Calculer le nombre de triangles
        if (geometry.index) {
            triangleCount = geometry.index.count / 3
        } else {
            triangleCount = vertexCount / 3
        }

        // Vérifier les coordonnées invalides
        const invalidCoords = this.checkForInvalidCoordinates(position)
        if (invalidCoords.count > 0) {
            issues.push(`Mesh ${index}: ${invalidCoords.count} coordonnées invalides`)
            suggestions.push('Vérifier les calculs de position dans le code')
        }

        // Vérifier la taille du mesh
        geometry.computeBoundingBox()
        if (geometry.boundingBox) {
            const size = geometry.boundingBox.getSize(new THREE.Vector3())
            const maxDim = Math.max(size.x, size.y, size.z)
            const minDim = Math.min(size.x, size.y, size.z)

            if (maxDim > 1000) {
                issues.push(`Mesh ${index}: très volumineux (${maxDim.toFixed(1)}mm)`)
                suggestions.push('Considérer une mise à l\'échelle')
            }

            if (maxDim < 0.1) {
                issues.push(`Mesh ${index}: très petit (${maxDim.toFixed(3)}mm)`)
                suggestions.push('Augmenter les dimensions')
            }

            if (minDim / maxDim < 0.001) {
                issues.push(`Mesh ${index}: géométrie très aplatie`)
                suggestions.push('Vérifier les proportions')
            }
        }

        // Vérifier les normales
        const normal = geometry.getAttribute('normal')
        if (!normal) {
            suggestions.push(`Mesh ${index}: normales manquantes (calculées automatiquement)`)
        }

        // Vérifier le matériau
        if (!mesh.material) {
            issues.push(`Mesh ${index}: matériau manquant`)
        } else if (Array.isArray(mesh.material)) {
            if (mesh.material.length === 0) {
                issues.push(`Mesh ${index}: tableau de matériaux vide`)
            }
        }

        return { issues, suggestions, triangleCount, vertexCount }
    }

    private static checkForInvalidCoordinates(position: THREE.BufferAttribute): {
        count: number
        examples: number[]
    } {
        let invalidCount = 0
        const examples: number[] = []

        for (let i = 0; i < position.count && examples.length < 5; i++) {
            const x = position.getX(i)
            const y = position.getY(i)
            const z = position.getZ(i)

            if (!isFinite(x) || !isFinite(y) || !isFinite(z)) {
                invalidCount++
                examples.push(i)
            }
        }

        return { count: invalidCount, examples }
    }

    static autoFixMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        return meshes.map((mesh, index) => {
            try {
                return this.autoFixSingleMesh(mesh)
            } catch (error) {
                console.warn(`Erreur lors de la correction du mesh ${index}:`, error)
                return mesh
            }
        }).filter(mesh => mesh !== null)
    }

    private static autoFixSingleMesh(mesh: THREE.Mesh): THREE.Mesh {
        if (!mesh || !mesh.geometry) return mesh

        const geometry = mesh.geometry as THREE.BufferGeometry

        // Calculer les normales si manquantes
        if (!geometry.getAttribute('normal')) {
            geometry.computeVertexNormals()
        }

        // Calculer la bounding box si manquante
        if (!geometry.boundingBox) {
            geometry.computeBoundingBox()
        }

        // Calculer la bounding sphere
        if (!geometry.boundingSphere) {
            geometry.computeBoundingSphere()
        }

        // Assurer un matériau valide
        if (!mesh.material) {
            mesh.material = new THREE.MeshStandardMaterial({
                color: 0x666666,
                metalness: 0.3,
                roughness: 0.7
            })
        }

        // Nettoyer les attributs inutiles
        geometry.deleteAttribute('uv2')

        return mesh
    }

    static generateAnalytics(meshes: THREE.Mesh[]): ModelAnalytics {
        let totalVertices = 0
        let totalTriangles = 0
        let totalVolume = 0
        const boundingBox = new THREE.Box3()

        meshes.forEach(mesh => {
            if (!mesh || !mesh.geometry) return

            const geometry = mesh.geometry as THREE.BufferGeometry
            const position = geometry.getAttribute('position')

            if (position) {
                totalVertices += position.count
                if (geometry.index) {
                    totalTriangles += geometry.index.count / 3
                } else {
                    totalTriangles += position.count / 3
                }
            }

            // Calcul du volume approximatif
            geometry.computeBoundingBox()
            if (geometry.boundingBox) {
                const size = geometry.boundingBox.getSize(new THREE.Vector3())
                totalVolume += size.x * size.y * size.z

                // Mise à jour du mesh world matrix pour des calculs précis
                mesh.updateMatrixWorld(true)
                const worldBoundingBox = geometry.boundingBox.clone()
                worldBoundingBox.applyMatrix4(mesh.matrixWorld)

                boundingBox.union(worldBoundingBox)
            }
        })

        const overallSize = boundingBox.getSize(new THREE.Vector3())
        const printability = this.assessPrintability(meshes)

        return {
            meshCount: meshes.length,
            totalVertices: Math.floor(totalVertices),
            totalTriangles: Math.floor(totalTriangles),
            estimatedVolume: Math.round(totalVolume * 100) / 100,
            dimensions: {
                width: Math.round(overallSize.x * 100) / 100,
                height: Math.round(overallSize.y * 100) / 100,
                depth: Math.round(overallSize.z * 100) / 100
            },
            complexity: this.getComplexityRating(totalTriangles),
            printability
        }
    }

    private static getComplexityRating(triangles: number): 'Simple' | 'Moyen' | 'Complexe' | 'Très complexe' {
        if (triangles < 1000) return 'Simple'
        if (triangles < 10000) return 'Moyen'
        if (triangles < 50000) return 'Complexe'
        return 'Très complexe'
    }

    private static assessPrintability(meshes: THREE.Mesh[]): {
        score: number
        issues: string[]
        suggestions: string[]
    } {
        const issues: string[] = []
        const suggestions: string[] = []
        let score = 100

        // Analyser chaque mesh pour les problèmes d'impression
        meshes.forEach((mesh, index) => {
            if (!mesh || !mesh.geometry) return

            const geometry = mesh.geometry as THREE.BufferGeometry
            geometry.computeBoundingBox()

            if (!geometry.boundingBox) return

            const size = geometry.boundingBox.getSize(new THREE.Vector3())
            const center = geometry.boundingBox.getCenter(new THREE.Vector3())

            // Vérifier les surplombs (ratio hauteur/largeur élevé)
            const aspectRatio = size.y / Math.max(size.x, size.z)
            if (aspectRatio > 4) {
                issues.push(`Mesh ${index}: ratio hauteur/largeur élevé (${aspectRatio.toFixed(1)})`)
                suggestions.push('Ajouter des supports d\'impression')
                score -= 15
            }

            // Vérifier la taille minimale des détails
            const minDim = Math.min(size.x, size.y, size.z)
            if (minDim < 0.4) {
                issues.push(`Mesh ${index}: détails très fins (${minDim.toFixed(2)}mm)`)
                suggestions.push('Augmenter l\'épaisseur minimale à 0.4mm')
                score -= 10
            }

            // Vérifier les géométries suspendues
            if (center.y > size.y * 0.3 && size.y > 10) {
                issues.push(`Mesh ${index}: géométrie potentiellement suspendue`)
                suggestions.push('Considérer l\'orientation d\'impression')
                score -= 10
            }

            // Vérifier la taille maximale (lit d'impression)
            const maxPrintDim = 200 // mm, taille typique d'imprimante 3D
            const maxMeshDim = Math.max(size.x, size.y, size.z)
            if (maxMeshDim > maxPrintDim) {
                issues.push(`Mesh ${index}: trop grand pour impression (${maxMeshDim.toFixed(1)}mm)`)
                suggestions.push(`Réduire à moins de ${maxPrintDim}mm ou diviser en parties`)
                score -= 20
            }

            // Vérifier les angles aigus
            if (this.hasSharpAngles(geometry)) {
                issues.push(`Mesh ${index}: angles très aigus détectés`)
                suggestions.push('Arrondir les angles pour éviter les défauts')
                score -= 5
            }
        })

        return {
            score: Math.max(0, score),
            issues,
            suggestions
        }
    }

    private static hasSharpAngles(geometry: THREE.BufferGeometry): boolean {
        // Analyse simplifiée - dans une vraie implémentation, 
        // on analyserait les normales des faces adjacentes
        const position = geometry.getAttribute('position')
        if (!position || position.count < 9) return false

        // Vérification basique sur quelques triangles
        for (let i = 0; i < Math.min(position.count - 6, 30); i += 9) {
            const v1 = new THREE.Vector3().fromBufferAttribute(position, i)
            const v2 = new THREE.Vector3().fromBufferAttribute(position, i + 1)
            const v3 = new THREE.Vector3().fromBufferAttribute(position, i + 2)

            const edge1 = new THREE.Vector3().subVectors(v2, v1)
            const edge2 = new THREE.Vector3().subVectors(v3, v1)

            const angle = edge1.angleTo(edge2)

            // Angle très aigu (< 15°) ou très obtus (> 165°)
            if (angle < Math.PI / 12 || angle > Math.PI * 11 / 12) {
                return true
            }
        }

        return false
    }

    static generateQualityReport(meshes: THREE.Mesh[]): {
        validation: ModelValidation
        analytics: ModelAnalytics
        recommendations: string[]
        overallScore: number
    } {
        const validation = this.validateMeshes(meshes)
        const analytics = this.generateAnalytics(meshes)
        const recommendations: string[] = []

        // Générer des recommandations
        if (validation.triangleCount > 50000) {
            recommendations.push('🔧 Optimiser le maillage pour réduire le nombre de triangles')
        }

        if (analytics.printability.score < 70) {
            recommendations.push('🖨️ Améliorer la géométrie pour l\'impression 3D')
        }

        if (analytics.dimensions.width < 1 || analytics.dimensions.height < 1) {
            recommendations.push('📏 Vérifier l\'échelle du modèle')
        }

        if (analytics.complexity === 'Très complexe') {
            recommendations.push('⚡ Simplifier la géométrie pour de meilleures performances')
        }

        if (validation.issues.length === 0) {
            recommendations.push('✅ Modèle de qualité, prêt pour l\'export')
        }

        // Calcul du score global
        let overallScore = 100
        overallScore -= validation.issues.length * 10
        overallScore -= (100 - analytics.printability.score) * 0.5

        if (analytics.complexity === 'Très complexe') overallScore -= 10
        if (analytics.triangleCount < 12) overallScore -= 15

        overallScore = Math.max(0, Math.min(100, overallScore))

        return {
            validation,
            analytics,
            recommendations,
            overallScore: Math.round(overallScore)
        }
    }
}