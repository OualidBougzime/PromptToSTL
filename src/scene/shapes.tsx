import * as React from 'react'
import { Cylinder, Sphere, Cube as CubeT, Shape } from '../parse/parser'


export function Cube({ size }: { size: number }) {
    return (
        <mesh>
            <boxGeometry args={[size, size, size]} />
            <meshStandardMaterial />
        </mesh>
    )
}


export function SphereShape({ radius }: { radius: number }) {
    return (
        <mesh>
            <sphereGeometry args={[radius, 32, 32]} />
            <meshStandardMaterial />
        </mesh>
    )
}


export function CylinderShape({ radius, height }: { radius: number; height: number }) {
    return (
        <mesh>
            <cylinderGeometry args={[radius, radius, height, 48]} />
            <meshStandardMaterial />
        </mesh>
    )
}


export function ShapeMesh({ shape }: { shape: Shape }) {
    return (
        <group position={[shape.at.x, shape.at.y, shape.at.z]}>
            {shape.kind === 'cube' && <Cube size={(shape as CubeT).size} />}
            {shape.kind === 'sphere' && <SphereShape radius={(shape as Sphere).radius} />}
            {shape.kind === 'cylinder' && (
                <CylinderShape radius={(shape as Cylinder).radius} height={(shape as Cylinder).height} />
            )}
        </group>
    )
}