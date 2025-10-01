import * as React from 'react'
import * as THREE from 'three'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, ContactShadows } from '@react-three/drei'

interface CADCanvasProps {
    meshes: THREE.Mesh[]
}

function MeshRenderer({ meshes }: { meshes: THREE.Mesh[] }) {
    const groupRef = React.useRef<THREE.Group>(null)

    React.useEffect(() => {
        if (!groupRef.current) return

        console.log('MeshRenderer: Processing', meshes.length, 'meshes')

        // Clear previous meshes
        while (groupRef.current.children.length > 0) {
            groupRef.current.remove(groupRef.current.children[0])
        }

        // Add new meshes
        meshes.forEach((mesh, index) => {
            if (mesh && mesh.geometry) {
                try {
                    const clonedMesh = mesh.clone()

                    // Ensure material exists and is visible
                    if (!clonedMesh.material || Array.isArray(clonedMesh.material)) {
                        clonedMesh.material = new THREE.MeshStandardMaterial({
                            color: 0x666666,
                            metalness: 0.2,
                            roughness: 0.8
                        })
                    }

                    groupRef.current?.add(clonedMesh)
                    console.log(`Added mesh ${index}:`, clonedMesh)
                } catch (error) {
                    console.error(`Error processing mesh ${index}:`, error)
                }
            } else {
                console.warn(`Skipping invalid mesh ${index}:`, mesh)
            }
        })

        // Auto-center and scale the model
        if (groupRef.current.children.length > 0) {
            try {
                const box = new THREE.Box3()
                groupRef.current.traverse((child) => {
                    if (child instanceof THREE.Mesh && child.geometry) {
                        child.geometry.computeBoundingBox()
                        if (child.geometry.boundingBox) {
                            box.expandByObject(child)
                        }
                    }
                })

                if (!box.isEmpty()) {
                    const center = box.getCenter(new THREE.Vector3())
                    const size = box.getSize(new THREE.Vector3())

                    // Center the model
                    groupRef.current.position.sub(center)

                    // Scale if too large
                    const maxDimension = Math.max(size.x, size.y, size.z)
                    if (maxDimension > 100) {
                        const scale = 100 / maxDimension
                        groupRef.current.scale.setScalar(scale)
                    }

                    console.log('Model centered and scaled:', { center, size, maxDimension })
                }
            } catch (error) {
                console.error('Error computing bounds:', error)
            }
        }

    }, [meshes])

    return <group ref={groupRef} />
}

function SceneLighting() {
    return (
        <>
            <ambientLight intensity={0.4} />
            <directionalLight
                position={[50, 50, 25]}
                intensity={1}
                castShadow
                shadow-mapSize={[2048, 2048]}
                shadow-camera-far={200}
                shadow-camera-left={-50}
                shadow-camera-right={50}
                shadow-camera-top={50}
                shadow-camera-bottom={-50}
            />
            <directionalLight
                position={[-25, 25, 25]}
                intensity={0.5}
                color="#4080ff"
            />
        </>
    )
}

function SceneEnvironment() {
    return (
        <>
            <Grid
                infiniteGrid
                size={100}
                cellSize={5}
                cellThickness={0.5}
                sectionSize={25}
                sectionThickness={1}
                fadeDistance={150}
                fadeStrength={1}
                cellColor="#999"
                sectionColor="#555"
            />
            <ContactShadows
                opacity={0.3}
                scale={100}
                blur={2}
                far={50}
                resolution={256}
                color="#000000"
            />
            {/* <Environment preset="studio" /> */}
        </>
    )
}

function ViewportInfo({ meshCount }: { meshCount: number }) {
    return (
        <div style={{
            position: 'absolute',
            top: '10px',
            left: '10px',
            backgroundColor: 'rgba(0,0,0,0.8)',
            color: 'white',
            padding: '8px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontFamily: 'monospace',
            pointerEvents: 'none',
            zIndex: 10
        }}>
            <div>Meshes: {meshCount}</div>
            <div>Mouse: Orbit | Wheel: Zoom</div>
        </div>
    )
}

export function CADCanvas({ meshes }: CADCanvasProps) {
    const [cameraPosition, setCameraPosition] = React.useState<[number, number, number]>([60, 40, 60])

    // Auto-adjust camera based on model bounds
    React.useEffect(() => {
        if (meshes.length === 0) {
            setCameraPosition([60, 40, 60])
            return
        }

        try {
            const box = new THREE.Box3()
            meshes.forEach(mesh => {
                if (mesh && mesh.geometry) {
                    mesh.geometry.computeBoundingBox()
                    if (mesh.geometry.boundingBox) {
                        // Transform bounding box to world coordinates
                        const worldBox = mesh.geometry.boundingBox.clone()
                        worldBox.applyMatrix4(mesh.matrixWorld)

                        // Expand main box using min/max points
                        box.expandByPoint(worldBox.min)
                        box.expandByPoint(worldBox.max)
                    }
                }
            })

            if (!box.isEmpty()) {
                const size = box.getSize(new THREE.Vector3())
                const maxDim = Math.max(size.x, size.y, size.z)
                const distance = Math.max(maxDim * 2, 60) // Minimum distance of 60
                setCameraPosition([distance, distance * 0.7, distance])
                console.log('Camera adjusted for model size:', { size, distance })
            }
        } catch (error) {
            console.error('Error adjusting camera:', error)
            // Fallback to default position
            setCameraPosition([60, 40, 60])
        }
    }, [meshes])

    return (
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
            <ViewportInfo meshCount={meshes.length} />

            <Canvas
                camera={{
                    position: cameraPosition,
                    fov: 50,
                    near: 0.1,
                    far: 10000
                }}
                shadows
                gl={{
                    antialias: true,
                    alpha: false,
                    powerPreference: 'high-performance'
                }}
                onCreated={({ gl }) => {
                    console.log('Canvas created successfully')
                }}
            >
                <SceneLighting />
                <SceneEnvironment />

                <MeshRenderer meshes={meshes} />

                <OrbitControls
                    makeDefault
                    enablePan={true}
                    enableZoom={true}
                    enableRotate={true}
                    minDistance={1}
                    maxDistance={1000}
                    panSpeed={1}
                    rotateSpeed={1}
                    zoomSpeed={1}
                />
            </Canvas>

            {meshes.length === 0 && (
                <div style={{
                    position: 'absolute',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    textAlign: 'center',
                    color: '#666',
                    pointerEvents: 'none'
                }}>
                    <div style={{ fontSize: '48px', marginBottom: '16px' }}>🏗️</div>
                    <div style={{ fontSize: '16px', fontWeight: 'bold' }}>No Model Generated</div>
                    <div style={{ fontSize: '14px', marginTop: '8px' }}>
                        Enter a description and click "Generate 3D Model"
                    </div>
                </div>
            )}
        </div>
    )
}