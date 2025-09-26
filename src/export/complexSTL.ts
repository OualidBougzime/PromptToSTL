import * as THREE from 'three'

interface Triangle {
    normal: THREE.Vector3
    vertices: [THREE.Vector3, THREE.Vector3, THREE.Vector3]
}

export function exportComplexSTL(meshes: THREE.Mesh[]): string {
    const triangles: Triangle[] = []

    for (const mesh of meshes) {
        if (!mesh || !mesh.geometry) continue

        const geometry = mesh.geometry as THREE.BufferGeometry
        const worldMatrix = mesh.matrixWorld.clone()
        const normalMatrix = new THREE.Matrix3().getNormalMatrix(worldMatrix)

        // Get position attribute
        const positions = geometry.getAttribute('position')
        if (!positions) continue

        // Get normal attribute or compute it
        let normals = geometry.getAttribute('normal')
        if (!normals) {
            geometry.computeVertexNormals()
            normals = geometry.getAttribute('normal')
        }

        // Get index attribute if exists
        const indices = geometry.getIndex()

        if (indices) {
            // Indexed geometry
            for (let i = 0; i < indices.count; i += 3) {
                const a = indices.getX(i)
                const b = indices.getX(i + 1)
                const c = indices.getX(i + 2)

                const triangle = extractTriangle(positions, normals, a, b, c, worldMatrix, normalMatrix)
                if (triangle) triangles.push(triangle)
            }
        } else {
            // Non-indexed geometry
            for (let i = 0; i < positions.count; i += 3) {
                const triangle = extractTriangle(positions, normals, i, i + 1, i + 2, worldMatrix, normalMatrix)
                if (triangle) triangles.push(triangle)
            }
        }
    }

    return generateSTLString(triangles)
}

function extractTriangle(
    positions: THREE.BufferAttribute,
    normals: THREE.BufferAttribute,
    a: number,
    b: number,
    c: number,
    worldMatrix: THREE.Matrix4,
    normalMatrix: THREE.Matrix3
): Triangle | null {
    try {
        // Get vertices
        const vA = new THREE.Vector3().fromBufferAttribute(positions, a).applyMatrix4(worldMatrix)
        const vB = new THREE.Vector3().fromBufferAttribute(positions, b).applyMatrix4(worldMatrix)
        const vC = new THREE.Vector3().fromBufferAttribute(positions, c).applyMatrix4(worldMatrix)

        // Get normals
        const nA = new THREE.Vector3().fromBufferAttribute(normals, a).applyMatrix3(normalMatrix).normalize()
        const nB = new THREE.Vector3().fromBufferAttribute(normals, b).applyMatrix3(normalMatrix).normalize()
        const nC = new THREE.Vector3().fromBufferAttribute(normals, c).applyMatrix3(normalMatrix).normalize()

        // Average normal (simple approach)
        const normal = new THREE.Vector3()
            .addVectors(nA, nB)
            .add(nC)
            .divideScalar(3)
            .normalize()

        // Validate triangle (check for degenerate triangles)
        const edge1 = new THREE.Vector3().subVectors(vB, vA)
        const edge2 = new THREE.Vector3().subVectors(vC, vA)
        const computedNormal = new THREE.Vector3().crossVectors(edge1, edge2)

        if (computedNormal.length() < 1e-10) {
            return null // Degenerate triangle
        }

        // Use computed normal if it's more reliable
        if (normal.length() < 0.5) {
            normal.copy(computedNormal.normalize())
        }

        return {
            normal,
            vertices: [vA, vB, vC]
        }
    } catch (error) {
        console.warn('Error extracting triangle:', error)
        return null
    }
}

function generateSTLString(triangles: Triangle[]): string {
    const lines: string[] = []
    lines.push('solid CAD_Generated_Model')

    for (const triangle of triangles) {
        const { normal, vertices } = triangle

        // Ensure normal is valid
        if (!isFinite(normal.x) || !isFinite(normal.y) || !isFinite(normal.z)) {
            console.warn('Invalid normal found, using default')
            normal.set(0, 0, 1)
        }

        lines.push(`  facet normal ${formatNumber(normal.x)} ${formatNumber(normal.y)} ${formatNumber(normal.z)}`)
        lines.push('    outer loop')

        for (const vertex of vertices) {
            // Ensure vertex coordinates are valid
            const x = isFinite(vertex.x) ? vertex.x : 0
            const y = isFinite(vertex.y) ? vertex.y : 0
            const z = isFinite(vertex.z) ? vertex.z : 0

            lines.push(`      vertex ${formatNumber(x)} ${formatNumber(y)} ${formatNumber(z)}`)
        }

        lines.push('    endloop')
        lines.push('  endfacet')
    }

    lines.push('endsolid CAD_Generated_Model')

    console.log(`Generated STL with ${triangles.length} triangles`)
    return lines.join('\n')
}

function formatNumber(num: number): string {
    // Format numbers to avoid scientific notation and limit precision
    if (!isFinite(num)) return '0.000000'

    // Round to 6 decimal places
    const rounded = Math.round(num * 1000000) / 1000000
    return rounded.toFixed(6)
}

// Binary STL export (more efficient for large models)
export function exportComplexSTLBinary(meshes: THREE.Mesh[]): ArrayBuffer {
    const triangles: Triangle[] = []

    // Extract triangles (same logic as ASCII version)
    for (const mesh of meshes) {
        if (!mesh || !mesh.geometry) continue

        const geometry = mesh.geometry as THREE.BufferGeometry
        const worldMatrix = mesh.matrixWorld.clone()
        const normalMatrix = new THREE.Matrix3().getNormalMatrix(worldMatrix)

        const positions = geometry.getAttribute('position')
        if (!positions) continue

        let normals = geometry.getAttribute('normal')
        if (!normals) {
            geometry.computeVertexNormals()
            normals = geometry.getAttribute('normal')
        }

        const indices = geometry.getIndex()

        if (indices) {
            for (let i = 0; i < indices.count; i += 3) {
                const a = indices.getX(i)
                const b = indices.getX(i + 1)
                const c = indices.getX(i + 2)
                const triangle = extractTriangle(positions, normals, a, b, c, worldMatrix, normalMatrix)
                if (triangle) triangles.push(triangle)
            }
        } else {
            for (let i = 0; i < positions.count; i += 3) {
                const triangle = extractTriangle(positions, normals, i, i + 1, i + 2, worldMatrix, normalMatrix)
                if (triangle) triangles.push(triangle)
            }
        }
    }

    // Create binary STL
    const bufferSize = 80 + 4 + (triangles.length * 50) // Header + triangle count + triangles
    const buffer = new ArrayBuffer(bufferSize)
    const view = new DataView(buffer)

    // Header (80 bytes)
    const encoder = new TextEncoder()
    const header = encoder.encode('CAD Generated Binary STL')
    const headerArray = new Uint8Array(buffer, 0, 80)
    headerArray.set(header.slice(0, 80))

    // Triangle count (4 bytes)
    view.setUint32(80, triangles.length, true)

    // Triangles (50 bytes each)
    let offset = 84
    for (const triangle of triangles) {
        const { normal, vertices } = triangle

        // Normal vector (12 bytes)
        view.setFloat32(offset, normal.x, true)
        view.setFloat32(offset + 4, normal.y, true)
        view.setFloat32(offset + 8, normal.z, true)
        offset += 12

        // Vertices (36 bytes)
        for (const vertex of vertices) {
            view.setFloat32(offset, vertex.x, true)
            view.setFloat32(offset + 4, vertex.y, true)
            view.setFloat32(offset + 8, vertex.z, true)
            offset += 12
        }

        // Attribute byte count (2 bytes) - typically 0
        view.setUint16(offset, 0, true)
        offset += 2
    }

    console.log(`Generated binary STL with ${triangles.length} triangles`)
    return buffer
}

// Helper function to download binary STL
export function downloadBinarySTL(meshes: THREE.Mesh[], filename: string = 'model.stl') {
    const buffer = exportComplexSTLBinary(meshes)
    const blob = new Blob([buffer], { type: 'application/octet-stream' })
    const url = URL.createObjectURL(blob)

    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()

    URL.revokeObjectURL(url)
}

// Validation function to check STL quality
export function validateSTL(meshes: THREE.Mesh[]): {
    isValid: boolean
    triangleCount: number
    issues: string[]
} {
    const issues: string[] = []
    let triangleCount = 0

    for (const mesh of meshes) {
        if (!mesh || !mesh.geometry) {
            issues.push('Found mesh without geometry')
            continue
        }

        const geometry = mesh.geometry as THREE.BufferGeometry
        const positions = geometry.getAttribute('position')

        if (!positions) {
            issues.push('Found geometry without position attribute')
            continue
        }

        const indices = geometry.getIndex()
        const faceCount = indices ? indices.count / 3 : positions.count / 3
        triangleCount += faceCount

        // Check for valid position data
        for (let i = 0; i < positions.count; i++) {
            const x = positions.getX(i)
            const y = positions.getY(i)
            const z = positions.getZ(i)

            if (!isFinite(x) || !isFinite(y) || !isFinite(z)) {
                issues.push('Found invalid vertex coordinates')
                break
            }
        }
    }

    if (triangleCount === 0) {
        issues.push('No triangles found')
    }

    return {
        isValid: issues.length === 0,
        triangleCount: Math.floor(triangleCount),
        issues
    }
}