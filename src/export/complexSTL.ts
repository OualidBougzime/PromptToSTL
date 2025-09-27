// src/export/complexSTL.ts - Version Optimisée
import * as THREE from 'three'

interface Triangle {
    normal: THREE.Vector3
    vertices: [THREE.Vector3, THREE.Vector3, THREE.Vector3]
}

export interface STLExportOptions {
    binary?: boolean
    mergeVertices?: boolean
    smoothNormals?: boolean
    scale?: number
    units?: 'mm' | 'cm' | 'in' | 'm'
    precision?: number
    removeDegenerate?: boolean
    flipNormals?: boolean
}

export class OptimizedSTLExporter {

    static export(meshes: THREE.Mesh[], options: STLExportOptions = {}): ArrayBuffer | string {
        const {
            binary = true,
            mergeVertices = true,
            smoothNormals = false,
            scale = 1,
            units = 'mm',
            precision = 6,
            removeDegenerate = true,
            flipNormals = false
        } = options

        console.log(`[STL Export] Démarrage export ${binary ? 'binaire' : 'ASCII'}`)

        // Prétraitement des meshes
        const processedMeshes = this.preprocessMeshes(meshes, {
            mergeVertices,
            smoothNormals,
            scale: scale * this.getUnitScale(units),
            removeDegenerate
        })

        // Extraction des triangles
        const triangles = this.extractTriangles(processedMeshes, flipNormals)

        console.log(`[STL Export] ${triangles.length} triangles extraits`)

        // Export selon le format
        if (binary) {
            return this.exportBinarySTL(triangles)
        } else {
            return this.exportASCIISTL(triangles, precision)
        }
    }

    private static preprocessMeshes(
        meshes: THREE.Mesh[],
        options: {
            mergeVertices: boolean
            smoothNormals: boolean
            scale: number
            removeDegenerate: boolean
        }
    ): THREE.Mesh[] {
        return meshes.map(mesh => {
            if (!mesh || !mesh.geometry) return mesh

            const clonedMesh = mesh.clone()
            let geometry = clonedMesh.geometry.clone()

            // Mise à l'échelle
            if (options.scale !== 1) {
                geometry.scale(options.scale, options.scale, options.scale)
            }

            // Mise à jour de la matrice monde
            clonedMesh.updateMatrixWorld(true)

            // Application de la transformation au niveau des vertices
            geometry.applyMatrix4(clonedMesh.matrixWorld)

            // Fusion des vertices si demandée (implémentation simplifiée)
            if (options.mergeVertices) {
                geometry = this.mergeVertices(geometry)
            }

            // Suppression des triangles dégénérés
            if (options.removeDegenerate) {
                geometry = this.removeDegenerateTriangles(geometry)
            }

            // Calcul des normales
            if (options.smoothNormals || !geometry.getAttribute('normal')) {
                geometry.computeVertexNormals()
            }

            clonedMesh.geometry = geometry

            // Reset transformation (déjà appliquée)
            clonedMesh.position.set(0, 0, 0)
            clonedMesh.rotation.set(0, 0, 0)
            clonedMesh.scale.set(1, 1, 1)
            clonedMesh.updateMatrixWorld(true)

            return clonedMesh
        })
    }

    private static mergeVertices(geometry: THREE.BufferGeometry, tolerance = 1e-4): THREE.BufferGeometry {
        // Implémentation simplifiée de fusion des vertices
        // En production, utiliser THREE.BufferGeometryUtils.mergeVertices()

        const position = geometry.getAttribute('position')
        if (!position) return geometry

        const vertices: THREE.Vector3[] = []
        const indices: number[] = []
        const vertexMap = new Map<string, number>()

        for (let i = 0; i < position.count; i++) {
            const vertex = new THREE.Vector3().fromBufferAttribute(position, i)
            const key = `${Math.round(vertex.x / tolerance)},${Math.round(vertex.y / tolerance)},${Math.round(vertex.z / tolerance)}`

            let index = vertexMap.get(key)
            if (index === undefined) {
                index = vertices.length
                vertices.push(vertex)
                vertexMap.set(key, index)
            }

            indices.push(index)
        }

        // Créer la nouvelle géométrie
        const newGeometry = new THREE.BufferGeometry()
        const positions = new Float32Array(vertices.length * 3)

        vertices.forEach((vertex, i) => {
            positions[i * 3] = vertex.x
            positions[i * 3 + 1] = vertex.y
            positions[i * 3 + 2] = vertex.z
        })

        newGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
        newGeometry.setIndex(indices)

        return newGeometry
    }

    private static removeDegenerateTriangles(geometry: THREE.BufferGeometry): THREE.BufferGeometry {
        const position = geometry.getAttribute('position')
        if (!position) return geometry

        const validTriangles: number[] = []
        const triangleCount = geometry.index ? geometry.index.count / 3 : position.count / 3

        for (let i = 0; i < triangleCount; i++) {
            const i1 = geometry.index ? geometry.index.getX(i * 3) : i * 3
            const i2 = geometry.index ? geometry.index.getX(i * 3 + 1) : i * 3 + 1
            const i3 = geometry.index ? geometry.index.getX(i * 3 + 2) : i * 3 + 2

            const v1 = new THREE.Vector3().fromBufferAttribute(position, i1)
            const v2 = new THREE.Vector3().fromBufferAttribute(position, i2)
            const v3 = new THREE.Vector3().fromBufferAttribute(position, i3)

            // Vérifier si le triangle n'est pas dégénéré
            const edge1 = new THREE.Vector3().subVectors(v2, v1)
            const edge2 = new THREE.Vector3().subVectors(v3, v1)
            const cross = new THREE.Vector3().crossVectors(edge1, edge2)

            if (cross.length() > 1e-10) {
                validTriangles.push(i1, i2, i3)
            }
        }

        if (validTriangles.length === position.count) {
            return geometry // Pas de triangles dégénérés
        }

        // Créer une nouvelle géométrie sans triangles dégénérés
        const newGeometry = new THREE.BufferGeometry()
        newGeometry.setAttribute('position', position)
        newGeometry.setIndex(validTriangles)

        return newGeometry
    }

    private static extractTriangles(meshes: THREE.Mesh[], flipNormals = false): Triangle[] {
        const triangles: Triangle[] = []

        for (const mesh of meshes) {
            if (!mesh || !mesh.geometry) continue

            const geometry = mesh.geometry as THREE.BufferGeometry
            const position = geometry.getAttribute('position')
            if (!position) continue

            let normals = geometry.getAttribute('normal')
            if (!normals) {
                geometry.computeVertexNormals()
                normals = geometry.getAttribute('normal')
            }

            const indices = geometry.getIndex()
            const triangleCount = indices ? indices.count / 3 : position.count / 3

            for (let i = 0; i < triangleCount; i++) {
                const i1 = indices ? indices.getX(i * 3) : i * 3
                const i2 = indices ? indices.getX(i * 3 + 1) : i * 3 + 1
                const i3 = indices ? indices.getX(i * 3 + 2) : i * 3 + 2

                const triangle = this.createTriangle(position, normals, i1, i2, i3, flipNormals)
                if (triangle) {
                    triangles.push(triangle)
                }
            }
        }

        return triangles
    }

    private static createTriangle(
        position: THREE.BufferAttribute,
        normals: THREE.BufferAttribute,
        i1: number,
        i2: number,
        i3: number,
        flipNormals: boolean
    ): Triangle | null {
        try {
            // Vertices
            const v1 = new THREE.Vector3().fromBufferAttribute(position, i1)
            const v2 = new THREE.Vector3().fromBufferAttribute(position, i2)
            const v3 = new THREE.Vector3().fromBufferAttribute(position, i3)

            // Normale (moyenne des normales des vertices)
            const n1 = new THREE.Vector3().fromBufferAttribute(normals, i1)
            const n2 = new THREE.Vector3().fromBufferAttribute(normals, i2)
            const n3 = new THREE.Vector3().fromBufferAttribute(normals, i3)

            const normal = new THREE.Vector3()
                .addVectors(n1, n2)
                .add(n3)
                .divideScalar(3)
                .normalize()

            // Validation du triangle
            const edge1 = new THREE.Vector3().subVectors(v2, v1)
            const edge2 = new THREE.Vector3().subVectors(v3, v1)
            const computedNormal = new THREE.Vector3().crossVectors(edge1, edge2)

            if (computedNormal.length() < 1e-10) {
                return null // Triangle dégénéré
            }

            // Utiliser la normale calculée si elle est plus fiable
            if (normal.length() < 0.5) {
                normal.copy(computedNormal.normalize())
            }

            // Retourner la normale si demandé
            if (flipNormals) {
                normal.multiplyScalar(-1)
            }

            // Vérifier la validité des coordonnées
            if (!this.isValidVector(v1) || !this.isValidVector(v2) ||
                !this.isValidVector(v3) || !this.isValidVector(normal)) {
                return null
            }

            return {
                normal,
                vertices: [v1, v2, v3]
            }
        } catch (error) {
            console.warn('Erreur création triangle:', error)
            return null
        }
    }

    private static isValidVector(v: THREE.Vector3): boolean {
        return isFinite(v.x) && isFinite(v.y) && isFinite(v.z)
    }

    private static exportBinarySTL(triangles: Triangle[]): ArrayBuffer {
        const bufferSize = 80 + 4 + (triangles.length * 50) // Header + count + triangles
        const buffer = new ArrayBuffer(bufferSize)
        const view = new DataView(buffer)

        // Header (80 bytes)
        const header = 'STL Binary - Generated by CAD Engine v2.0'
        const encoder = new TextEncoder()
        const headerBytes = encoder.encode(header)
        const headerArray = new Uint8Array(buffer, 0, 80)
        headerArray.set(headerBytes.slice(0, 80))

        // Triangle count (4 bytes)
        view.setUint32(80, triangles.length, true)

        // Triangles (50 bytes each)
        let offset = 84
        for (const triangle of triangles) {
            // Normal vector (12 bytes)
            view.setFloat32(offset, triangle.normal.x, true)
            view.setFloat32(offset + 4, triangle.normal.y, true)
            view.setFloat32(offset + 8, triangle.normal.z, true)
            offset += 12

            // Vertices (36 bytes)
            for (const vertex of triangle.vertices) {
                view.setFloat32(offset, vertex.x, true)
                view.setFloat32(offset + 4, vertex.y, true)
                view.setFloat32(offset + 8, vertex.z, true)
                offset += 12
            }

            // Attribute byte count (2 bytes) - always 0
            view.setUint16(offset, 0, true)
            offset += 2
        }

        console.log(`[STL Export] STL binaire généré: ${triangles.length} triangles, ${bufferSize} bytes`)
        return buffer
    }

    private static exportASCIISTL(triangles: Triangle[], precision: number): string {
        const lines: string[] = []
        lines.push('solid CAD_Generated_Model_v2')

        for (const triangle of triangles) {
            const { normal, vertices } = triangle

            lines.push(`  facet normal ${this.formatNumber(normal.x, precision)} ${this.formatNumber(normal.y, precision)} ${this.formatNumber(normal.z, precision)}`)
            lines.push('    outer loop')

            for (const vertex of vertices) {
                lines.push(`      vertex ${this.formatNumber(vertex.x, precision)} ${this.formatNumber(vertex.y, precision)} ${this.formatNumber(vertex.z, precision)}`)
            }

            lines.push('    endloop')
            lines.push('  endfacet')
        }

        lines.push('endsolid CAD_Generated_Model_v2')

        const result = lines.join('\n')
        console.log(`[STL Export] STL ASCII généré: ${triangles.length} triangles, ${result.length} caractères`)
        return result
    }

    private static formatNumber(num: number, precision: number): string {
        if (!isFinite(num)) return '0.000000'
        return num.toFixed(precision)
    }

    private static getUnitScale(units: 'mm' | 'cm' | 'in' | 'm'): number {
        switch (units) {
            case 'cm': return 10
            case 'in': return 25.4
            case 'm': return 1000
            default: return 1 // mm
        }
    }
}

// Fonctions de commodité pour maintenir la compatibilité
export function exportComplexSTL(meshes: THREE.Mesh[]): string {
    return OptimizedSTLExporter.export(meshes, { binary: false }) as string
}

export function exportComplexSTLBinary(meshes: THREE.Mesh[]): ArrayBuffer {
    return OptimizedSTLExporter.export(meshes, { binary: true }) as ArrayBuffer
}

export function downloadSTL(
    meshes: THREE.Mesh[],
    filename: string = 'model.stl',
    options: STLExportOptions = {}
): void {
    try {
        const result = OptimizedSTLExporter.export(meshes, options)

        let blob: Blob
        let suggestedName = filename

        if (options.binary !== false) {
            blob = new Blob([result as ArrayBuffer], { type: 'application/octet-stream' })
            if (!suggestedName.endsWith('.stl')) {
                suggestedName += '.stl'
            }
        } else {
            blob = new Blob([result as string], { type: 'text/plain' })
            if (!suggestedName.endsWith('.stl')) {
                suggestedName += '.stl'
            }
        }

        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = suggestedName
        a.click()

        URL.revokeObjectURL(url)

        console.log(`[STL Export] Téléchargement initié: ${suggestedName}`)
    } catch (error) {
        console.error('Erreur téléchargement STL:', error)
        throw error
    }
}

// Validation de la qualité STL
export function validateSTL(meshes: THREE.Mesh[]): {
    isValid: boolean
    triangleCount: number
    issues: string[]
    fileSize: number
} {
    const issues: string[] = []
    let triangleCount = 0

    if (meshes.length === 0) {
        issues.push('Aucun mesh à exporter')
        return { isValid: false, triangleCount: 0, issues, fileSize: 0 }
    }

    for (const mesh of meshes) {
        if (!mesh || !mesh.geometry) {
            issues.push('Mesh sans géométrie trouvé')
            continue
        }

        const geometry = mesh.geometry as THREE.BufferGeometry
        const position = geometry.getAttribute('position')

        if (!position) {
            issues.push('Géométrie sans positions trouvée')
            continue
        }

        const meshTriangleCount = geometry.index ? geometry.index.count / 3 : position.count / 3
        triangleCount += meshTriangleCount

        // Vérifier les coordonnées valides
        for (let i = 0; i < position.count; i++) {
            const x = position.getX(i)
            const y = position.getY(i)
            const z = position.getZ(i)

            if (!isFinite(x) || !isFinite(y) || !isFinite(z)) {
                issues.push('Coordonnées invalides détectées')
                break
            }
        }
    }

    if (triangleCount === 0) {
        issues.push('Aucun triangle valide trouvé')
    }

    // Estimation de la taille du fichier
    const estimatedSize = 84 + (triangleCount * 50) // STL binaire

    return {
        isValid: issues.length === 0,
        triangleCount: Math.floor(triangleCount),
        issues,
        fileSize: estimatedSize
    }
}