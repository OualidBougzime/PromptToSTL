import * as React from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, StatsGl } from '@react-three/drei'
import { Shape } from '../parse/parser'
import { ShapeMesh } from './shapes'


export function SceneCanvas({ shapes, onReadyMeshes }: { shapes: Shape[]; onReadyMeshes?: (meshes: THREE.Mesh[]) => void }) {
    const groupRef = React.useRef<THREE.Group>(null)


    React.useEffect(() => {
        if (!groupRef.current || !onReadyMeshes) return
        const meshes: THREE.Mesh[] = []
        groupRef.current.traverse((obj) => {
            // @ts-ignore
            if (obj.isMesh) meshes.push(obj as THREE.Mesh)
        })
        onReadyMeshes(meshes)
    }, [shapes, onReadyMeshes])


    return (
        <Canvas camera={{ position: [60, 40, 60], fov: 50 }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[40, 80, 40]} intensity={0.8} />
            <group ref={groupRef}>
                {shapes.map((s) => (
                    <ShapeMesh key={s.id} shape={s} />
                ))}
            </group>
            <Grid infiniteGrid args={[100, 100]} />
            <OrbitControls makeDefault />
            <StatsGl />
        </Canvas>
    )
}