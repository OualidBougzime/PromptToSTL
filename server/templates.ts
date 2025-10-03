// server/templates.ts
export interface Template {
    name: string
    description: string
    requiredParams: string[]
    generate: (params: Record<string, number>) => string
}

export const TEMPLATES: Record<string, Template> = {
    ellipsoid_implant: {
        name: 'Ellipsoidal Implant',
        description: 'Implant with ellipsoidal shape, cavity, membrane, and tab',
        requiredParams: ['length', 'width', 'height', 'wallThickness'],
        generate: (p) => `
const length = ${p.length || 30}
const width = ${p.width || 15}
const height = ${p.height || 10}
const wallThickness = ${p.wallThickness || 2}
const membraneThickness = ${p.membraneThickness || 0.3}
const tabLength = ${p.tabLength || 5}
const tabWidth = ${p.tabWidth || 3}

function generateModel() {
  const meshes = []
  
  const outerGeo = new THREE.SphereGeometry(1, 64, 32)
  const outerMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const outer = new THREE.Mesh(outerGeo, outerMat)
  outer.scale.set(length/2, width/2, height/2)
  meshes.push(outer)
  
  const innerGeo = new THREE.SphereGeometry(1, 32, 32)
  const innerMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const inner = new THREE.Mesh(innerGeo, innerMat)
  inner.scale.set((length-wallThickness*2)/2, (width-wallThickness*2)/2, (height-wallThickness*2)/2)
  meshes.push(inner)
  
  const membraneGeo = new THREE.SphereGeometry(1, 32, 16, 0, Math.PI*2, 0, Math.PI/3)
  const membraneMat = new THREE.MeshStandardMaterial({ color: 0xFFAAAA })
  const membrane = new THREE.Mesh(membraneGeo, membraneMat)
  membrane.scale.set((length-wallThickness*2)/2, membraneThickness, (height-wallThickness*2)/2)
  membrane.position.y = width/2 - wallThickness
  meshes.push(membrane)
  
  const tabGeo = new THREE.BoxGeometry(tabLength, tabWidth, 2)
  const tabMat = new THREE.MeshStandardMaterial({ color: 0xCCCCCC })
  const tab = new THREE.Mesh(tabGeo, tabMat)
  tab.position.set(length/2 + tabLength/2, 0, 0)
  meshes.push(tab)
  
  const holeGeo = new THREE.CylinderGeometry(0.5, 0.5, 3, 16)
  const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
  const hole1 = new THREE.Mesh(holeGeo, holeMat)
  hole1.position.set(length/2 + tabLength/2, tabWidth/3, 0)
  hole1.rotation.x = Math.PI/2
  meshes.push(hole1)
  const hole2 = new THREE.Mesh(holeGeo, holeMat)
  hole2.position.set(length/2 + tabLength/2, -tabWidth/3, 0)
  hole2.rotation.x = Math.PI/2
  meshes.push(hole2)
  
  return meshes
}
`.trim()
    },

    hemispherical_capsule: {
        name: 'Hemispherical Capsule',
        description: 'Cylindrical capsule with hemispherical caps and channels',
        requiredParams: ['length', 'diameter', 'wallThickness'],
        generate: (p) => `
const bodyLength = ${p.length || 18}
const outerRadius = ${p.diameter ? p.diameter / 2 : 4}
const wallThickness = ${p.wallThickness || 1}
const innerRadius = outerRadius - wallThickness
const channelCount = ${p.channelCount || 12}
const channelRadius = 0.25

function generateModel() {
  const meshes = []
  
  const bodyGeo = new THREE.CylinderGeometry(outerRadius, outerRadius, bodyLength, 64)
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const body = new THREE.Mesh(bodyGeo, bodyMat)
  body.position.y = 0
  meshes.push(body)
  
  const capGeo = new THREE.SphereGeometry(outerRadius, 32, 16, 0, Math.PI*2, 0, Math.PI/2)
  const capMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const topCap = new THREE.Mesh(capGeo, capMat)
  topCap.position.y = bodyLength/2
  meshes.push(topCap)
  const bottomCap = new THREE.Mesh(capGeo, capMat)
  bottomCap.rotation.z = Math.PI
  bottomCap.position.y = -bodyLength/2
  meshes.push(bottomCap)
  
  const cavityGeo = new THREE.CylinderGeometry(innerRadius, innerRadius, bodyLength-2, 32)
  const cavityMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const cavity = new THREE.Mesh(cavityGeo, cavityMat)
  meshes.push(cavity)
  
  const channelLength = wallThickness + 0.5
  for (let i = 0; i < channelCount; i++) {
    const angle = (i/channelCount) * Math.PI * 2
    const row = Math.floor(i/4)
    const y = (row-1) * (bodyLength/4)
    const x = Math.cos(angle) * (outerRadius - channelLength/2)
    const z = Math.sin(angle) * (outerRadius - channelLength/2)
    const channelGeo = new THREE.CylinderGeometry(channelRadius, channelRadius, channelLength, 12)
    const channelMat = new THREE.MeshStandardMaterial({ color: 0x666666 })
    const channel = new THREE.Mesh(channelGeo, channelMat)
    channel.position.set(x, y, z)
    channel.rotation.z = Math.PI/2
    channel.rotation.y = angle
    meshes.push(channel)
  }
  
  return meshes
}
`.trim()
    },

    zigzag_stent: {
        name: 'Zigzag Stent',
        description: 'Vascular stent with zigzag pattern',
        requiredParams: ['length', 'diameter', 'ringCount'],
        generate: (p) => `
const stentLength = ${p.length || 25}
const diameter = ${p.diameter || 8}
const radius = diameter/2
const strutThickness = ${p.strutThickness || 0.3}
const ringCount = ${p.ringCount || 8}
const pointsPerRing = ${p.pointsPerRing || 12}
const bridgeCount = ${p.bridgeCount || 3}

function generateModel() {
  const meshes = []
  
  for (let ring = 0; ring < ringCount; ring++) {
    const y = (ring/(ringCount-1)) * stentLength - stentLength/2
    for (let i = 0; i < pointsPerRing; i++) {
      const angle1 = (i/pointsPerRing) * Math.PI * 2
      const angle2 = ((i+1)/pointsPerRing) * Math.PI * 2
      const r1 = radius + (i%2===0 ? 0.5 : -0.5)
      const r2 = radius + (i%2===0 ? -0.5 : 0.5)
      const x1 = Math.cos(angle1)*r1
      const z1 = Math.sin(angle1)*r1
      const x2 = Math.cos(angle2)*r2
      const z2 = Math.sin(angle2)*r2
      const length = Math.sqrt((x2-x1)**2 + (z2-z1)**2)
      const strutGeo = new THREE.CylinderGeometry(strutThickness/2, strutThickness/2, length, 8)
      const strutMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
      const strut = new THREE.Mesh(strutGeo, strutMat)
      strut.position.set((x1+x2)/2, y, (z1+z2)/2)
      const angleZ = Math.atan2(z2-z1, x2-x1)
      strut.rotation.y = angleZ
      strut.rotation.z = Math.PI/2
      meshes.push(strut)
    }
  }
  
  for (let b = 0; b < bridgeCount; b++) {
    const angle = (b/bridgeCount) * Math.PI * 2
    const x = Math.cos(angle) * radius
    const z = Math.sin(angle) * radius
    for (let ring = 0; ring < ringCount-1; ring++) {
      const y1 = (ring/(ringCount-1)) * stentLength - stentLength/2
      const y2 = ((ring+1)/(ringCount-1)) * stentLength - stentLength/2
      const bridgeLength = y2 - y1
      const bridgeGeo = new THREE.CylinderGeometry(strutThickness/2, strutThickness/2, bridgeLength, 8)
      const bridgeMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
      const bridge = new THREE.Mesh(bridgeGeo, bridgeMat)
      bridge.position.set(x, (y1+y2)/2, z)
      meshes.push(bridge)
    }
  }
  
  return meshes
}
`.trim()
    },

    soft_actuator: {
        name: 'Soft Actuator',
        description: 'Pneumatic soft actuator with chambers',
        requiredParams: ['length', 'width', 'height', 'chamberCount'],
        generate: (p) => `
const actuatorLength = ${p.length || 60}
const actuatorWidth = ${p.width || 15}
const actuatorHeight = ${p.height || 10}
const chamberCount = ${p.chamberCount || 6}
const chamberSpacing = actuatorLength / chamberCount
const wallThickness = ${p.wallThickness || 1.5}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(actuatorLength, wallThickness, actuatorWidth)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xF0F0F0 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  base.position.y = wallThickness/2
  meshes.push(base)
  
  for (let i = 0; i < chamberCount; i++) {
    const x = (i-(chamberCount-1)/2) * chamberSpacing
    const chamberSize = chamberSpacing - 2
    const topGeo = new THREE.BoxGeometry(chamberSize, wallThickness, actuatorWidth-2)
    const topMat = new THREE.MeshStandardMaterial({ color: 0xE0E0E0 })
    const top = new THREE.Mesh(topGeo, topMat)
    top.position.set(x, actuatorHeight, 0)
    meshes.push(top)
    const sideGeo = new THREE.BoxGeometry(wallThickness, actuatorHeight, actuatorWidth-2)
    const sideMat = new THREE.MeshStandardMaterial({ color: 0xD0D0D0 })
    const leftSide = new THREE.Mesh(sideGeo, sideMat)
    leftSide.position.set(x-chamberSize/2, actuatorHeight/2, 0)
    meshes.push(leftSide)
    const rightSide = new THREE.Mesh(sideGeo, sideMat)
    rightSide.position.set(x+chamberSize/2, actuatorHeight/2, 0)
    meshes.push(rightSide)
    for (let ridge = 0; ridge < 3; ridge++) {
      const ridgeY = (ridge+1) * actuatorHeight/4
      const ridgeGeo = new THREE.TorusGeometry(chamberSize/2-1, 0.3, 8, 16)
      const ridgeMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
      const ridgeMesh = new THREE.Mesh(ridgeGeo, ridgeMat)
      ridgeMesh.position.set(x, ridgeY, 0)
      ridgeMesh.rotation.x = Math.PI/2
      meshes.push(ridgeMesh)
    }
  }
  
  return meshes
}
`.trim()
    },

    braided_stent: {
        name: 'Braided Mesh Stent',
        description: 'Self-expanding stent with braided wire pattern',
        requiredParams: ['length', 'diameter', 'wireCount', 'wireDiameter'],
        generate: (p) => `
const stentLength = ${p.length || 40}
const diameter = ${p.diameter || 10}
const radius = diameter/2
const wireDiameter = ${p.wireDiameter || 0.2}
const wireCount = ${p.wireCount || 16}
const braideAngle = ${p.braideAngle || 45} * Math.PI/180
const turnsPerWire = ${p.turnsPerWire || 4}
const segmentsPerTurn = 32

function generateModel() {
  const meshes = []
  
  // Braided wires
  for (let wire = 0; wire < wireCount; wire++) {
    const direction = wire % 2 === 0 ? 1 : -1
    const phaseOffset = (wire / wireCount) * Math.PI * 2
    
    for (let i = 0; i < turnsPerWire * segmentsPerTurn; i++) {
      const t = i / (turnsPerWire * segmentsPerTurn)
      const angle = direction * t * turnsPerWire * Math.PI * 2 + phaseOffset
      const y = t * stentLength - stentLength/2
      
      if (i === 0) continue
      
      const x1 = Math.cos(angle) * radius
      const z1 = Math.sin(angle) * radius
      const prevT = (i-1) / (turnsPerWire * segmentsPerTurn)
      const prevAngle = direction * prevT * turnsPerWire * Math.PI * 2 + phaseOffset
      const prevY = prevT * stentLength - stentLength/2
      const x2 = Math.cos(prevAngle) * radius
      const z2 = Math.sin(prevAngle) * radius
      
      const dx = x1 - x2
      const dy = y - prevY
      const dz = z1 - z2
      const length = Math.sqrt(dx*dx + dy*dy + dz*dz)
      
      const wireGeo = new THREE.CylinderGeometry(wireDiameter/2, wireDiameter/2, length, 6)
      const wireMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
      const wireMesh = new THREE.Mesh(wireGeo, wireMat)
      
      wireMesh.position.set((x1+x2)/2, (y+prevY)/2, (z1+z2)/2)
      
      const angleY = Math.atan2(dz, dx)
      const angleZ = Math.atan2(Math.sqrt(dx*dx + dz*dz), dy)
      wireMesh.rotation.y = angleY
      wireMesh.rotation.z = angleZ - Math.PI/2
      
      meshes.push(wireMesh)
    }
  }
  
  // Radiopaque markers at ends
  const markerRadius = diameter/2 + 0.5
  for (let i = 0; i < 4; i++) {
    const angle = (i/4) * Math.PI * 2
    const x = Math.cos(angle) * markerRadius
    const z = Math.sin(angle) * markerRadius
    
    const markerGeo = new THREE.SphereGeometry(0.4, 12, 12)
    const markerMat = new THREE.MeshStandardMaterial({ color: 0xFFD700 })
    
    const topMarker = new THREE.Mesh(markerGeo, markerMat)
    topMarker.position.set(x, stentLength/2, z)
    meshes.push(topMarker)
    
    const bottomMarker = new THREE.Mesh(markerGeo, markerMat)
    bottomMarker.position.set(x, -stentLength/2, z)
    meshes.push(bottomMarker)
  }
  
  return meshes
}
`.trim()
    },

    mckibben_actuator: {
        name: 'McKibben Artificial Muscle',
        description: 'Pneumatic muscle actuator with braided mesh sleeve',
        requiredParams: ['length', 'diameter', 'filamentCount'],
        generate: (p) => `
const muscleLength = ${p.length || 100}
const diameter = ${p.diameter || 20}
const radius = diameter/2
const filamentCount = ${p.filamentCount || 45}
const filamentThickness = ${p.filamentThickness || 0.5}
const helixAngle = ${p.helixAngle || 30} * Math.PI/180
const turnsPerFilament = 3
const segmentsPerTurn = 24

function generateModel() {
  const meshes = []
  
  // Internal bladder (cavity with BackSide)
  const bladderGeo = new THREE.CylinderGeometry(radius-1, radius-1, muscleLength-4, 32)
  const bladderMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const bladder = new THREE.Mesh(bladderGeo, bladderMat)
  meshes.push(bladder)
  
  // Braided mesh sleeve
  for (let filament = 0; filament < filamentCount; filament++) {
    const direction = filament % 2 === 0 ? 1 : -1
    const phaseOffset = (filament / filamentCount) * Math.PI * 2
    
    for (let i = 0; i < turnsPerFilament * segmentsPerTurn; i++) {
      const t = i / (turnsPerFilament * segmentsPerTurn)
      const angle = direction * t * turnsPerFilament * Math.PI * 2 + phaseOffset
      const y = t * muscleLength - muscleLength/2
      
      if (i === 0) continue
      
      const x1 = Math.cos(angle) * radius
      const z1 = Math.sin(angle) * radius
      const prevT = (i-1) / (turnsPerFilament * segmentsPerTurn)
      const prevAngle = direction * prevT * turnsPerFilament * Math.PI * 2 + phaseOffset
      const prevY = prevT * muscleLength - muscleLength/2
      const x2 = Math.cos(prevAngle) * radius
      const z2 = Math.sin(prevAngle) * radius
      
      const dx = x1 - x2
      const dy = y - prevY
      const dz = z1 - z2
      const length = Math.sqrt(dx*dx + dy*dy + dz*dz)
      
      const filamentGeo = new THREE.CylinderGeometry(filamentThickness/2, filamentThickness/2, length, 6)
      const filamentMat = new THREE.MeshStandardMaterial({ color: 0x4A4A4A })
      const filamentMesh = new THREE.Mesh(filamentGeo, filamentMat)
      
      filamentMesh.position.set((x1+x2)/2, (y+prevY)/2, (z1+z2)/2)
      
      const angleY = Math.atan2(dz, dx)
      const angleZ = Math.atan2(Math.sqrt(dx*dx + dz*dz), dy)
      filamentMesh.rotation.y = angleY
      filamentMesh.rotation.z = angleZ - Math.PI/2
      
      meshes.push(filamentMesh)
    }
  }
  
  // End caps with threaded connections
  const capRadius = radius + 2
  const capHeight = 4
  
  const topCapGeo = new THREE.CylinderGeometry(capRadius, capRadius, capHeight, 32)
  const capMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const topCap = new THREE.Mesh(topCapGeo, capMat)
  topCap.position.y = muscleLength/2 + capHeight/2
  meshes.push(topCap)
  
  const bottomCap = new THREE.Mesh(topCapGeo, capMat)
  bottomCap.position.y = -muscleLength/2 - capHeight/2
  meshes.push(bottomCap)
  
  // M8 threaded connections (simplified as cylinders)
  const threadRadius = 4
  const threadLength = 6
  const threadGeo = new THREE.CylinderGeometry(threadRadius, threadRadius, threadLength, 16)
  const threadMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  
  const topThread = new THREE.Mesh(threadGeo, threadMat)
  topThread.position.y = muscleLength/2 + capHeight + threadLength/2
  meshes.push(topThread)
  
  const bottomThread = new THREE.Mesh(threadGeo, threadMat)
  bottomThread.position.y = -muscleLength/2 - capHeight - threadLength/2
  meshes.push(bottomThread)
  
  return meshes
}
`.trim()
    },

    segmented_soft_robot: {
        name: 'Segmented Soft Robot',
        description: 'Bio-inspired segmented robot (caterpillar/earthworm)',
        requiredParams: ['segmentCount', 'segmentLength', 'diameter'],
        generate: (p) => `
const segmentCount = ${p.segmentCount || 5}
const segmentLength = ${p.segmentLength || 20}
const diameter = ${p.diameter || 30}
const radius = diameter/2
const totalLength = segmentCount * segmentLength
const ridgeHeight = ${p.ridgeHeight || 2}
const ridgeSpacing = ${p.ridgeSpacing || 5}
const chamberCount = ${p.chamberCount || 4}

function generateModel() {
  const meshes = []
  
  for (let seg = 0; seg < segmentCount; seg++) {
    const segmentY = seg * segmentLength - totalLength/2 + segmentLength/2
    
    // Main segment body
    const bodyGeo = new THREE.CylinderGeometry(radius, radius, segmentLength-2, 32)
    const bodyMat = new THREE.MeshStandardMaterial({ color: 0xF0E0D0 })
    const body = new THREE.Mesh(bodyGeo, bodyMat)
    body.position.y = segmentY
    meshes.push(body)
    
    // Radial expansion chambers (visible as grooves)
    for (let chamber = 0; chamber < chamberCount; chamber++) {
      const chamberY = segmentY - segmentLength/2 + (chamber+0.5) * segmentLength/chamberCount
      const grooveGeo = new THREE.TorusGeometry(radius-0.5, 0.4, 12, 32)
      const grooveMat = new THREE.MeshStandardMaterial({ color: 0xE0D0C0 })
      const groove = new THREE.Mesh(grooveGeo, grooveMat)
      groove.position.y = chamberY
      groove.rotation.x = Math.PI/2
      meshes.push(groove)
    }
    
    // Gripping ridges/protrusions around circumference
    const ridgeCount = Math.floor(segmentLength / ridgeSpacing)
    for (let r = 0; r < ridgeCount; r++) {
      const ridgeY = segmentY - segmentLength/2 + r * ridgeSpacing
      const ridgesPerCircle = 12
      
      for (let i = 0; i < ridgesPerCircle; i++) {
        const angle = (i/ridgesPerCircle) * Math.PI * 2
        const x = Math.cos(angle) * radius
        const z = Math.sin(angle) * radius
        
        const ridgeGeo = new THREE.ConeGeometry(1, ridgeHeight, 8)
        const ridgeMat = new THREE.MeshStandardMaterial({ color: 0xD0C0B0 })
        const ridge = new THREE.Mesh(ridgeGeo, ridgeMat)
        ridge.position.set(x, ridgeY, z)
        ridge.rotation.x = Math.PI/2
        ridge.rotation.y = angle
        meshes.push(ridge)
      }
    }
    
    // Tapered connection to next segment
    if (seg < segmentCount - 1) {
      const connectorGeo = new THREE.CylinderGeometry(radius-1, radius-1, 2, 16)
      const connectorMat = new THREE.MeshStandardMaterial({ color: 0xC0B0A0 })
      const connector = new THREE.Mesh(connectorGeo, connectorMat)
      connector.position.y = segmentY + segmentLength/2
      meshes.push(connector)
    }
    
    // Sensing bumps (if requested)
    if (${p.sensingBumps || 'false'}) {
      const sensorCount = 4
      for (let s = 0; s < sensorCount; s++) {
        const angle = (s/sensorCount) * Math.PI * 2
        const x = Math.cos(angle) * (radius + 1)
        const z = Math.sin(angle) * (radius + 1)
        const sensorGeo = new THREE.SphereGeometry(0.8, 12, 12)
        const sensorMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
        const sensor = new THREE.Mesh(sensorGeo, sensorMat)
        sensor.position.set(x, segmentY, z)
        meshes.push(sensor)
      }
    }
  }
  
  return meshes
}
`.trim()
    },

    wrist_splint: {
        name: 'Wrist Splint',
        description: 'Adaptive wrist splint with ventilation',
        requiredParams: ['length', 'width'],
        generate: (p) => `
const splintLength = ${p.length || 180}
const splintWidth = ${p.width || 60}
const wallThickness = 3
const strapCount = ${p.strapCount || 3}

function generateModel() {
  const meshes = []
  
  const bodyGeo = new THREE.BoxGeometry(splintWidth, splintLength, wallThickness)
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const body = new THREE.Mesh(bodyGeo, bodyMat)
  body.position.y = 0
  meshes.push(body)
  
  const holeSize = 5
  const holesX = Math.floor(splintWidth / 12)
  const holesY = Math.floor(splintLength / 12)
  
  for (let ix = 0; ix < holesX; ix++) {
    for (let iy = 0; iy < holesY; iy++) {
      const x = (ix - holesX/2) * 12
      const y = (iy - holesY/2) * 12
      const holeGeo = new THREE.CylinderGeometry(holeSize/2, holeSize/2, wallThickness+1, 6)
      const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
      const hole = new THREE.Mesh(holeGeo, holeMat)
      hole.position.set(x, y, 0)
      hole.rotation.x = Math.PI/2
      meshes.push(hole)
    }
  }
  
  for (let i = 0; i < strapCount; i++) {
    const y = (i/(strapCount-1)) * splintLength * 0.7 - splintLength*0.35
    const strapGeo = new THREE.BoxGeometry(splintWidth + 20, 8, 2)
    const strapMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
    const strap = new THREE.Mesh(strapGeo, strapMat)
    strap.position.set(0, y, wallThickness/2 + 1)
    meshes.push(strap)
    const ratchetGeo = new THREE.BoxGeometry(10, 10, 4)
    const ratchetMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
    const ratchet = new THREE.Mesh(ratchetGeo, ratchetMat)
    ratchet.position.set(splintWidth/2 + 15, y, wallThickness/2 + 2)
    meshes.push(ratchet)
  }
  
  const palmGeo = new THREE.BoxGeometry(splintWidth-10, 40, 8)
  const palmMat = new THREE.MeshStandardMaterial({ color: 0xF0F0F0 })
  const palm = new THREE.Mesh(palmGeo, palmMat)
  palm.position.set(0, -splintLength/2 + 20, wallThickness/2 + 4)
  meshes.push(palm)
  
  const paddingCount = 3
  for (let i = 0; i < paddingCount; i++) {
    const y = (i/(paddingCount-1)) * splintLength * 0.6 - splintLength*0.3
    const paddingGeo = new THREE.BoxGeometry(10, splintLength/6, 2)
    const paddingMat = new THREE.MeshStandardMaterial({ color: 0xD0D0D0 })
    const padding = new THREE.Mesh(paddingGeo, paddingMat)
    padding.position.set(splintWidth/2 - 5, y, wallThickness/2 + 1)
    meshes.push(padding)
  }
  
  return meshes
}
`.trim()
    },

    finger_splint: {
        name: 'Finger Splint',
        description: 'Articulated finger splint with hinges',
        requiredParams: ['length', 'width'],
        generate: (p) => `
const splintLength = ${p.length || 70}
const splintWidth = ${p.width || 18}
const wallThickness = 3

function generateModel() {
  const meshes = []
  
  const segment1Length = splintLength * 0.45
  const segment2Length = splintLength * 0.45
  const hingeGap = splintLength * 0.1
  
  const segment1Geo = new THREE.CylinderGeometry(splintWidth/2, splintWidth/2, segment1Length, 16)
  const segmentMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8 })
  const segment1 = new THREE.Mesh(segment1Geo, segmentMat)
  segment1.position.y = -splintLength/2 + segment1Length/2
  meshes.push(segment1)
  
  const innerGeo1 = new THREE.CylinderGeometry(splintWidth/2 - wallThickness, splintWidth/2 - wallThickness, segment1Length-4, 16)
  const innerMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const inner1 = new THREE.Mesh(innerGeo1, innerMat)
  inner1.position.y = -splintLength/2 + segment1Length/2
  meshes.push(inner1)
  
  const segment2 = new THREE.Mesh(segment1Geo, segmentMat)
  segment2.position.y = splintLength/2 - segment2Length/2
  meshes.push(segment2)
  const inner2 = new THREE.Mesh(innerGeo1, innerMat)
  inner2.position.y = splintLength/2 - segment2Length/2
  meshes.push(inner2)
  
  const hingeY = -splintLength/2 + segment1Length + hingeGap/2
  const hingeGeo = new THREE.CylinderGeometry(3, 3, splintWidth + 4, 16)
  const hingeMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const hinge = new THREE.Mesh(hingeGeo, hingeMat)
  hinge.position.y = hingeY
  hinge.rotation.z = Math.PI/2
  meshes.push(hinge)
  
  const slotCount = 4
  for (let i = 0; i < slotCount; i++) {
    const y = (i/(slotCount-1)) * segment1Length - splintLength/2 + segment1Length/2
    const slotGeo = new THREE.BoxGeometry(2, 15, splintWidth + 2)
    const slotMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const slot = new THREE.Mesh(slotGeo, slotMat)
    slot.position.set(splintWidth/2, y, 0)
    meshes.push(slot)
  }
  
  const velcroCount = 2
  for (let i = 0; i < velcroCount; i++) {
    const y = i === 0 ? -splintLength/2 + segment1Length*0.3 : splintLength/2 - segment2Length*0.3
    const velcroGeo = new THREE.BoxGeometry(splintWidth + 10, 6, 1)
    const velcroMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
    const velcro = new THREE.Mesh(velcroGeo, velcroMat)
    velcro.position.set(0, y, splintWidth/2 + 1)
    meshes.push(velcro)
  }
  
  return meshes
}
`.trim()
    },

    prosthetic_socket: {
        name: 'Prosthetic Socket',
        description: 'Modular prosthetic socket with conical shape',
        requiredParams: ['height', 'proximalDiameter', 'distalDiameter'],
        generate: (p) => `
const socketHeight = ${p.height || 300}
const proximalRadius = ${p.proximalDiameter ? p.proximalDiameter / 2 : 60}
const distalRadius = ${p.distalDiameter ? p.distalDiameter / 2 : 40}
const wallThickness = 8

function generateModel() {
  const meshes = []
  
  const outerGeo = new THREE.CylinderGeometry(distalRadius, proximalRadius, socketHeight, 32)
  const outerMat = new THREE.MeshStandardMaterial({ color: 0xD0D0D0 })
  const outer = new THREE.Mesh(outerGeo, outerMat)
  outer.position.y = 0
  meshes.push(outer)
  
  const linerGeo = new THREE.CylinderGeometry(distalRadius-wallThickness, proximalRadius-wallThickness, socketHeight-10, 32)
  const linerMat = new THREE.MeshStandardMaterial({ color: 0xF5E6D3, side: THREE.BackSide })
  const liner = new THREE.Mesh(linerGeo, linerMat)
  meshes.push(liner)
  
  const windowCount = 8
  for (let i = 0; i < windowCount; i++) {
    const angle = (i/windowCount) * Math.PI * 2
    const avgRadius = (proximalRadius + distalRadius)/2
    const x = Math.cos(angle) * avgRadius
    const z = Math.sin(angle) * avgRadius
    const windowGeo = new THREE.BoxGeometry(wallThickness + 2, 40, 30)
    const windowMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const window = new THREE.Mesh(windowGeo, windowMat)
    window.position.set(x, socketHeight/4, z)
    window.rotation.y = angle
    meshes.push(window)
  }
  
  const ribCount = 8
  for (let i = 0; i < ribCount; i++) {
    const angle = (i/ribCount) * Math.PI * 2
    const x = Math.cos(angle) * (proximalRadius + distalRadius)/2
    const z = Math.sin(angle) * (proximalRadius + distalRadius)/2
    const ribGeo = new THREE.BoxGeometry(5, socketHeight, 3)
    const ribMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
    const rib = new THREE.Mesh(ribGeo, ribMat)
    rib.position.set(x, 0, z)
    rib.rotation.y = angle
    meshes.push(rib)
  }
  
  const valveGeo = new THREE.CylinderGeometry(6, 6, 15, 16)
  const valveMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const valve = new THREE.Mesh(valveGeo, valveMat)
  valve.position.set(proximalRadius + 10, socketHeight/3, 0)
  valve.rotation.z = Math.PI/2
  meshes.push(valve)
  
  const releaseGeo = new THREE.BoxGeometry(20, 15, 10)
  const releaseMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const release = new THREE.Mesh(releaseGeo, releaseMat)
  release.position.set(0, socketHeight/2 + 5, distalRadius + 5)
  meshes.push(release)
  
  return meshes
}
`.trim()
    },

    voronoi_scaffold: {
        name: 'Voronoi Scaffold',
        description: 'Porous scaffold with random cell pattern',
        requiredParams: ['diameter', 'height'],
        generate: (p) => `
const diameter = ${p.diameter || 40}
const height = ${p.height || 30}
const radius = diameter/2
const cellCount = ${p.cellCount || 200}
const strutThickness = ${p.strutThickness || 1.5}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.CylinderGeometry(radius, radius, 3, 32)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xE0E0E0 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  base.position.y = -height/2
  meshes.push(base)
  
  const seeds = []
  for (let i = 0; i < cellCount; i++) {
    const theta = Math.random() * Math.PI * 2
    const r = Math.sqrt(Math.random()) * radius * 0.8
    const y = Math.random() * height - height/2
    seeds.push({
      x: Math.cos(theta) * r,
      y: y,
      z: Math.sin(theta) * r
    })
  }
  
  for (let i = 0; i < seeds.length; i++) {
    const seed = seeds[i]
    const neighbors = []
    for (let j = 0; j < seeds.length; j++) {
      if (i === j) continue
      const other = seeds[j]
      const dist = Math.sqrt(
        (seed.x-other.x)**2 + 
        (seed.y-other.y)**2 + 
        (seed.z-other.z)**2
      )
      if (dist < diameter/5) {
        neighbors.push({index: j, dist: dist})
      }
    }
    
    neighbors.sort((a,b) => a.dist - b.dist)
    const maxConnections = 6
    for (let k = 0; k < Math.min(maxConnections, neighbors.length); k++) {
      const other = seeds[neighbors[k].index]
      const dx = other.x - seed.x
      const dy = other.y - seed.y
      const dz = other.z - seed.z
      const length = Math.sqrt(dx*dx + dy*dy + dz*dz)
      
      const strutGeo = new THREE.CylinderGeometry(strutThickness/2, strutThickness/2, length, 6)
      const strutMat = new THREE.MeshStandardMaterial({ color: 0xCCCCCC })
      const strut = new THREE.Mesh(strutGeo, strutMat)
      
      strut.position.set(
        (seed.x + other.x)/2,
        (seed.y + other.y)/2,
        (seed.z + other.z)/2
      )
      
      const angleY = Math.atan2(dz, dx)
      const angleZ = Math.atan2(Math.sqrt(dx*dx + dz*dz), dy)
      strut.rotation.y = angleY
      strut.rotation.z = angleZ - Math.PI/2
      
      meshes.push(strut)
    }
  }
  
  return meshes
}
`.trim()
    },

    auxetic_honeycomb: {
        name: 'Auxetic Honeycomb',
        description: 'Re-entrant hexagonal cells with negative Poisson ratio',
        requiredParams: ['width', 'height'],
        generate: (p) => `
const panelWidth = ${p.width || 100}
const panelHeight = ${p.height || 100}
const panelThickness = ${p.thickness || 10}
const cellWidth = ${p.cellWidth || 8}
const strutThickness = ${p.strutThickness || 1.5}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(panelWidth, panelHeight, panelThickness)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xF0F0F0 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  meshes.push(base)
  
  const cellsX = Math.floor(panelWidth / cellWidth)
  const cellsY = Math.floor(panelHeight / cellWidth)
  
  for (let ix = 0; ix < cellsX; ix++) {
    for (let iy = 0; iy < cellsY; iy++) {
      const cx = (ix - cellsX/2) * cellWidth
      const cy = (iy - cellsY/2) * cellWidth
      
      const angle = 30 * Math.PI/180
      const innerSize = cellWidth * 0.4
      
      const points = [
        {x: cx, y: cy + innerSize},
        {x: cx + innerSize * Math.cos(angle), y: cy + innerSize * Math.sin(angle)},
        {x: cx + innerSize * Math.cos(angle), y: cy - innerSize * Math.sin(angle)},
        {x: cx, y: cy - innerSize},
        {x: cx - innerSize * Math.cos(angle), y: cy - innerSize * Math.sin(angle)},
        {x: cx - innerSize * Math.cos(angle), y: cy + innerSize * Math.sin(angle)}
      ]
      
      for (let i = 0; i < points.length; i++) {
        const p1 = points[i]
        const p2 = points[(i+1) % points.length]
        const length = Math.sqrt((p2.x-p1.x)**2 + (p2.y-p1.y)**2)
        const strutGeo = new THREE.BoxGeometry(strutThickness, length, panelThickness)
        const strutMat = new THREE.MeshStandardMaterial({ color: 0xD0D0D0 })
        const strut = new THREE.Mesh(strutGeo, strutMat)
        strut.position.set((p1.x+p2.x)/2, (p1.y+p2.y)/2, 0)
        strut.rotation.z = Math.atan2(p2.y-p1.y, p2.x-p1.x) + Math.PI/2
        meshes.push(strut)
      }
    }
  }
  
  for (let i = 0; i < 4; i++) {
    const x = (i % 2 === 0 ? -1 : 1) * panelWidth/2
    const y = (i < 2 ? -1 : 1) * panelHeight/2
    const holeGeo = new THREE.CylinderGeometry(2, 2, panelThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x*0.9, y*0.9, 0)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  return meshes
}
`.trim()
    },

    advanced_lattice: {
        name: 'Advanced Lattice Structure',
        description: 'Lattice with different unit cell types',
        requiredParams: ['size', 'cellSize', 'strutThickness', 'cellType'],
        generate: (p) => `
const latticeSize = ${p.size || 50}
const unitCellSize = ${p.cellSize || 5}
const strutThickness = ${p.strutThickness || 0.8}
const cellType = "${p.cellType || 'cubic'}"

function generateModel() {
  const meshes = []
  const cellsPerSide = Math.floor(latticeSize / unitCellSize)
  
  function createStrut(x1, y1, z1, x2, y2, z2) {
    const dx = x2 - x1, dy = y2 - y1, dz = z2 - z1
    const length = Math.sqrt(dx*dx + dy*dy + dz*dz)
    const strutGeo = new THREE.CylinderGeometry(strutThickness/2, strutThickness/2, length, 8)
    const strutMat = new THREE.MeshStandardMaterial({ color: 0xCCCCCC })
    const strut = new THREE.Mesh(strutGeo, strutMat)
    strut.position.set((x1+x2)/2, (y1+y2)/2, (z1+z2)/2)
    const angleY = Math.atan2(dz, dx)
    const angleZ = Math.atan2(Math.sqrt(dx*dx + dz*dz), dy)
    strut.rotation.y = angleY
    strut.rotation.z = angleZ - Math.PI/2
    meshes.push(strut)
  }
  
  for (let ix = 0; ix < cellsPerSide; ix++) {
    for (let iy = 0; iy < cellsPerSide; iy++) {
      for (let iz = 0; iz < cellsPerSide; iz++) {
        const cx = (ix - cellsPerSide/2) * unitCellSize
        const cy = (iy - cellsPerSide/2) * unitCellSize
        const cz = (iz - cellsPerSide/2) * unitCellSize
        const h = unitCellSize / 2
        
        if (cellType === 'bcc' || cellType === 'body-centered') {
          const corners = [
            [cx-h, cy-h, cz-h], [cx+h, cy-h, cz-h],
            [cx-h, cy+h, cz-h], [cx+h, cy+h, cz-h],
            [cx-h, cy-h, cz+h], [cx+h, cy-h, cz+h],
            [cx-h, cy+h, cz+h], [cx+h, cy+h, cz+h]
          ]
          for (let i = 0; i < 8; i++) {
            createStrut(...corners[i], cx, cy, cz)
          }
        }
        else if (cellType === 'fcc' || cellType === 'face-centered') {
          createStrut(cx-h, cy-h, cz, cx+h, cy+h, cz)
          createStrut(cx+h, cy-h, cz, cx-h, cy+h, cz)
          createStrut(cx, cy-h, cz-h, cx, cy+h, cz+h)
          createStrut(cx, cy+h, cz-h, cx, cy-h, cz+h)
          createStrut(cx-h, cy, cz-h, cx+h, cy, cz+h)
          createStrut(cx+h, cy, cz-h, cx-h, cy, cz+h)
        }
        else {
          if (ix < cellsPerSide - 1) createStrut(cx+h, cy, cz, cx+h+unitCellSize, cy, cz)
          if (iy < cellsPerSide - 1) createStrut(cx, cy+h, cz, cx, cy+h+unitCellSize, cz)
          if (iz < cellsPerSide - 1) createStrut(cx, cy, cz+h, cx, cy, cz+h+unitCellSize)
        }
      }
    }
  }
  return meshes
}
`.trim()
},

    chiral_metamaterial: {
        name: 'Chiral Metamaterial',
        description: 'Rotating nodes with curved ligaments',
        requiredParams: ['size', 'nodeCount', 'nodeDiameter', 'ligamentThickness'], // IMPORTANT: Ajoutez cette ligne
        generate: (p) => `
const tileSize = ${p.size || 60}  // Utilise le paramètre extrait
const nodeCount = ${p.nodeCount || 9}
const nodeRadius = ${p.nodeDiameter ? p.nodeDiameter / 2 : 4}
const ligamentThickness = ${p.ligamentThickness || 2}

function generateModel() {
  const meshes = []
  
  const nodesPerSide = Math.sqrt(nodeCount)
  const spacing = tileSize / (nodesPerSide + 1)
  
  for (let ix = 0; ix < nodesPerSide; ix++) {
    for (let iy = 0; iy < nodesPerSide; iy++) {
      const x = (ix - (nodesPerSide-1)/2) * spacing
      const y = (iy - (nodesPerSide-1)/2) * spacing
      
      const nodeGeo = new THREE.CylinderGeometry(nodeRadius, nodeRadius, 3, 16)
      const nodeMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
      const node = new THREE.Mesh(nodeGeo, nodeMat)
      node.position.set(x, y, 0)
      node.rotation.x = Math.PI/2
      meshes.push(node)
      
      if (ix < nodesPerSide - 1) {
        const nextX = (ix+1 - (nodesPerSide-1)/2) * spacing
        const curvePoints = []
        const segments = 16
        for (let i = 0; i <= segments; i++) {
          const t = i / segments
          const px = x + t * (nextX - x)
          const py = y + Math.sin(t * Math.PI) * spacing * 0.3
          curvePoints.push(new THREE.Vector3(px, py, 0))
        }
        
        for (let i = 0; i < curvePoints.length - 1; i++) {
          const p1 = curvePoints[i]
          const p2 = curvePoints[i+1]
          const length = p1.distanceTo(p2)
          const ligGeo = new THREE.CylinderGeometry(ligamentThickness/2, ligamentThickness/2, length, 6)
          const ligMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
          const lig = new THREE.Mesh(ligGeo, ligMat)
          lig.position.set((p1.x+p2.x)/2, (p1.y+p2.y)/2, 0)
          const angle = Math.atan2(p2.y-p1.y, p2.x-p1.x)
          lig.rotation.z = angle + Math.PI/2
          meshes.push(lig)
        }
      }
      
      if (iy < nodesPerSide - 1) {
        const nextY = (iy+1 - (nodesPerSide-1)/2) * spacing
        const curvePoints = []
        const segments = 16
        for (let i = 0; i <= segments; i++) {
          const t = i / segments
          const py = y + t * (nextY - y)
          const px = x + Math.sin(t * Math.PI) * spacing * 0.3
          curvePoints.push(new THREE.Vector3(px, py, 0))
        }
        
        for (let i = 0; i < curvePoints.length - 1; i++) {
          const p1 = curvePoints[i]
          const p2 = curvePoints[i+1]
          const length = p1.distanceTo(p2)
          const ligGeo = new THREE.CylinderGeometry(ligamentThickness/2, ligamentThickness/2, length, 6)
          const ligMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
          const lig = new THREE.Mesh(ligGeo, ligMat)
          lig.position.set((p1.x+p2.x)/2, (p1.y+p2.y)/2, 0)
          const angle = Math.atan2(p2.y-p1.y, p2.x-p1.x)
          lig.rotation.z = angle + Math.PI/2
          meshes.push(lig)
        }
      }
    }
  }
  
  return meshes
}
`.trim()
    },

    microfluidic_chip: {
        name: 'Microfluidic Chip',
        description: 'Serpentine mixing channels with ports',
        requiredParams: ['length', 'width', 'channelWidth'],
        generate: (p) => `
const chipLength = ${p.length || 75}
const chipWidth = ${p.width || 50}
const chipThickness = ${p.thickness || 5}
const channelWidth = ${p.channelWidth || 0.3}
const channelDepth = ${p.channelDepth || 0.2}
const loopCount = ${p.loopCount || 8}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(chipLength, chipWidth, chipThickness)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xE8E8E8, transparent: true, opacity: 0.7 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  meshes.push(base)
  
  const loopHeight = chipWidth * 0.8 / loopCount
  let prevX = -chipLength/2 + 10
  let prevY = -chipWidth/2 + 5
  
  for (let i = 0; i < loopCount; i++) {
    const direction = i % 2 === 0 ? 1 : -1
    const targetY = prevY + direction * loopHeight
    
    const segments = 8
    for (let j = 0; j < segments; j++) {
      const t1 = j / segments
      const t2 = (j+1) / segments
      const x1 = prevX + (chipLength * 0.8 / loopCount) * t1
      const y1 = prevY + direction * loopHeight * Math.sin(t1 * Math.PI/2)
      const x2 = prevX + (chipLength * 0.8 / loopCount) * t2
      const y2 = prevY + direction * loopHeight * Math.sin(t2 * Math.PI/2)
      
      const length = Math.sqrt((x2-x1)**2 + (y2-y1)**2)
      const channelGeo = new THREE.BoxGeometry(channelWidth, length, channelDepth)
      const channelMat = new THREE.MeshStandardMaterial({ color: 0x4080FF })
      const channel = new THREE.Mesh(channelGeo, channelMat)
      channel.position.set((x1+x2)/2, (y1+y2)/2, chipThickness/2)
      channel.rotation.z = Math.atan2(y2-y1, x2-x1) + Math.PI/2
      meshes.push(channel)
    }
    
    prevX += chipLength * 0.8 / loopCount
    prevY = targetY
  }
  
  const inletGeo = new THREE.CylinderGeometry(1, 1, chipThickness+2, 16)
  const portMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const inlet = new THREE.Mesh(inletGeo, portMat)
  inlet.position.set(-chipLength/2 + 10, -chipWidth/2 + 5, 0)
  inlet.rotation.x = Math.PI/2
  meshes.push(inlet)
  
  const outlet = new THREE.Mesh(inletGeo, portMat)
  outlet.position.set(chipLength/2 - 10, prevY, 0)
  outlet.rotation.x = Math.PI/2
  meshes.push(outlet)
  
  const windowGeo = new THREE.BoxGeometry(20, 20, 1)
  const windowMat = new THREE.MeshStandardMaterial({ color: 0xFFFFFF, transparent: true, opacity: 0.3 })
  const window = new THREE.Mesh(windowGeo, windowMat)
  window.position.set(0, 0, chipThickness/2 + 0.5)
  meshes.push(window)
  
  return meshes
}
`.trim()
    },

    cell_culture_scaffold: {
        name: 'Cell Culture Scaffold',
        description: 'Octahedral unit cell structure with pores',
        requiredParams: ['diameter', 'thickness'],
        generate: (p) => `
const diameter = ${p.diameter || 20}
const thickness = ${p.thickness || 5}
const radius = diameter/2
const poreSize = ${p.poreSize || 0.4}
const strutDiameter = ${p.strutDiameter || 0.2}
const cellSize = poreSize * 2

function generateModel() {
  const meshes = []
  
  const cellsRadial = Math.floor(diameter / cellSize)
  const cellsVertical = Math.floor(thickness / cellSize)
  
  for (let ix = -cellsRadial/2; ix < cellsRadial/2; ix++) {
    for (let iy = 0; iy < cellsVertical; iy++) {
      for (let iz = -cellsRadial/2; iz < cellsRadial/2; iz++) {
        const x = ix * cellSize
        const y = iy * cellSize - thickness/2
        const z = iz * cellSize
        
        const distFromCenter = Math.sqrt(x*x + z*z)
        if (distFromCenter > radius) continue
        
        const octPoints = [
          {x: x, y: y + cellSize/2, z: z},
          {x: x + cellSize/2, y: y, z: z},
          {x: x, y: y, z: z + cellSize/2},
          {x: x - cellSize/2, y: y, z: z},
          {x: x, y: y, z: z - cellSize/2},
          {x: x, y: y - cellSize/2, z: z}
        ]
        
        for (let i = 0; i < octPoints.length; i++) {
          for (let j = i+1; j < octPoints.length; j++) {
            const p1 = octPoints[i]
            const p2 = octPoints[j]
            const dx = p2.x - p1.x
            const dy = p2.y - p1.y
            const dz = p2.z - p1.z
            const length = Math.sqrt(dx*dx + dy*dy + dz*dz)
            
            if (length < cellSize * 0.9) {
              const strutGeo = new THREE.CylinderGeometry(strutDiameter/2, strutDiameter/2, length, 6)
              const strutMat = new THREE.MeshStandardMaterial({ color: 0xE0E0E0 })
              const strut = new THREE.Mesh(strutGeo, strutMat)
              strut.position.set((p1.x+p2.x)/2, (p1.y+p2.y)/2, (p1.z+p2.z)/2)
              
              const angleY = Math.atan2(dz, dx)
              const angleZ = Math.atan2(Math.sqrt(dx*dx + dz*dz), dy)
              strut.rotation.y = angleY
              strut.rotation.z = angleZ - Math.PI/2
              
              meshes.push(strut)
            }
          }
        }
      }
    }
  }
  
  return meshes
}
`.trim()
    },

    compliant_gripper: {
        name: 'Compliant Gripper',
        description: 'Parallel jaw gripper with living hinges',
        requiredParams: ['jawLength'],
        generate: (p) => `
const jawLength = ${p.jawLength || 60}
const jawWidth = ${p.jawWidth || 15}
const flexureThickness = ${p.flexureThickness || 0.5}
const baseSize = ${p.baseSize || 30}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(baseSize, baseSize, 5)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xD0D0D0 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  base.position.y = -10
  meshes.push(base)
  
  for (let i = 0; i < 4; i++) {
    const x = (i % 2 === 0 ? -1 : 1) * baseSize/2 * 0.7
    const z = (i < 2 ? -1 : 1) * baseSize/2 * 0.7
    const holeGeo = new THREE.CylinderGeometry(2, 2, 6, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, -10, z)
    meshes.push(hole)
  }
  
  for (let side = 0; side < 2; side++) {
    const xOffset = (side === 0 ? -1 : 1) * 8
    
    const armGeo = new THREE.BoxGeometry(5, 15, 3)
    const armMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
    const arm = new THREE.Mesh(armGeo, armMat)
    arm.position.set(xOffset, 0, 0)
    meshes.push(arm)
    
    const hingeGeo = new THREE.BoxGeometry(5, flexureThickness, 3)
    const hingeMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
    const hinge = new THREE.Mesh(hingeGeo, hingeMat)
    hinge.position.set(xOffset, 8, 0)
    meshes.push(hinge)
    
    const jawGeo = new THREE.BoxGeometry(5, jawLength, jawWidth)
    const jawMat = new THREE.MeshStandardMaterial({ color: 0xB0B0B0 })
    const jaw = new THREE.Mesh(jawGeo, jawMat)
    jaw.position.set(xOffset, jawLength/2 + 10, 0)
    meshes.push(jaw)
    
    const ribCount = 5
    for (let r = 0; r < ribCount; r++) {
      const y = jawLength/2 + 10 - jawLength/2 + (r/(ribCount-1)) * jawLength * 0.8
      const ribGeo = new THREE.BoxGeometry(5, 2, jawWidth * 0.6)
      const ribMat = new THREE.MeshStandardMaterial({ color: 0x909090 })
      const rib = new THREE.Mesh(ribGeo, ribMat)
      rib.position.set(xOffset, y, 0)
      meshes.push(rib)
    }
  }
  
  return meshes
}
`.trim()
    },

    bistable_mechanism: {
        name: 'Bistable Mechanism',
        description: 'Snap-through mechanism with curved beam',
        requiredParams: ['beamLength'],
        generate: (p) => `
const beamLength = ${p.beamLength || 80}
const beamWidth = ${p.beamWidth || 10}
const beamThickness = ${p.beamThickness || 3}
const curveRise = ${p.curveRise || 15}

function generateModel() {
  const meshes = []
  
  const segments = 20
  for (let i = 0; i < segments; i++) {
    const t = i / segments
    const x = (t - 0.5) * beamLength
    const y = Math.sin(t * Math.PI) * curveRise
    
    const segmentGeo = new THREE.BoxGeometry(beamLength/segments, beamWidth, beamThickness)
    const segmentMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
    const segment = new THREE.Mesh(segmentGeo, segmentMat)
    segment.position.set(x, y, 0)
    
    const angle = Math.atan2(
      Math.sin((t+1/segments) * Math.PI) * curveRise - y,
      beamLength/segments
    )
    segment.rotation.z = angle
    meshes.push(segment)
  }
  
  const tabGeo = new THREE.BoxGeometry(15, 20, beamThickness)
  const tabMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const leftTab = new THREE.Mesh(tabGeo, tabMat)
  leftTab.position.set(-beamLength/2, 0, 0)
  meshes.push(leftTab)
  const rightTab = new THREE.Mesh(tabGeo, tabMat)
  rightTab.position.set(beamLength/2, 0, 0)
  meshes.push(rightTab)
  
  const stopGeo = new THREE.BoxGeometry(5, 5, beamThickness + 4)
  const stopMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const topStop = new THREE.Mesh(stopGeo, stopMat)
  topStop.position.set(0, curveRise + 5, 0)
  meshes.push(topStop)
  const bottomStop = new THREE.Mesh(stopGeo, stopMat)
  bottomStop.position.set(0, -5, 0)
  meshes.push(bottomStop)
  
  return meshes
}
`.trim()
    },

    lattice_cube: {
        name: 'Lattice Structure',
        description: 'Cubic lattice with struts',
        requiredParams: ['size', 'cellSize', 'thickness'],
        generate: (p) => `
const cubeSize = ${p.size || 50}
const unitCellSize = ${p.cellSize || 5}
const strutThickness = ${p.thickness || 0.8}
const cellsPerSide = Math.floor(cubeSize/unitCellSize)

function generateModel() {
  const meshes = []
  for (let ix = 0; ix < cellsPerSide; ix++) {
    for (let iy = 0; iy < cellsPerSide; iy++) {
      for (let iz = 0; iz < cellsPerSide; iz++) {
        const x = (ix-cellsPerSide/2)*unitCellSize
        const y = (iy-cellsPerSide/2)*unitCellSize
        const z = (iz-cellsPerSide/2)*unitCellSize
        const strutXGeo = new THREE.CylinderGeometry(strutThickness/2, strutThickness/2, unitCellSize, 8)
        const strutMat = new THREE.MeshStandardMaterial({ color: 0xCCCCCC })
        const strutX = new THREE.Mesh(strutXGeo, strutMat)
        strutX.position.set(x+unitCellSize/2, y, z)
        strutX.rotation.z = Math.PI/2
        meshes.push(strutX)
        const strutY = new THREE.Mesh(strutXGeo, strutMat)
        strutY.position.set(x, y+unitCellSize/2, z)
        meshes.push(strutY)
        const strutZ = new THREE.Mesh(strutXGeo, strutMat)
        strutZ.position.set(x, y, z+unitCellSize/2)
        strutZ.rotation.x = Math.PI/2
        meshes.push(strutZ)
      }
    }
  }
  return meshes
}
`.trim()
    },
    engine_mount: {
        name: 'Engine Mount Bracket',
        description: 'Motor mount with rubber insert cavity and mounting holes',
        requiredParams: ['length', 'width', 'thickness', 'holeCount'],
        generate: (p) => `
const mountLength = ${p.length || 120}
const mountWidth = ${p.width || 80}
const mountThickness = ${p.thickness || 15}
const holeCount = ${p.holeCount || 4}
const holeDiameter = 10
const insertDiameter = ${p.insertDiameter || 50}
const ribThickness = ${p.ribThickness || 8}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(mountLength, mountWidth, mountThickness)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  meshes.push(base)
  
  const cavityGeo = new THREE.CylinderGeometry(insertDiameter/2, insertDiameter/2, mountThickness+2, 32)
  const cavityMat = new THREE.MeshStandardMaterial({ color: 0x333333 })
  const cavity = new THREE.Mesh(cavityGeo, cavityMat)
  cavity.rotation.x = Math.PI/2
  meshes.push(cavity)
  
  const holeSpacingX = mountLength * 0.8
  const holeSpacingY = mountWidth * 0.75
  for (let i = 0; i < holeCount; i++) {
    const x = (i % 2 === 0 ? -1 : 1) * holeSpacingX/2
    const y = (i < 2 ? -1 : 1) * holeSpacingY/2
    const holeGeo = new THREE.CylinderGeometry(holeDiameter/2, holeDiameter/2, mountThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, y, 0)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  const ribCount = 4
  for (let i = 0; i < ribCount; i++) {
    const angle = (i/ribCount) * Math.PI * 2
    const x = Math.cos(angle) * insertDiameter/2
    const y = Math.sin(angle) * insertDiameter/2
    const ribLength = Math.sqrt((mountLength/2-x)**2 + (mountWidth/2-y)**2)
    const ribGeo = new THREE.BoxGeometry(ribThickness, ribLength, mountThickness*0.8)
    const ribMat = new THREE.MeshStandardMaterial({ color: 0x707070 })
    const rib = new THREE.Mesh(ribGeo, ribMat)
    rib.position.set(x/2, y/2, 0)
    rib.rotation.z = angle + Math.PI/2
    meshes.push(rib)
  }
  
  return meshes
}
`.trim()
    },

    oil_pan: {
        name: 'Oil Pan',
        description: 'Oil sump with drain plug and sensor bosses',
        requiredParams: ['length', 'width', 'depth'],
        generate: (p) => `
const panLength = ${p.length || 300}
const panWidth = ${p.width || 200}
const panDepth = ${p.depth || 80}
const wallThickness = ${p.wallThickness || 4}
const drainDiameter = ${p.drainDiameter || 20}
const sensorDiameter = ${p.sensorDiameter || 15}

function generateModel() {
  const meshes = []
  
  const outerGeo = new THREE.BoxGeometry(panLength, panWidth, panDepth)
  const outerMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
  const outer = new THREE.Mesh(outerGeo, outerMat)
  outer.position.z = -panDepth/2
  meshes.push(outer)
  
  const innerGeo = new THREE.BoxGeometry(
    panLength-wallThickness*2, 
    panWidth-wallThickness*2, 
    panDepth-wallThickness
  )
  const innerMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const inner = new THREE.Mesh(innerGeo, innerMat)
  inner.position.z = -panDepth/2 + wallThickness/2
  meshes.push(inner)
  
  const flangeGeo = new THREE.BoxGeometry(panLength+16, panWidth+16, wallThickness)
  const flangeMat = new THREE.MeshStandardMaterial({ color: 0x909090 })
  const flange = new THREE.Mesh(flangeGeo, flangeMat)
  flange.position.z = wallThickness/2
  meshes.push(flange)
  
  const boltCount = 12
  for (let i = 0; i < boltCount; i++) {
    const isXSide = i < boltCount/2
    const pos = (i % (boltCount/2)) / (boltCount/2 - 1)
    const x = isXSide ? (pos - 0.5) * panLength : (i % 2 === 0 ? 1 : -1) * panLength/2
    const y = isXSide ? (i < boltCount/4 ? 1 : -1) * panWidth/2 : (pos - 0.5) * panWidth
    const holeGeo = new THREE.CylinderGeometry(4, 4, wallThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, y, 0)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  const drainGeo = new THREE.CylinderGeometry(drainDiameter/2, drainDiameter/2, wallThickness*3, 16)
  const drainMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const drain = new THREE.Mesh(drainGeo, drainMat)
  drain.position.set(-panLength*0.3, 0, -panDepth)
  meshes.push(drain)
  
  const sensorGeo = new THREE.CylinderGeometry(sensorDiameter/2, sensorDiameter/2, wallThickness*2.5, 16)
  const sensorMat = new THREE.MeshStandardMaterial({ color: 0x707070 })
  const sensor = new THREE.Mesh(sensorGeo, sensorMat)
  sensor.position.set(panLength*0.35, panWidth*0.3, -panDepth/2)
  sensor.rotation.x = Math.PI/2
  meshes.push(sensor)
  
  return meshes
}
`.trim()
    },

    intake_manifold: {
        name: 'Intake Manifold',
        description: '4-cylinder intake manifold with plenum',
        requiredParams: ['plenumLength', 'runnerDiameter', 'runnerLength'],
        generate: (p) => `
const plenumLength = ${p.plenumLength || 150}
const plenumWidth = ${p.plenumWidth || 100}
const plenumHeight = ${p.plenumHeight || 80}
const runnerDiameter = ${p.runnerDiameter || 40}
const runnerLength = ${p.runnerLength || 180}
const runnerSpacing = ${p.runnerSpacing || 80}
const runnerCount = ${p.runnerCount || 4}

function generateModel() {
  const meshes = []
  
  const plenumGeo = new THREE.BoxGeometry(plenumLength, plenumWidth, plenumHeight)
  const plenumMat = new THREE.MeshStandardMaterial({ color: 0xB0B0B0 })
  const plenum = new THREE.Mesh(plenumGeo, plenumMat)
  meshes.push(plenum)
  
  for (let i = 0; i < runnerCount; i++) {
    const x = (i - (runnerCount-1)/2) * runnerSpacing
    const runnerGeo = new THREE.CylinderGeometry(
      runnerDiameter/2, 
      runnerDiameter/2, 
      runnerLength, 
      16
    )
    const runnerMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
    const runner = new THREE.Mesh(runnerGeo, runnerMat)
    runner.position.set(x, 0, -plenumHeight/2 - runnerLength/2)
    meshes.push(runner)
    
    const flangeGeo = new THREE.CylinderGeometry(
      runnerDiameter/2 + 8, 
      runnerDiameter/2 + 8, 
      6, 
      16
    )
    const flangeMat = new THREE.MeshStandardMaterial({ color: 0x909090 })
    const flange = new THREE.Mesh(flangeGeo, flangeMat)
    flange.position.set(x, 0, -plenumHeight/2 - runnerLength - 3)
    meshes.push(flange)
  }
  
  const throttleDiameter = 70
  const throttleGeo = new THREE.CylinderGeometry(throttleDiameter/2, throttleDiameter/2, 30, 32)
  const throttleMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const throttle = new THREE.Mesh(throttleGeo, throttleMat)
  throttle.position.set(0, plenumWidth/2 + 15, plenumHeight*0.2)
  throttle.rotation.x = Math.PI/2
  meshes.push(throttle)
  
  return meshes
}
`.trim()
    },

    throttle_body_adapter: {
        name: 'Throttle Body Adapter',
        description: 'Tapered adapter between different throttle diameters',
        requiredParams: ['diameterFrom', 'diameterTo', 'length'],
        generate: (p) => `
const diameterFrom = ${p.diameterFrom || 70}
const diameterTo = ${p.diameterTo || 80}
const adapterLength = ${p.length || 50}
const wallThickness = ${p.wallThickness || 4}
const boltCount = 4

function generateModel() {
  const meshes = []
  
  const outerGeo = new THREE.CylinderGeometry(
    diameterTo/2, 
    diameterFrom/2, 
    adapterLength, 
    32
  )
  const outerMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
  const outer = new THREE.Mesh(outerGeo, outerMat)
  meshes.push(outer)
  
  const innerGeo = new THREE.CylinderGeometry(
    diameterTo/2 - wallThickness, 
    diameterFrom/2 - wallThickness, 
    adapterLength + 2, 
    32
  )
  const innerMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const inner = new THREE.Mesh(innerGeo, innerMat)
  meshes.push(inner)
  
  const boltCircleFrom = diameterFrom + 15
  const boltCircleTo = diameterTo + 15
  
  for (let i = 0; i < boltCount; i++) {
    const angle = (i / boltCount) * Math.PI * 2
    
    const x1 = Math.cos(angle) * boltCircleFrom/2
    const z1 = Math.sin(angle) * boltCircleFrom/2
    const holeGeo1 = new THREE.CylinderGeometry(3, 3, wallThickness*2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole1 = new THREE.Mesh(holeGeo1, holeMat)
    hole1.position.set(x1, -adapterLength/2, z1)
    meshes.push(hole1)
    
    const x2 = Math.cos(angle) * boltCircleTo/2
    const z2 = Math.sin(angle) * boltCircleTo/2
    const hole2 = new THREE.Mesh(holeGeo1, holeMat)
    hole2.position.set(x2, adapterLength/2, z2)
    meshes.push(hole2)
  }
  
  return meshes
}
`.trim()
    },
    valve_cover: {
        name: 'Valve Cover',
        description: 'Rocker cover with sealing groove and filler neck',
        requiredParams: ['length', 'width', 'height'],
        generate: (p) => `
const coverLength = ${p.length || 400}
const coverWidth = ${p.width || 150}
const coverHeight = ${p.height || 60}
const wallThickness = ${p.wallThickness || 5}
const grooveWidth = ${p.grooveWidth || 6}
const grooveDepth = ${p.grooveDepth || 4}
const fillerDiameter = ${p.fillerDiameter || 50}

function generateModel() {
  const meshes = []
  
  const topGeo = new THREE.BoxGeometry(coverLength, coverWidth, wallThickness)
  const topMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
  const top = new THREE.Mesh(topGeo, topMat)
  top.position.z = coverHeight - wallThickness/2
  meshes.push(top)
  
  const sideGeo = new THREE.BoxGeometry(coverLength, wallThickness, coverHeight)
  const sideMat = new THREE.MeshStandardMaterial({ color: 0x909090 })
  const side1 = new THREE.Mesh(sideGeo, sideMat)
  side1.position.set(0, coverWidth/2 - wallThickness/2, coverHeight/2)
  meshes.push(side1)
  const side2 = new THREE.Mesh(sideGeo, sideMat)
  side2.position.set(0, -coverWidth/2 + wallThickness/2, coverHeight/2)
  meshes.push(side2)
  
  const endGeo = new THREE.BoxGeometry(wallThickness, coverWidth, coverHeight)
  const end1 = new THREE.Mesh(endGeo, sideMat)
  end1.position.set(coverLength/2 - wallThickness/2, 0, coverHeight/2)
  meshes.push(end1)
  const end2 = new THREE.Mesh(endGeo, sideMat)
  end2.position.set(-coverLength/2 + wallThickness/2, 0, coverHeight/2)
  meshes.push(end2)
  
  const grooveGeo = new THREE.BoxGeometry(coverLength-20, grooveWidth, grooveDepth)
  const grooveMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
  const groove1 = new THREE.Mesh(grooveGeo, grooveMat)
  groove1.position.set(0, coverWidth/2 - wallThickness - grooveWidth/2, -grooveDepth/2)
  meshes.push(groove1)
  const groove2 = new THREE.Mesh(grooveGeo, grooveMat)
  groove2.position.set(0, -coverWidth/2 + wallThickness + grooveWidth/2, -grooveDepth/2)
  meshes.push(groove2)
  
  const fillerGeo = new THREE.CylinderGeometry(fillerDiameter/2, fillerDiameter/2, 40, 32)
  const fillerMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const filler = new THREE.Mesh(fillerGeo, fillerMat)
  filler.position.set(coverLength*0.3, 0, coverHeight + 20)
  meshes.push(filler)
  
  const boltCount = 4
  for (let i = 0; i < boltCount; i++) {
    const x = (i % 2 === 0 ? -1 : 1) * coverLength * 0.4
    const y = (i < 2 ? -1 : 1) * coverWidth * 0.35
    const bossGeo = new THREE.CylinderGeometry(8, 8, coverHeight*0.4, 16)
    const bossMat = new THREE.MeshStandardMaterial({ color: 0x707070 })
    const boss = new THREE.Mesh(bossGeo, bossMat)
    boss.position.set(x, y, coverHeight*0.3)
    meshes.push(boss)
  }
  
  return meshes
}
`.trim()
    },

    alternator_bracket: {
        name: 'Alternator Bracket',
        description: 'L-shaped adjustable bracket',
        requiredParams: ['verticalHeight', 'horizontalLength', 'thickness'],
        generate: (p) => `
const verticalHeight = ${p.verticalHeight || p.height || 150}
const horizontalLength = ${p.horizontalLength || p.length || 120}
const bracketThickness = ${p.thickness || 10}
const slotLength = ${p.slotLength || 80}
const slotWidth = ${p.slotWidth || 12}

function generateModel() {
  const meshes = []
  
  const verticalGeo = new THREE.BoxGeometry(bracketThickness, 60, verticalHeight)
  const metalMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const vertical = new THREE.Mesh(verticalGeo, metalMat)
  vertical.position.set(0, -horizontalLength/2 + 30, verticalHeight/2)
  meshes.push(vertical)
  
  const horizontalGeo = new THREE.BoxGeometry(bracketThickness, horizontalLength, 50)
  const horizontal = new THREE.Mesh(horizontalGeo, metalMat)
  horizontal.position.set(0, 0, 25)
  meshes.push(horizontal)
  
  const ribGeo = new THREE.BoxGeometry(bracketThickness, 80, 80)
  const rib = new THREE.Mesh(ribGeo, metalMat)
  rib.position.set(0, -horizontalLength/2 + 40, verticalHeight/2 - 40)
  rib.rotation.z = Math.PI/4
  meshes.push(rib)
  
  const slotGeo = new THREE.BoxGeometry(bracketThickness+2, slotWidth, slotLength)
  const slotMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
  const slot = new THREE.Mesh(slotGeo, slotMat)
  slot.position.set(0, -horizontalLength/2 + 30, verticalHeight/2)
  meshes.push(slot)
  
  for (let i = 0; i < 3; i++) {
    const y = (i-1) * horizontalLength/3
    const holeGeo = new THREE.CylinderGeometry(5, 5, bracketThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x333333 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(0, y, 25)
    hole.rotation.y = Math.PI/2
    meshes.push(hole)
  }
  
  return meshes
}
`.trim()
    },
    oil_cooler: {
        name: 'Oil Cooler Housing',
        description: 'Oil cooler with internal fins and ports',
        requiredParams: ['length', 'width', 'height'],
        generate: (p) => `
const housingLength = ${p.length || 200}
const housingWidth = ${p.width || 100}
const housingHeight = ${p.height || 40}
const finCount = ${p.finCount || 10}
const finThickness = ${p.finThickness || 2}
const portDiameter = ${p.portDiameter || 20}

function generateModel() {
  const meshes = []
  
  const bodyGeo = new THREE.BoxGeometry(housingLength, housingWidth, housingHeight)
  const bodyMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
  const body = new THREE.Mesh(bodyGeo, bodyMat)
  meshes.push(body)
  
  const finSpacing = housingLength / (finCount + 1)
  for (let i = 0; i < finCount; i++) {
    const x = -housingLength/2 + (i+1) * finSpacing
    const finGeo = new THREE.BoxGeometry(finThickness, housingWidth-10, housingHeight-10)
    const finMat = new THREE.MeshStandardMaterial({ color: 0x909090 })
    const fin = new THREE.Mesh(finGeo, finMat)
    fin.position.x = x
    meshes.push(fin)
  }
  
  const inletGeo = new THREE.CylinderGeometry(portDiameter/2, portDiameter/2, 20, 16)
  const portMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const inlet = new THREE.Mesh(inletGeo, portMat)
  inlet.position.set(-housingLength/2 - 10, housingWidth/3, 0)
  inlet.rotation.z = Math.PI/2
  meshes.push(inlet)
  
  const outlet = new THREE.Mesh(inletGeo, portMat)
  outlet.position.set(housingLength/2 + 10, -housingWidth/3, 0)
  outlet.rotation.z = Math.PI/2
  meshes.push(outlet)
  
  for (let i = 0; i < 2; i++) {
    const x = (i === 0 ? -1 : 1) * housingLength * 0.4
    const tabGeo = new THREE.BoxGeometry(20, 30, 5)
    const tabMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
    const tab = new THREE.Mesh(tabGeo, tabMat)
    tab.position.set(x, 0, housingHeight/2 + 2.5)
    meshes.push(tab)
    
    const holeGeo = new THREE.CylinderGeometry(4, 4, 6, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, 0, housingHeight/2 + 2.5)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  return meshes
}
`.trim()
    },

    air_filter_box: {
        name: 'Air Filter Housing',
        description: 'Airbox with filter seat and intake tube',
        requiredParams: ['length', 'width', 'height'],
        generate: (p) => `
const boxLength = ${p.length || 250}
const boxWidth = ${p.width || 200}
const boxHeight = ${p.height || 150}
const wallThickness = ${p.wallThickness || 3}
const filterDiameter = ${p.filterDiameter || 150}
const tubeDiameter = ${p.tubeDiameter || 75}

function generateModel() {
  const meshes = []
  
  const outerGeo = new THREE.BoxGeometry(boxLength, boxWidth, boxHeight)
  const outerMat = new THREE.MeshStandardMaterial({ color: 0x303030 })
  const outer = new THREE.Mesh(outerGeo, outerMat)
  meshes.push(outer)
  
  const innerGeo = new THREE.BoxGeometry(
    boxLength - wallThickness*2,
    boxWidth - wallThickness*2,
    boxHeight - wallThickness*2
  )
  const innerMat = new THREE.MeshStandardMaterial({ color: 0x404040, side: THREE.BackSide })
  const inner = new THREE.Mesh(innerGeo, innerMat)
  meshes.push(inner)
  
  const seatGeo = new THREE.CylinderGeometry(filterDiameter/2, filterDiameter/2, wallThickness*2, 32)
  const seatMat = new THREE.MeshStandardMaterial({ color: 0x505050 })
  const seat = new THREE.Mesh(seatGeo, seatMat)
  seat.position.z = -boxHeight/2 + wallThickness
  seat.rotation.x = Math.PI/2
  meshes.push(seat)
  
  const tubeGeo = new THREE.CylinderGeometry(tubeDiameter/2, tubeDiameter/2, 100, 32)
  const tubeMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
  const tube = new THREE.Mesh(tubeGeo, tubeMat)
  tube.position.set(boxLength/2 + 50, 0, boxHeight/4)
  tube.rotation.z = Math.PI/2
  meshes.push(tube)
  
  for (let i = 0; i < 4; i++) {
    const x = (i % 2 === 0 ? -1 : 1) * boxLength/2 * 0.7
    const y = (i < 2 ? -1 : 1) * boxWidth/2 * 0.7
    const drainGeo = new THREE.CylinderGeometry(2.5, 2.5, wallThickness+2, 12)
    const drainMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const drain = new THREE.Mesh(drainGeo, drainMat)
    drain.position.set(x, y, -boxHeight/2)
    meshes.push(drain)
  }
  
  const lidGeo = new THREE.BoxGeometry(boxLength-10, boxWidth-10, wallThickness*2)
  const lidMat = new THREE.MeshStandardMaterial({ color: 0x353535 })
  const lid = new THREE.Mesh(lidGeo, lidMat)
  lid.position.z = boxHeight/2 + wallThickness
  meshes.push(lid)
  
  return meshes
}
`.trim()
    },

    turbo_spacer: {
        name: 'Turbo Spacer',
        description: 'Thermal spacer gasket with exhaust ports',
        requiredParams: ['length', 'width', 'thickness'],
        generate: (p) => `
const spacerLength = ${p.length || 180}
const spacerWidth = ${p.width || 120}
const spacerThickness = ${p.thickness || 10}
const portDiameter = ${p.portDiameter || 45}
const portSpacingX = ${p.portSpacingX || 140}
const portSpacingY = ${p.portSpacingY || 80}

function generateModel() {
  const meshes = []
  
  const baseGeo = new THREE.BoxGeometry(spacerLength, spacerWidth, spacerThickness)
  const baseMat = new THREE.MeshStandardMaterial({ color: 0xB0B0B0 })
  const base = new THREE.Mesh(baseGeo, baseMat)
  meshes.push(base)
  
  for (let ix = 0; ix < 2; ix++) {
    for (let iy = 0; iy < 2; iy++) {
      const x = (ix - 0.5) * portSpacingX
      const y = (iy - 0.5) * portSpacingY
      const portGeo = new THREE.CylinderGeometry(portDiameter/2, portDiameter/2, spacerThickness+2, 32)
      const portMat = new THREE.MeshStandardMaterial({ color: 0x333333 })
      const port = new THREE.Mesh(portGeo, portMat)
      port.position.set(x, y, 0)
      port.rotation.x = Math.PI/2
      meshes.push(port)
    }
  }
  
  const boltCount = 6
  for (let i = 0; i < boltCount; i++) {
    const angle = (i/boltCount) * Math.PI * 2
    const radius = Math.min(spacerLength, spacerWidth) * 0.45
    const x = Math.cos(angle) * radius
    const y = Math.sin(angle) * radius
    const holeGeo = new THREE.CylinderGeometry(5, 5, spacerThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, y, 0)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  for (let i = 0; i < 3; i++) {
    const grooveGeo = new THREE.BoxGeometry(spacerLength*0.8, 3, 2)
    const grooveMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
    const groove = new THREE.Mesh(grooveGeo, grooveMat)
    groove.position.set(0, (i-1)*spacerWidth*0.25, spacerThickness/2-1)
    meshes.push(groove)
  }
  
  return meshes
}
`.trim()
    },

    timing_cover: {
        name: 'Timing Belt Cover',
        description: 'Curved protective cover with inspection window',
        requiredParams: ['length', 'width'],
        generate: (p) => `
const coverLength = ${p.length || 250}
const coverWidth = ${p.width || 180}
const curveRadius = ${p.curveRadius || 150}
const wallThickness = ${p.wallThickness || 3}

function generateModel() {
  const meshes = []
  
  const segments = 20
  for (let i = 0; i < segments; i++) {
    const t = i / segments
    const angle = t * Math.PI/3 - Math.PI/6
    const z = Math.sin(angle) * curveRadius
    const x = Math.cos(angle) * curveRadius - curveRadius
    
    const segGeo = new THREE.BoxGeometry(coverLength/segments, coverWidth, wallThickness)
    const segMat = new THREE.MeshStandardMaterial({ color: 0x404040 })
    const seg = new THREE.Mesh(segGeo, segMat)
    seg.position.set(x, 0, z)
    seg.rotation.y = -angle
    meshes.push(seg)
  }
  
  const windowGeo = new THREE.BoxGeometry(80, 60, wallThickness+2)
  const windowMat = new THREE.MeshStandardMaterial({ color: 0xFFFFFF, transparent: true, opacity: 0.3 })
  const window = new THREE.Mesh(windowGeo, windowMat)
  window.position.set(-curveRadius*0.3, 0, curveRadius*0.2)
  meshes.push(window)
  
  for (let i = 0; i < 4; i++) {
    const angle = (i/4) * Math.PI/3 - Math.PI/6
    const z = Math.sin(angle) * curveRadius
    const x = Math.cos(angle) * curveRadius - curveRadius
    const y = (i % 2 === 0 ? -1 : 1) * coverWidth/2 * 0.8
    
    const tabGeo = new THREE.BoxGeometry(15, 20, 5)
    const tabMat = new THREE.MeshStandardMaterial({ color: 0x505050 })
    const tab = new THREE.Mesh(tabGeo, tabMat)
    tab.position.set(x, y, z)
    tab.rotation.y = -angle
    meshes.push(tab)
    
    const holeGeo = new THREE.CylinderGeometry(3, 3, 6, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, y, z)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  return meshes
}
`.trim()
    },

    fuel_rail: {
        name: 'Fuel Rail',
        description: 'Fuel rail with injector ports',
        requiredParams: ['length', 'diameter'],
        generate: (p) => `
const railLength = ${p.length || 400}
const outerDiameter = ${p.diameter || p.outerDiameter || 20}
const innerDiameter = ${p.innerDiameter || 16}
const injectorCount = ${p.injectorCount || 4}
const injectorDiameter = ${p.injectorDiameter || 14}

function generateModel() {
  const meshes = []
  
  const railGeo = new THREE.CylinderGeometry(outerDiameter/2, outerDiameter/2, railLength, 32)
  const railMat = new THREE.MeshStandardMaterial({ color: 0xC0C0C0 })
  const rail = new THREE.Mesh(railGeo, railMat)
  rail.rotation.z = Math.PI/2
  meshes.push(rail)
  
  const cavityGeo = new THREE.CylinderGeometry(innerDiameter/2, innerDiameter/2, railLength+2, 32)
  const cavityMat = new THREE.MeshStandardMaterial({ color: 0x333333, side: THREE.BackSide })
  const cavity = new THREE.Mesh(cavityGeo, cavityMat)
  cavity.rotation.z = Math.PI/2
  meshes.push(cavity)
  
  const injectorSpacing = railLength * 0.8 / (injectorCount - 1)
  for (let i = 0; i < injectorCount; i++) {
    const x = -railLength*0.4 + i * injectorSpacing
    const portGeo = new THREE.CylinderGeometry(injectorDiameter/2, injectorDiameter/2, 15, 16)
    const portMat = new THREE.MeshStandardMaterial({ color: 0xA0A0A0 })
    const port = new THREE.Mesh(portGeo, portMat)
    port.position.set(x, 0, -outerDiameter/2 - 7.5)
    port.rotation.x = Math.PI/6
    meshes.push(port)
  }
  
  const inletGeo = new THREE.CylinderGeometry(6, 6, 20, 16)
  const inletMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const inlet = new THREE.Mesh(inletGeo, inletMat)
  inlet.position.set(railLength/2 + 10, 0, 0)
  inlet.rotation.z = Math.PI/2
  meshes.push(inlet)
  
  const sensorGeo = new THREE.CylinderGeometry(5, 5, 15, 16)
  const sensorMat = new THREE.MeshStandardMaterial({ color: 0x606060 })
  const sensor = new THREE.Mesh(sensorGeo, sensorMat)
  sensor.position.set(-railLength/2 + 30, outerDiameter/2 + 7.5, 0)
  meshes.push(sensor)
  
  return meshes
}
`.trim()
    },

    bellhousing_adapter: {
        name: 'Bellhousing Adapter',
        description: 'Adapter plate between engine and transmission',
        requiredParams: ['diameter', 'thickness'],
        generate: (p) => `
const plateRadius = ${p.diameter ? p.diameter / 2 : 150}
const plateThickness = ${p.thickness || 15}
const pilotDiameter = ${p.pilotDiameter || 100}
const boltCircle1 = ${p.boltCircle1 || 280}
const boltCircle2 = ${p.boltCircle2 || 250}

function generateModel() {
  const meshes = []
  
  const plateGeo = new THREE.CylinderGeometry(plateRadius, plateRadius, plateThickness, 64)
  const plateMat = new THREE.MeshStandardMaterial({ color: 0x808080 })
  const plate = new THREE.Mesh(plateGeo, plateMat)
  meshes.push(plate)
  
  const pilotGeo = new THREE.CylinderGeometry(pilotDiameter/2, pilotDiameter/2, plateThickness+2, 32)
  const pilotMat = new THREE.MeshStandardMaterial({ color: 0x333333 })
  const pilot = new THREE.Mesh(pilotGeo, pilotMat)
  meshes.push(pilot)
  
  for (let i = 0; i < 8; i++) {
    const angle = (i/8) * Math.PI * 2
    const x = Math.cos(angle) * boltCircle1/2
    const z = Math.sin(angle) * boltCircle1/2
    const holeGeo = new THREE.CylinderGeometry(5, 5, plateThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, 0, z)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  for (let i = 0; i < 4; i++) {
    const angle = (i/4) * Math.PI * 2 + Math.PI/4
    const x = Math.cos(angle) * boltCircle2/2
    const z = Math.sin(angle) * boltCircle2/2
    const holeGeo = new THREE.CylinderGeometry(6, 6, plateThickness+2, 16)
    const holeMat = new THREE.MeshStandardMaterial({ color: 0x222222 })
    const hole = new THREE.Mesh(holeGeo, holeMat)
    hole.position.set(x, 0, z)
    hole.rotation.x = Math.PI/2
    meshes.push(hole)
  }
  
  return meshes
}
`.trim()
    }
}

export function selectTemplate(prompt: string): string | null {
    const lower = prompt.toLowerCase()

    if (/ellips.*implant|reservoir.*ellips|subcutaneous.*ellips/i.test(lower)) {
        return 'ellipsoid_implant'
    }
    if (/capsule.*hemisphere|drug.*capsule|hemisphere.*cap/i.test(lower)) {
        return 'hemispherical_capsule'
    }
    if (/stent.*zigzag|zigzag.*stent|vascular.*stent/i.test(lower)) {
        return 'zigzag_stent'
    }
    if (/soft.*actuator|pneumatic.*actuator|actuator.*chamber/i.test(lower)) {
        return 'soft_actuator'
    }
    if (/lattice|treillis|unit cell/i.test(lower)) {
        // Si type spécifique mentionné → advanced_lattice
        if (/(bcc|fcc|octet|kelvin|diamond|tetrahedral|body.centered|face.centered)/i.test(lower)) {
            return 'advanced_lattice'
        }
        return 'lattice_cube'
    }
    if (/braided.*stent|mesh.*stent|self.expanding.*stent|woven.*stent/i.test(lower)) {
        return 'braided_stent'
    }
    if (/mckibben|artificial.*muscle|pneumatic.*muscle|braided.*muscle/i.test(lower)) {
        return 'mckibben_actuator'
    }
    if (/caterpillar|earthworm|peristaltic.*robot|segmented.*robot|crawling.*robot/i.test(lower)) {
        return 'segmented_soft_robot'
    }
    if (/wrist.*splint|adaptive.*splint|splint.*wrist/i.test(lower)) {
        return 'wrist_splint'
    }
    if (/finger.*splint|splint.*finger|articulated.*splint/i.test(lower)) {
        return 'finger_splint'
    }
    if (/prosthetic.*socket|socket.*prosthetic|limb.*prosthetic/i.test(lower)) {
        return 'prosthetic_socket'
    }
    if (/voronoi|random.*cell.*pattern|porous.*scaffold/i.test(lower)) {
        return 'voronoi_scaffold'
    }
    if (/auxetic|re.entrant|negative.*poisson/i.test(lower)) {
        return 'auxetic_honeycomb'
    }
    if (/chiral.*metamaterial|rotating.*node/i.test(lower)) {
        return 'chiral_metamaterial'
    }
    if (/microfluidic|serpentine.*channel|mixing.*chip/i.test(lower)) {
        return 'microfluidic_chip'
    }
    if (/cell.*culture.*scaffold|octahedral.*cell/i.test(lower)) {
        return 'cell_culture_scaffold'
    }
    if (/compliant.*gripper|living.*hinge|parallel.*jaw/i.test(lower)) {
        return 'compliant_gripper'
    }
    if (/bistable|snap.through/i.test(lower)) {
        return 'bistable_mechanism'
    }
    if (/engine.*mount|motor.*mount|support.*moteur/i.test(lower)) {
        return 'engine_mount'
    }
    if (/oil.*pan|carter.*huile|sump/i.test(lower)) {
        return 'oil_pan'
    }
    if (/intake.*manifold|collecteur.*admission/i.test(lower)) {
        return 'intake_manifold'
    }
    if (/throttle.*adapter|adaptateur.*papillon/i.test(lower)) {
        return 'throttle_body_adapter'
    }
    if (/valve.*cover|cache.*culbuteur|rocker.*cover/i.test(lower)) {
        return 'valve_cover'
    }
    if (/alternator.*bracket|support.*alternateur/i.test(lower)) {
        return 'alternator_bracket'
    }
    if (/oil.*cooler|refroidisseur.*huile/i.test(lower)) {
        return 'oil_cooler'
    }
    if (/air.*filter.*box|boitier.*filtre/i.test(lower)) {
        return 'air_filter_box'
    }
    if (/turbo.*spacer|entretoise.*turbo/i.test(lower)) {
        return 'turbo_spacer'
    }
    if (/timing.*cover|cache.*distribution/i.test(lower)) {
        return 'timing_cover'
    }
    if (/fuel.*rail|rampe.*injection/i.test(lower)) {
        return 'fuel_rail'
    }
    if (/bellhousing|cloche.*adaptateur/i.test(lower)) {
        return 'bellhousing_adapter'
    }

    return null
}