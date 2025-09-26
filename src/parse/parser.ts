// src/parse/parser.ts
export type Vec3 = { x: number; y: number; z: number }
export type BaseShape = { id: string; at: Vec3 }
export type Cube = BaseShape & { kind: 'cube'; size: number }
export type Sphere = BaseShape & { kind: 'sphere'; radius: number }
export type Cylinder = BaseShape & { kind: 'cylinder'; radius: number; height: number }
export type Shape = Cube | Sphere | Cylinder

export type SceneSpec = { shapes: Shape[] }

const num = /-?\d+(?:\.\d+)?/

function parseVec3(src: string): Vec3 | null {
    // support: at x y z | at(x,y,z)
    const m1 = src.match(new RegExp(`at\\s*\\(\\s*(${num.source})\\s*,\\s*(${num.source})\\s*,\\s*(${num.source})\\s*\\)`))
    if (m1) return { x: parseFloat(m1[1]), y: parseFloat(m1[2]), z: parseFloat(m1[3]) }
    const m2 = src.match(new RegExp(`at\\s+(${num.source})\\s+(${num.source})\\s+(${num.source})`))
    if (m2) return { x: parseFloat(m2[1]), y: parseFloat(m2[2]), z: parseFloat(m2[3]) }
    return null
}

function uid(prefix = 'shp'): string {
    return `${prefix}_${Math.random().toString(36).slice(2, 9)}`
}

export function parsePrompt(prompt: string): SceneSpec {
    const shapes: Shape[] = []
    const text = prompt.toLowerCase().replace(/\n/g, ' ')
    // blocs séparés par virgule ou point-virgule
    const parts = text.split(/[,;]+/).map(s => s.trim()).filter(Boolean)

    for (const part of parts) {
        // CUBE — ex: "cube 20 at 0 0 0" | "cube size=20 at(0,0,0)"
        let m = part.match(new RegExp(`^cube(?:\\s+(${num.source}))?(?:.*?size\\s*=\\s*(${num.source}))?`))
        if (m) {
            const size = parseFloat(m[1] || m[2] || '10')
            const at = parseVec3(part) ?? { x: 0, y: 0, z: 0 }
            shapes.push({ id: uid('cube'), kind: 'cube', size, at })
            continue
        }

        // SPHERE — ex: "sphere 10 at 0 10 0" | "sphere r=10 at(0,10,0)"
        m = part.match(new RegExp(`^sph(?:ere)?(?:\\s+(${num.source}))?(?:.*?r(?:adius)?\\s*=\\s*(${num.source}))?`))
        if (m) {
            const radius = parseFloat(m[1] || m[2] || '5')
            const at = parseVec3(part) ?? { x: 0, y: 0, z: 0 }
            shapes.push({ id: uid('sphere'), kind: 'sphere', radius, at })
            continue
        }

        // CYLINDER — ex: "cylinder 5 20 at 10 0 0" | "cylinder r=5 h=20 at(10,0,0)"
        m = part.match(new RegExp(`^cyl(?:inder)?(?:\\s+(${num.source})\\s+(${num.source}))?`))
        if (m && m[1] && m[2]) {
            const radius = parseFloat(m[1])
            const height = parseFloat(m[2])
            const at = parseVec3(part) ?? { x: 0, y: 0, z: 0 }
            shapes.push({ id: uid('cyl'), kind: 'cylinder', radius, height, at })
            continue
        } else {
            const mr = part.match(new RegExp(`r(?:adius)?\\s*=\\s*(${num.source})`))
            const mh = part.match(new RegExp(`h(?:eight)?\\s*=\\s*(${num.source})`))
            if (mr || mh) {
                const radius = parseFloat(mr?.[1] || '5')
                const height = parseFloat(mh?.[1] || '20')
                const at = parseVec3(part) ?? { x: 0, y: 0, z: 0 }
                shapes.push({ id: uid('cyl'), kind: 'cylinder', radius, height, at })
                continue
            }
        }
    }

    return { shapes }
}

export function serializeScene(scene: SceneSpec): string {
    return JSON.stringify(scene, null, 2)
}

export function deserializeScene(json: string): SceneSpec {
    const data = JSON.parse(json)
    if (!Array.isArray(data.shapes)) return { shapes: [] }
    return { shapes: data.shapes as Shape[] }
}
