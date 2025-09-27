// src/cad/advancedShapes.ts
import * as THREE from 'three'

export interface ShapeParameters {
    [key: string]: number | string | boolean
}

export class AdvancedShapes {

    // Engrenage paramétrique avancé
    static createGear(params: {
        outerRadius?: number
        innerRadius?: number
        teeth?: number
        thickness?: number
        holeRadius?: number
        toothDepth?: number
        pressureAngle?: number
    }): THREE.Group {
        const {
            outerRadius = 15,
            innerRadius = 8,
            teeth = 12,
            thickness = 4,
            holeRadius = 3,
            toothDepth = 2,
            pressureAngle = 20
        } = params

        const gear = new THREE.Group()

        // Calcul du profil d'engrenage
        const pitchRadius = (outerRadius + innerRadius) / 2
        const baseRadius = pitchRadius * Math.cos(pressureAngle * Math.PI / 180)

        // Corps principal de l'engrenage
        const segments = Math.max(teeth * 4, 32)
        const gearShape = new THREE.Shape()

        // Génération du profil avec dents
        for (let i = 0; i <= segments; i++) {
            const angle = (i / segments) * Math.PI * 2
            const toothPhase = (angle * teeth) % (Math.PI * 2)

            let radius = pitchRadius

            // Forme de la dent (simplifiée)
            if (toothPhase < Math.PI / 2) {
                radius = pitchRadius + toothDepth * Math.sin(toothPhase * 2)
            } else if (toothPhase < Math.PI) {
                radius = pitchRadius + toothDepth * Math.sin(toothPhase * 2)
            } else {
                radius = pitchRadius
            }

            const x = Math.cos(angle) * radius
            const y = Math.sin(angle) * radius

            if (i === 0) {
                gearShape.moveTo(x, y)
            } else {
                gearShape.lineTo(x, y)
            }
        }

        gearShape.closePath()

        // Trou central
        if (innerRadius > 0) {
            const hole = new THREE.Path()
            hole.absarc(0, 0, innerRadius, 0, Math.PI * 2, true)
            gearShape.holes.push(hole)
        }

        // Extrusion
        const extrudeSettings = {
            depth: thickness,
            bevelEnabled: true,
            bevelThickness: 0.1,
            bevelSize: 0.1
        }

        const gearGeometry = new THREE.ExtrudeGeometry(gearShape, extrudeSettings)
        const gearMesh = new THREE.Mesh(
            gearGeometry,
            new THREE.MeshStandardMaterial({
                color: 0x888888,
                metalness: 0.8,
                roughness: 0.2
            })
        )

        gear.add(gearMesh)

        // Trou de montage central
        if (holeRadius > 0) {
            const holeGeometry = new THREE.CylinderGeometry(holeRadius, holeRadius, thickness + 0.2, 16)
            const holeMesh = new THREE.Mesh(
                holeGeometry,
                new THREE.MeshStandardMaterial({
                    color: 0x000000,
                    transparent: true,
                    opacity: 0.3
                })
            )
            gear.add(holeMesh)
        }

        return gear
    }

    // Ressort hélicoïdal
    static createSpring(params: {
        outerRadius?: number
        innerRadius?: number
        length?: number
        coils?: number
        wireThickness?: number
        pitch?: number
    }): THREE.Group {
        const {
            outerRadius = 8,
            innerRadius = 6,
            length = 50,
            coils = 10,
            wireThickness = 0.8,
            pitch = length / coils
        } = params

        const spring = new THREE.Group()
        const points = []
        const segments = coils * 32 // Points par spire

        // Génération de la courbe hélicoïdale
        for (let i = 0; i <= segments; i++) {
            const t = i / segments
            const angle = t * coils * Math.PI * 2
            const y = t * length

            // Variation du rayon pour effet de compression
            const radiusVariation = 1 + 0.1 * Math.sin(angle * 4)
            const currentRadius = (outerRadius + innerRadius) / 2 * radiusVariation

            const x = Math.cos(angle) * currentRadius
            const z = Math.sin(angle) * currentRadius

            points.push(new THREE.Vector3(x, y, z))
        }

        // Création du tube suivant la courbe
        const curve = new THREE.CatmullRomCurve3(points)
        const tubeGeometry = new THREE.TubeGeometry(
            curve,
            segments,
            wireThickness,
            8,
            false
        )

        const springMesh = new THREE.Mesh(
            tubeGeometry,
            new THREE.MeshStandardMaterial({
                color: 0x666666,
                metalness: 0.9,
                roughness: 0.1
            })
        )

        spring.add(springMesh)
        return spring
    }

    // Support en L avec nervures
    static createRibbledBracket(params: {
        width?: number
        height?: number
        thickness?: number
        armLength?: number
        ribCount?: number
        holeRadius?: number
        holeSpacing?: number
    }): THREE.Group {
        const {
            width = 40,
            height = 60,
            thickness = 8,
            armLength = 50,
            ribCount = 3,
            holeRadius = 3,
            holeSpacing = 15
        } = params

        const bracket = new THREE.Group()

        // Bras vertical
        const verticalGeometry = new THREE.BoxGeometry(thickness, height, width)
        const verticalMesh = new THREE.Mesh(
            verticalGeometry,
            new THREE.MeshStandardMaterial({ color: 0x404040 })
        )
        verticalMesh.position.set(thickness / 2, height / 2, 0)
        bracket.add(verticalMesh)

        // Bras horizontal
        const horizontalGeometry = new THREE.BoxGeometry(armLength, thickness, width)
        const horizontalMesh = new THREE.Mesh(
            horizontalGeometry,
            new THREE.MeshStandardMaterial({ color: 0x404040 })
        )
        horizontalMesh.position.set(armLength / 2, thickness / 2, 0)
        bracket.add(horizontalMesh)

        // Nervures de renforcement
        const ribThickness = 2
        const ribHeight = Math.min(height, armLength) * 0.7

        for (let i = 0; i < ribCount; i++) {
            const ribZ = (i - (ribCount - 1) / 2) * (width / ribCount)

            // Créer la forme triangulaire de la nervure
            const ribShape = new THREE.Shape()
            ribShape.moveTo(thickness, thickness)
            ribShape.lineTo(ribHeight * 0.7, thickness)
            ribShape.lineTo(thickness, ribHeight * 0.7)
            ribShape.closePath()

            const ribGeometry = new THREE.ExtrudeGeometry(ribShape, {
                depth: ribThickness,
                bevelEnabled: false
            })

            const ribMesh = new THREE.Mesh(
                ribGeometry,
                new THREE.MeshStandardMaterial({ color: 0x505050 })
            )

            ribMesh.position.set(0, 0, ribZ - ribThickness / 2)
            bracket.add(ribMesh)
        }

        // Trous de montage
        if (holeRadius > 0) {
            const holePositions = [
                // Trous horizontaux
                [armLength - holeSpacing, thickness / 2, -width / 4],
                [armLength - holeSpacing, thickness / 2, width / 4],
                [armLength - holeSpacing * 2, thickness / 2, 0],

                // Trous verticaux
                [thickness / 2, height - holeSpacing, -width / 4],
                [thickness / 2, height - holeSpacing, width / 4],
                [thickness / 2, height - holeSpacing * 2, 0]
            ]

            holePositions.forEach(([x, y, z]) => {
                const holeGeometry = new THREE.CylinderGeometry(holeRadius, holeRadius, width + 1, 12)
                const holeMesh = new THREE.Mesh(
                    holeGeometry,
                    new THREE.MeshStandardMaterial({
                        color: 0x000000,
                        transparent: true,
                        opacity: 0.4
                    })
                )

                holeMesh.position.set(x, y, z)
                holeMesh.rotation.x = Math.PI / 2
                bracket.add(holeMesh)
            })
        }

        return bracket
    }

    // Boîtier électronique avec grille de ventilation
    static createVentilatedEnclosure(params: {
        width?: number
        height?: number
        depth?: number
        wallThickness?: number
        lidHeight?: number
        ventHoleSize?: number
        ventHoleSpacing?: number
        standoffHeight?: number
        standoffRadius?: number
    }): THREE.Group {
        const {
            width = 100,
            height = 60,
            depth = 80,
            wallThickness = 3,
            lidHeight = 8,
            ventHoleSize = 3,
            ventHoleSpacing = 8,
            standoffHeight = 5,
            standoffRadius = 2.5
        } = params

        const enclosure = new THREE.Group()

        // Boîtier principal
        const mainBoxGeometry = new THREE.BoxGeometry(width, height, depth)
        const mainBoxMesh = new THREE.Mesh(
            mainBoxGeometry,
            new THREE.MeshStandardMaterial({ color: 0x2C3E50 })
        )
        mainBoxMesh.position.y = height / 2
        enclosure.add(mainBoxMesh)

        // Cavité intérieure (représentation visuelle)
        const innerBoxGeometry = new THREE.BoxGeometry(
            width - wallThickness * 2,
            height - wallThickness,
            depth - wallThickness * 2
        )
        const innerBoxMesh = new THREE.Mesh(
            innerBoxGeometry,
            new THREE.MeshStandardMaterial({
                color: 0x1A252F,
                transparent: true,
                opacity: 0.3
            })
        )
        innerBoxMesh.position.y = height / 2 + wallThickness / 2
        enclosure.add(innerBoxMesh)

        // Couvercle
        const lidGeometry = new THREE.BoxGeometry(width + 1, lidHeight, depth + 1)
        const lidMesh = new THREE.Mesh(
            lidGeometry,
            new THREE.MeshStandardMaterial({ color: 0x34495E })
        )
        lidMesh.position.y = height + lidHeight / 2
        enclosure.add(lidMesh)

        // Grille de ventilation sur le couvercle
        const ventRows = Math.floor(width / ventHoleSpacing) - 1
        const ventCols = Math.floor(depth / ventHoleSpacing) - 1

        for (let row = 0; row < ventRows; row++) {
            for (let col = 0; col < ventCols; col++) {
                if ((row + col) % 2 === 0) { // Motif en damier
                    const ventHoleGeometry = new THREE.CylinderGeometry(
                        ventHoleSize / 2,
                        ventHoleSize / 2,
                        lidHeight + 0.2,
                        8
                    )
                    const ventHoleMesh = new THREE.Mesh(
                        ventHoleGeometry,
                        new THREE.MeshStandardMaterial({
                            color: 0x000000,
                            transparent: true,
                            opacity: 0.6
                        })
                    )

                    const x = -width / 2 + (row + 1) * ventHoleSpacing
                    const z = -depth / 2 + (col + 1) * ventHoleSpacing

                    ventHoleMesh.position.set(x, height + lidHeight / 2, z)
                    enclosure.add(ventHoleMesh)
                }
            }
        }

        // Supports de montage PCB
        const standoffPositions = [
            [-width / 3, wallThickness + standoffHeight / 2, -depth / 3],
            [width / 3, wallThickness + standoffHeight / 2, -depth / 3],
            [-width / 3, wallThickness + standoffHeight / 2, depth / 3],
            [width / 3, wallThickness + standoffHeight / 2, depth / 3]
        ]

        standoffPositions.forEach(([x, y, z]) => {
            const standoffGeometry = new THREE.CylinderGeometry(
                standoffRadius,
                standoffRadius,
                standoffHeight,
                12
            )
            const standoffMesh = new THREE.Mesh(
                standoffGeometry,
                new THREE.MeshStandardMaterial({ color: 0x555555 })
            )
            standoffMesh.position.set(x, y, z)
            enclosure.add(standoffMesh)

            // Trou de vis dans le support
            const screwHoleGeometry = new THREE.CylinderGeometry(
                1.5,
                1.5,
                standoffHeight + 0.1,
                8
            )
            const screwHoleMesh = new THREE.Mesh(
                screwHoleGeometry,
                new THREE.MeshStandardMaterial({
                    color: 0x000000,
                    transparent: true,
                    opacity: 0.5
                })
            )
            screwHoleMesh.position.set(x, y, z)
            enclosure.add(screwHoleMesh)
        })

        return enclosure
    }

    // Connecteur fileté
    static createThreadedConnector(params: {
        bodyLength?: number
        bodyRadius?: number
        threadPitch?: number
        threadDepth?: number
        flangeRadius?: number
        flangeThickness?: number
        holeRadius?: number
        threadLength?: number
    }): THREE.Group {
        const {
            bodyLength = 40,
            bodyRadius = 8,
            threadPitch = 1.5,
            threadDepth = 0.5,
            flangeRadius = 15,
            flangeThickness = 5,
            holeRadius = 5,
            threadLength = 20
        } = params

        const connector = new THREE.Group()

        // Corps principal
        const bodyGeometry = new THREE.CylinderGeometry(
            bodyRadius,
            bodyRadius,
            bodyLength,
            32
        )
        const bodyMesh = new THREE.Mesh(
            bodyGeometry,
            new THREE.MeshStandardMaterial({
                color: 0x316AC5,
                metalness: 0.7,
                roughness: 0.3
            })
        )
        connector.add(bodyMesh)

        // Simulation du filetage avec anneaux
        const threadTurns = threadLength / threadPitch
        for (let i = 0; i < threadTurns * 4; i++) {
            const threadRingGeometry = new THREE.TorusGeometry(
                bodyRadius + threadDepth,
                threadDepth * 0.3,
                8,
                16
            )
            const threadRingMesh = new THREE.Mesh(
                threadRingGeometry,
                new THREE.MeshStandardMaterial({
                    color: 0x4A7BC8,
                    metalness: 0.8,
                    roughness: 0.2
                })
            )

            const y = -threadLength / 2 + (i / (threadTurns * 4)) * threadLength
            threadRingMesh.position.y = y
            threadRingMesh.rotation.x = Math.PI / 2
            connector.add(threadRingMesh)
        }

        // Brides aux extrémités
        for (let end = 0; end < 2; end++) {
            const flangeGeometry = new THREE.CylinderGeometry(
                flangeRadius,
                flangeRadius,
                flangeThickness,
                32
            )
            const flangeMesh = new THREE.Mesh(
                flangeGeometry,
                new THREE.MeshStandardMaterial({ color: 0x404040 })
            )
            flangeMesh.position.y = (end - 0.5) * (bodyLength + flangeThickness)
            connector.add(flangeMesh)

            // Trous de boulonnage
            const boltHoleCount = 6
            const boltCircleRadius = flangeRadius - 3

            for (let i = 0; i < boltHoleCount; i++) {
                const angle = (i / boltHoleCount) * Math.PI * 2
                const x = Math.cos(angle) * boltCircleRadius
                const z = Math.sin(angle) * boltCircleRadius

                const boltHoleGeometry = new THREE.CylinderGeometry(
                    2,
                    2,
                    flangeThickness + 0.1,
                    8
                )
                const boltHoleMesh = new THREE.Mesh(
                    boltHoleGeometry,
                    new THREE.MeshStandardMaterial({
                        color: 0x000000,
                        transparent: true,
                        opacity: 0.5
                    })
                )
                boltHoleMesh.position.set(
                    x,
                    (end - 0.5) * (bodyLength + flangeThickness),
                    z
                )
                connector.add(boltHoleMesh)
            }
        }

        // Trou central
        if (holeRadius > 0) {
            const centralHoleGeometry = new THREE.CylinderGeometry(
                holeRadius,
                holeRadius,
                bodyLength + flangeThickness * 2 + 0.2,
                16
            )
            const centralHoleMesh = new THREE.Mesh(
                centralHoleGeometry,
                new THREE.MeshStandardMaterial({
                    color: 0x000000,
                    transparent: true,
                    opacity: 0.2
                })
            )
            connector.add(centralHoleMesh)
        }

        return connector
    }

    // Support d'outils avec crochets
    static createToolHolder(params: {
        baseWidth?: number
        baseDepth?: number
        baseHeight?: number
        hookCount?: number
        hookRadius?: number
        hookHeight?: number
        mountingHoles?: boolean
    }): THREE.Group {
        const {
            baseWidth = 200,
            baseDepth = 40,
            baseHeight = 20,
            hookCount = 6,
            hookRadius = 8,
            hookHeight = 30,
            mountingHoles = true
        } = params

        const toolHolder = new THREE.Group()

        // Base
        const baseGeometry = new THREE.BoxGeometry(baseWidth, baseHeight, baseDepth)
        const baseMesh = new THREE.Mesh(
            baseGeometry,
            new THREE.MeshStandardMaterial({ color: 0x8B4513 })
        )
        baseMesh.position.y = baseHeight / 2
        toolHolder.add(baseMesh)

        // Crochets
        const hookSpacing = baseWidth / (hookCount + 1)

        for (let i = 0; i < hookCount; i++) {
            const hookX = -baseWidth / 2 + (i + 1) * hookSpacing

            // Tige verticale du crochet
            const hookStemGeometry = new THREE.CylinderGeometry(
                hookRadius * 0.3,
                hookRadius * 0.3,
                hookHeight,
                8
            )
            const hookStemMesh = new THREE.Mesh(
                hookStemGeometry,
                new THREE.MeshStandardMaterial({ color: 0x654321 })
            )
            hookStemMesh.position.set(hookX, baseHeight + hookHeight / 2, 0)
            toolHolder.add(hookStemMesh)

            // Partie courbée du crochet
            const hookCurve = new THREE.TorusGeometry(
                hookRadius,
                hookRadius * 0.2,
                8,
                16,
                Math.PI
            )
            const hookCurveMesh = new THREE.Mesh(
                hookCurve,
                new THREE.MeshStandardMaterial({ color: 0x654321 })
            )
            hookCurveMesh.position.set(
                hookX,
                baseHeight + hookHeight - hookRadius,
                hookRadius
            )
            hookCurveMesh.rotation.z = Math.PI
            toolHolder.add(hookCurveMesh)
        }

        // Trous de montage
        if (mountingHoles) {
            const holePositions = [
                [-baseWidth / 3, baseHeight / 2, 0],
                [baseWidth / 3, baseHeight / 2, 0]
            ]

            holePositions.forEach(([x, y, z]) => {
                const holeGeometry = new THREE.CylinderGeometry(3, 3, baseHeight + 0.1, 8)
                const holeMesh = new THREE.Mesh(
                    holeGeometry,
                    new THREE.MeshStandardMaterial({
                        color: 0x000000,
                        transparent: true,
                        opacity: 0.4
                    })
                )
                holeMesh.position.set(x, y, z)
                toolHolder.add(holeMesh)
            })
        }

        return toolHolder
    }
}

// Extensions pour intégrer les formes dans le moteur CAD
export function extendCADEngineWithAdvancedShapes(cadEngine: any) {
    cadEngine.createGear = AdvancedShapes.createGear
    cadEngine.createSpring = AdvancedShapes.createSpring
    cadEngine.createRibbledBracket = AdvancedShapes.createRibbledBracket
    cadEngine.createVentilatedEnclosure = AdvancedShapes.createVentilatedEnclosure
    cadEngine.createThreadedConnector = AdvancedShapes.createThreadedConnector
    cadEngine.createToolHolder = AdvancedShapes.createToolHolder
}