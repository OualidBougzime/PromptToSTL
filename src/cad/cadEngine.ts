import * as THREE from 'three'
import { CSG } from 'three-csg-ts'

export class CADEngine {
    private initialized = false

    async initialize(): Promise<void> {
        if (this.initialized) return
        this.initialized = true
        console.log('CAD Engine initialized')
    }

    async executeCADCode(code: string): Promise<THREE.Mesh[]> {
        if (!this.initialized) {
            await this.initialize()
        }

        console.log('Executing CAD code:', code)

        try {
            // Pre-validate and clean the code
            const cleanCode = this.sanitizeCode(code)
            console.log('Cleaned code:', cleanCode)

            // Create a safe execution context with helper functions
            const executionContext = {
                THREE,
                CSG,
                Math,
                console: {
                    log: (...args: any[]) => console.log('[CAD Code]', ...args),
                    warn: (...args: any[]) => console.warn('[CAD Code]', ...args),
                    error: (...args: any[]) => console.error('[CAD Code]', ...args)
                },
                // Helper functions for complex shapes
                createHuman: this.createHuman.bind(this),
                createTree: this.createTree.bind(this),
                createBuilding: this.createBuilding.bind(this),
                createCar: this.createCar.bind(this),
                randomInRange: (min: number, max: number) => Math.random() * (max - min) + min
            }

            // Wrap the code in a function if it's not already
            let wrappedCode = cleanCode
            if (!cleanCode.includes('function generateModel')) {
                wrappedCode = `
          function generateModel() {
            const meshes = []
            ${cleanCode}
            return meshes
          }
        `
            }

            // Create the execution function with error handling
            const functionBody = `
        const { THREE, CSG, Math, console, createHuman, createTree, createBuilding, createCar, randomInRange } = this;
        try {
          ${wrappedCode}
          const result = generateModel();
          if (!Array.isArray(result)) {
            console.warn('Code did not return an array');
            return [];
          }
          return result;
        } catch (error) {
          console.error('Code execution error:', error);
          return [];
        }
      `

            const executeFunction = new Function(functionBody)
            const result = executeFunction.call(executionContext)

            // Validate and process result
            if (!Array.isArray(result)) {
                console.warn('CAD code did not return an array, creating fallback')
                return [this.createFallbackShape()]
            }

            // Filter and validate meshes
            const validMeshes = result.filter(item => {
                if (!item || typeof item !== 'object') {
                    console.warn('Invalid item in result array:', item)
                    return false
                }
                if (item.isMesh || (item.geometry && item.material)) return true
                return false
            })

            if (validMeshes.length === 0) {
                console.warn('No valid meshes generated, creating fallback')
                return [this.createFallbackShape()]
            }

            // Ensure all items are proper Three.js meshes
            const finalMeshes = validMeshes.map(mesh => {
                if (mesh.isMesh) return mesh

                // Convert to proper mesh if needed
                const material = mesh.material || new THREE.MeshStandardMaterial({ color: 0x888888 })
                return new THREE.Mesh(mesh.geometry, material)
            })

            console.log(`Successfully generated ${finalMeshes.length} meshes`)
            return finalMeshes

        } catch (error) {
            console.error('CAD code execution error:', error)

            // Return a fallback shape instead of crashing
            return [this.createFallbackShape('cube')]
        }
    }

    // Helper function to create a basic human figure
    private createHuman(): THREE.Group {
        const human = new THREE.Group()

        // Head
        const headGeo = new THREE.SphereGeometry(2, 16, 16)
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffdbac })
        const head = new THREE.Mesh(headGeo, headMat)
        head.position.y = 16
        human.add(head)

        // Body
        const bodyGeo = new THREE.CylinderGeometry(2.5, 3, 8, 8)
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0x4169e1 })
        const body = new THREE.Mesh(bodyGeo, bodyMat)
        body.position.y = 8
        human.add(body)

        // Arms
        for (let i = 0; i < 2; i++) {
            const armGeo = new THREE.CylinderGeometry(0.8, 0.8, 6, 8)
            const armMat = new THREE.MeshStandardMaterial({ color: 0xffdbac })
            const arm = new THREE.Mesh(armGeo, armMat)
            arm.position.set((i * 2 - 1) * 4, 10, 0)
            arm.rotation.z = (i * 2 - 1) * Math.PI / 8
            human.add(arm)
        }

        // Legs  
        for (let i = 0; i < 2; i++) {
            const legGeo = new THREE.CylinderGeometry(1, 1, 8, 8)
            const legMat = new THREE.MeshStandardMaterial({ color: 0x2f4f4f })
            const leg = new THREE.Mesh(legGeo, legMat)
            leg.position.set((i * 2 - 1) * 1.5, 0, 0)
            human.add(leg)
        }

        return human
    }

    // Helper function to create a basic tree
    private createTree(): THREE.Group {
        const tree = new THREE.Group()

        // Trunk
        const trunkGeo = new THREE.CylinderGeometry(1.5, 2, 10, 8)
        const trunkMat = new THREE.MeshStandardMaterial({ color: 0x8b4513 })
        const trunk = new THREE.Mesh(trunkGeo, trunkMat)
        trunk.position.y = 5
        tree.add(trunk)

        // Branches
        for (let i = 0; i < 6; i++) {
            const angle = (i / 6) * Math.PI * 2
            const branchGeo = new THREE.CylinderGeometry(0.3, 0.6, 4, 6)
            const branchMat = new THREE.MeshStandardMaterial({ color: 0x654321 })
            const branch = new THREE.Mesh(branchGeo, branchMat)
            branch.position.set(
                Math.cos(angle) * 2,
                8 + Math.sin(i) * 1,
                Math.sin(angle) * 2
            )
            branch.rotation.set(Math.PI / 4, angle, 0)
            tree.add(branch)
        }

        // Leaves
        for (let i = 0; i < 15; i++) {
            const leafGeo = new THREE.SphereGeometry(Math.random() * 1.5 + 0.5, 6, 6)
            const leafMat = new THREE.MeshStandardMaterial({ color: 0x228b22 })
            const leaf = new THREE.Mesh(leafGeo, leafMat)
            leaf.position.set(
                (Math.random() - 0.5) * 8,
                10 + Math.random() * 6,
                (Math.random() - 0.5) * 8
            )
            tree.add(leaf)
        }

        return tree
    }

    // Helper function to create a basic building
    private createBuilding(): THREE.Group {
        const building = new THREE.Group()

        // Main structure
        const baseGeo = new THREE.BoxGeometry(15, 25, 12)
        const baseMat = new THREE.MeshStandardMaterial({ color: 0x708090 })
        const base = new THREE.Mesh(baseGeo, baseMat)
        base.position.y = 12.5
        building.add(base)

        // Windows
        for (let floor = 0; floor < 4; floor++) {
            for (let win = 0; win < 3; win++) {
                const windowGeo = new THREE.BoxGeometry(2, 2.5, 0.2)
                const windowMat = new THREE.MeshStandardMaterial({ color: 0x87ceeb })
                const window = new THREE.Mesh(windowGeo, windowMat)
                window.position.set(
                    (win - 1) * 4,
                    floor * 5 + 3,
                    6.1
                )
                building.add(window)
            }
        }

        // Roof
        const roofGeo = new THREE.ConeGeometry(10, 8, 4)
        const roofMat = new THREE.MeshStandardMaterial({ color: 0x8b0000 })
        const roof = new THREE.Mesh(roofGeo, roofMat)
        roof.position.y = 29
        roof.rotation.y = Math.PI / 4
        building.add(roof)

        return building
    }

    // Helper function to create a basic car
    private createCar(): THREE.Group {
        const car = new THREE.Group()

        // Body
        const bodyGeo = new THREE.BoxGeometry(8, 2, 3)
        const bodyMat = new THREE.MeshStandardMaterial({ color: 0xff4500 })
        const body = new THREE.Mesh(bodyGeo, bodyMat)
        body.position.y = 1.5
        car.add(body)

        // Cabin
        const cabinGeo = new THREE.BoxGeometry(5, 2, 2.8)
        const cabinMat = new THREE.MeshStandardMaterial({ color: 0x4169e1 })
        const cabin = new THREE.Mesh(cabinGeo, cabinMat)
        cabin.position.y = 3
        car.add(cabin)

        // Wheels
        for (let i = 0; i < 4; i++) {
            const wheelGeo = new THREE.CylinderGeometry(1, 1, 0.5, 8)
            const wheelMat = new THREE.MeshStandardMaterial({ color: 0x2f2f2f })
            const wheel = new THREE.Mesh(wheelGeo, wheelMat)
            const x = (i % 2) * 6 - 3
            const z = Math.floor(i / 2) * 3 - 1.5
            wheel.position.set(x, 0.5, z)
            wheel.rotation.z = Math.PI / 2
            car.add(wheel)
        }

        return car
    }

    private sanitizeCode(code: string): string {
        // Remove problematic patterns
        let clean = code

        // Remove ALL import statements
        clean = clean.replace(/import\s+.*?from\s+['"][^'"]*['"];?\s*/g, '')
        clean = clean.replace(/import\s+\{[^}]*\}\s+from\s+['"][^'"]*['"];?\s*/g, '')
        clean = clean.replace(/import\s+\*\s+as\s+\w+\s+from\s+['"][^'"]*['"];?\s*/g, '')

        // Remove duplicate variable declarations
        clean = clean.replace(/const meshes = \[.*?\];?\s*/g, '')

        // Remove duplicate returns and broken CSG operations
        clean = clean.replace(/return meshes;?\s*return meshes;?/g, 'return meshes')
        clean = clean.replace(/const tree = CSG\.fromMesh.*$/gm, '') // Remove broken CSG operations
        clean = clean.replace(/return tree\s*$/gm, '') // Remove return tree

        // Fix common variable scoping issues - add meshes.push for meshes created in code
        // Find meshes created but not pushed
        const meshCreationPattern = /const (\w+) = new THREE\.Mesh\([^)]+\)/g
        let match
        const meshNames: string[] = []

        while ((match = meshCreationPattern.exec(clean)) !== null) {
            const meshName = match[1]
            if (!meshNames.includes(meshName) && meshName !== 'meshes') {
                meshNames.push(meshName)
            }
        }

        // Add meshes.push() for any mesh that doesn't have it
        meshNames.forEach(meshName => {
            if (!clean.includes(`meshes.push(${meshName})`)) {
                // Find the mesh creation and add push after position/rotation if present
                const meshDefPattern = new RegExp(`(const ${meshName} = new THREE\\.Mesh\\([^)]+\\)[^\\n]*(?:\\n[^\\n]*(?:position|rotation|scale)\\.[^\\n]*)*)`, 'g')
                clean = clean.replace(meshDefPattern, `$1\nmeshes.push(${meshName})`)
            }
        })

        // Fix CSG operations that reference undefined variables
        clean = clean.replace(/CSG\.fromMesh\((\w+)\)\.union\(CSG\.fromMesh\((\w+)\)\)\.subtract\(CSG\.fromMesh\((\w+)\)\)/g,
            '/* Complex CSG operation removed - variables may be undefined */')

        // Fix loops that don't push meshes
        clean = clean.replace(/for\s*\([^)]+\)\s*\{([^}]*const\s+(\w+)\s*=\s*new\s+THREE\.Mesh[^}]*)\}/g,
            (match, loopBody, meshVar) => {
                if (!loopBody.includes('meshes.push')) {
                    return match.replace(loopBody, loopBody + `\n  meshes.push(${meshVar})`)
                }
                return match
            })

        // Remove function wrapper if present (we'll add our own)
        clean = clean.replace(/function generateModel\(\)\s*\{/, '')
        clean = clean.replace(/function\s+\w+\(\)\s*\{[^}]*\}?\s*/g, '') // Remove extra functions
        clean = clean.replace(/\}\s*$/, '')

        // Remove problematic CSG method calls that don't exist
        clean = clean.replace(/CSG\.fromGeometry\(/g, 'CSG.fromMesh(new THREE.Mesh(')
        clean = clean.replace(/\.translate\(/g, '.position.set(') // Fix non-existent methods

        return clean.trim()
    }

    // Helper method to create basic shapes for fallback
    createFallbackShape(type: 'cube' | 'sphere' | 'cylinder' = 'cube'): THREE.Mesh {
        let geometry: THREE.BufferGeometry

        switch (type) {
            case 'sphere':
                geometry = new THREE.SphereGeometry(10, 32, 32)
                break
            case 'cylinder':
                geometry = new THREE.CylinderGeometry(5, 5, 20, 32)
                break
            default:
                geometry = new THREE.BoxGeometry(20, 20, 20)
        }

        const material = new THREE.MeshStandardMaterial({
            color: 0xff6b6b, // Red color to indicate fallback
            transparent: true,
            opacity: 0.8
        })

        const mesh = new THREE.Mesh(geometry, material)
        mesh.position.set(0, 10, 0)

        return mesh
    }

    // Method to validate and clean generated meshes
    validateMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        return meshes.filter(mesh => {
            if (!mesh || !mesh.geometry) {
                console.warn('Invalid mesh found, skipping')
                return false
            }

            // Check if geometry has vertices
            const position = mesh.geometry.getAttribute('position')
            if (!position || position.count === 0) {
                console.warn('Mesh with empty geometry found, skipping')
                return false
            }

            return true
        })
    }

    // Method to optimize meshes for better performance
    optimizeMeshes(meshes: THREE.Mesh[]): THREE.Mesh[] {
        return meshes.map(mesh => {
            try {
                // Compute bounding box and center if needed
                if (!mesh.geometry.boundingBox) {
                    mesh.geometry.computeBoundingBox()
                }

                // Compute vertex normals if not present
                if (!mesh.geometry.getAttribute('normal')) {
                    mesh.geometry.computeVertexNormals()
                }

                // Ensure material exists
                if (!mesh.material) {
                    mesh.material = new THREE.MeshStandardMaterial({ color: 0x888888 })
                }

                return mesh
            } catch (error) {
                console.warn('Error optimizing mesh:', error)
                return mesh
            }
        })
    }
}