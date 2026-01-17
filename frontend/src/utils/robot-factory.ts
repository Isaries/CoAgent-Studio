import * as THREE from 'three'
import { VISUAL_COLORS } from '../types/visuals'

export interface RobotParts {
  robotGroup: THREE.Group
  headGroup: THREE.Group
  torsoGroup: THREE.Group
  leftArmGroup: THREE.Group
  rightArmGroup: THREE.Group
  coreReactor: THREE.Mesh
  visorMesh: THREE.Mesh
  satellitesGroup: THREE.Group
}

const createTechMaterial = (color: number, wireframe = false, opacity = 1) => {
  const mat = new THREE.MeshBasicMaterial({
    color: color,
    wireframe: wireframe,
    transparent: true,
    opacity: opacity,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending
  })
  mat.userData = { originalColor: color }
  return mat
}

const createSolidMaterial = (color: number) => {
  const mat = new THREE.MeshPhongMaterial({
    color: color,
    emissive: color,
    emissiveIntensity: 0.1,
    shininess: 120,
    flatShading: true
  })
  mat.userData = { originalColor: color }
  return mat
}

export const createRobot = (scene: THREE.Scene, x: number, y: number, z: number): RobotParts => {
  // --- Robot Assembly ---
  const robotGroup = new THREE.Group()
  robotGroup.position.set(x, y, z)
  scene.add(robotGroup)

  // 1. Torso: Industrial Frame
  const torsoGroup = new THREE.Group()
  robotGroup.add(torsoGroup)

  // Central Spine (Visible Skeleton)
  const spineGeo = new THREE.CylinderGeometry(0.15, 0.12, 1.2, 8)
  const spineMat = createSolidMaterial(VISUAL_COLORS.DARK)
  // Spine Segment 1 (Upper)
  const spine1 = new THREE.Mesh(spineGeo, spineMat)
  spine1.position.y = 0.6
  torsoGroup.add(spine1)
  // Spine Segment 2 (Lower)
  const spine2 = new THREE.Mesh(spineGeo, spineMat)
  spine2.position.y = -0.6
  torsoGroup.add(spine2)
  // Spine Glow
  const spineGlow = new THREE.Mesh(
    new THREE.CylinderGeometry(0.05, 0.05, 2.5, 6),
    createTechMaterial(VISUAL_COLORS.CYAN, false, 0.8)
  )
  torsoGroup.add(spineGlow)

  // Floating Armor Plating
  const plateGeo = new THREE.BoxGeometry(0.6, 1.0, 0.2)
  // Chest Left
  const lPlate = new THREE.Mesh(plateGeo, createTechMaterial(VISUAL_COLORS.BLUE, true))
  lPlate.position.set(-0.6, 0.6, 0.4)
  lPlate.rotation.z = 0.1
  lPlate.rotation.y = 0.3
  torsoGroup.add(lPlate)
  // Chest Right
  const rPlate = new THREE.Mesh(plateGeo, createTechMaterial(VISUAL_COLORS.BLUE, true))
  rPlate.position.set(0.6, 0.6, 0.4)
  rPlate.rotation.z = -0.1
  rPlate.rotation.y = -0.3
  torsoGroup.add(rPlate)
  // Stomach Guard
  const abPlate = new THREE.Mesh(
    new THREE.BoxGeometry(0.5, 0.6, 0.3),
    createTechMaterial(VISUAL_COLORS.CYAN, true)
  )
  abPlate.position.set(0, -0.4, 0.5)
  torsoGroup.add(abPlate)

  // Reactor (Deep in chest)
  const coreReactor = new THREE.Mesh(
    new THREE.DodecahedronGeometry(0.3),
    createTechMaterial(VISUAL_COLORS.CYAN, false, 0.9)
  )
  coreReactor.position.set(0, 0.6, 0)
  torsoGroup.add(coreReactor)

  // 2. Head: Layered Tactical Helmet
  const headGroup = new THREE.Group()
  headGroup.position.y = 1.6
  robotGroup.add(headGroup)

  // Neck Joint
  const neck = new THREE.Mesh(
    new THREE.SphereGeometry(0.25),
    createSolidMaterial(VISUAL_COLORS.DARK)
  )
  neck.position.y = -0.4
  headGroup.add(neck)

  // Helmet Core
  const helmCore = new THREE.Mesh(
    new THREE.BoxGeometry(0.8, 0.7, 0.8),
    createTechMaterial(VISUAL_COLORS.BLUE, true, 0.5)
  )
  headGroup.add(helmCore)

  // Ear/Comms Modules
  const earGeo = new THREE.BoxGeometry(0.2, 0.5, 0.5)
  const lEar = new THREE.Mesh(earGeo, createSolidMaterial(VISUAL_COLORS.DARK))
  lEar.position.set(-0.55, 0, 0)
  headGroup.add(lEar)
  const rEar = new THREE.Mesh(earGeo, createSolidMaterial(VISUAL_COLORS.DARK))
  rEar.position.set(0.55, 0, 0)
  headGroup.add(rEar)
  // Antennas
  const antGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.8)
  const lAnt = new THREE.Mesh(antGeo, createTechMaterial(VISUAL_COLORS.CYAN))
  lAnt.position.set(-0.55, 0.4, 0)
  headGroup.add(lAnt)
  const rAnt = new THREE.Mesh(antGeo, createTechMaterial(VISUAL_COLORS.CYAN))
  rAnt.position.set(0.55, 0.4, 0)
  headGroup.add(rAnt)

  // Faceplate
  const faceGeo = new THREE.BoxGeometry(0.85, 0.6, 0.1)
  const face = new THREE.Mesh(faceGeo, createTechMaterial(VISUAL_COLORS.BLUE))
  face.position.set(0, -0.1, 0.45)
  headGroup.add(face)

  // Eyes (The Visor + Pupils)
  const visorMesh = new THREE.Mesh(
    new THREE.BoxGeometry(0.9, 0.15, 0.05),
    createTechMaterial(VISUAL_COLORS.CYAN, false, 0.8)
  )
  visorMesh.position.set(0, 0.05, 0.52)
  headGroup.add(visorMesh)
  // Pupils (Focus Points)
  const eyeGeo = new THREE.SphereGeometry(0.06)
  const eyeMat = createTechMaterial(VISUAL_COLORS.LASER_GLOW, false, 1)
  const lEye = new THREE.Mesh(eyeGeo, eyeMat)
  lEye.position.set(-0.2, 0.05, 0.55)
  headGroup.add(lEye)
  const rEye = new THREE.Mesh(eyeGeo, eyeMat)
  rEye.position.set(0.2, 0.05, 0.55)
  headGroup.add(rEye)

  // 3. Arms: Articulated Mecha Claws
  const leftArmGroup = new THREE.Group()
  leftArmGroup.position.set(-1.2, 0.8, 0)
  robotGroup.add(leftArmGroup)
  const rightArmGroup = new THREE.Group()
  rightArmGroup.position.set(1.2, 0.8, 0)
  robotGroup.add(rightArmGroup)

  // Shoulder Joint
  const shoulderSphere = new THREE.Mesh(
    new THREE.SphereGeometry(0.35),
    createSolidMaterial(VISUAL_COLORS.DARK)
  )
  leftArmGroup.add(shoulderSphere.clone())
  rightArmGroup.add(shoulderSphere.clone())

  // Shoulder Armor
  const shoulderArmor = new THREE.Mesh(
    new THREE.OctahedronGeometry(0.5, 0),
    createTechMaterial(VISUAL_COLORS.BLUE, true)
  )
  shoulderArmor.position.y = 0.2
  leftArmGroup.add(shoulderArmor.clone())
  rightArmGroup.add(shoulderArmor.clone())

  const createMechaArm = (group: THREE.Group, isRight: boolean) => {
    // Upper Arm (Floating but aligned)
    const upperArm = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.8, 0.3),
      createTechMaterial(VISUAL_COLORS.BLUE, true, 0.5)
    )
    upperArm.position.y = -0.6
    group.add(upperArm)

    // Elbow Joint
    const elbow = new THREE.Mesh(
      new THREE.SphereGeometry(0.25),
      createSolidMaterial(VISUAL_COLORS.DARK)
    )
    elbow.position.y = -1.1
    group.add(elbow)

    // Forearm (Gauntlet)
    const forearm = new THREE.Mesh(
      new THREE.BoxGeometry(0.4, 0.7, 0.4),
      createTechMaterial(VISUAL_COLORS.BLUE, true)
    )
    forearm.position.y = -1.6
    group.add(forearm)

    // Wrist
    const wrist = new THREE.Mesh(
      new THREE.CylinderGeometry(0.15, 0.15, 0.2),
      createSolidMaterial(VISUAL_COLORS.DARK)
    )
    wrist.position.y = -2.0
    group.add(wrist)

    // Claw Hand (3 Fingers)
    const clawGroup = new THREE.Group()
    clawGroup.position.y = -2.1
    group.add(clawGroup)

    const thumb = new THREE.Mesh(
      new THREE.BoxGeometry(0.1, 0.4, 0.1),
      createTechMaterial(VISUAL_COLORS.CYAN)
    )
    thumb.position.set(isRight ? -0.15 : 0.15, -0.2, 0.1)
    thumb.rotation.z = isRight ? 0.5 : -0.5
    clawGroup.add(thumb)

    const f1 = new THREE.Mesh(
      new THREE.BoxGeometry(0.1, 0.5, 0.1),
      createTechMaterial(VISUAL_COLORS.CYAN)
    )
    f1.position.set(isRight ? 0.1 : -0.1, -0.3, 0.1)
    f1.rotation.z = isRight ? -0.2 : 0.2
    clawGroup.add(f1)

    const f2 = new THREE.Mesh(
      new THREE.BoxGeometry(0.1, 0.45, 0.1),
      createTechMaterial(VISUAL_COLORS.CYAN)
    )
    f2.position.set(0, -0.25, -0.15)
    f2.rotation.x = -0.5
    clawGroup.add(f2)
  }
  createMechaArm(leftArmGroup, false)
  createMechaArm(rightArmGroup, true)

  // 4. Thrusters (Floating Funnels)
  const funnelGeo = new THREE.ConeGeometry(0.2, 1.2, 4)
  const funnelMat = createTechMaterial(VISUAL_COLORS.CYAN, true, 0.8)

  // Left Funnels
  const lFunnelGroup = new THREE.Group()
  lFunnelGroup.position.set(-1.0, 1.5, -0.8)
  lFunnelGroup.rotation.z = 0.4
  for (let i = 0; i < 2; i++) {
    const f = new THREE.Mesh(funnelGeo, funnelMat)
    f.position.x = -i * 0.5
    f.position.y = -i * 0.2
    f.rotation.x = 0.2
    lFunnelGroup.add(f)
  }
  robotGroup.add(lFunnelGroup)

  // Right Funnels
  const rFunnelGroup = new THREE.Group()
  rFunnelGroup.position.set(1.0, 1.5, -0.8)
  rFunnelGroup.rotation.z = -0.4
  for (let i = 0; i < 2; i++) {
    const f = new THREE.Mesh(funnelGeo, funnelMat)
    f.position.x = i * 0.5
    f.position.y = -i * 0.2
    f.rotation.x = 0.2
    rFunnelGroup.add(f)
  }
  robotGroup.add(rFunnelGroup)

  // 5. Satellites & Atmosphere
  const satellitesGroup = new THREE.Group()
  robotGroup.add(satellitesGroup)
  satellitesGroup.rotation.z = 0.2
  satellitesGroup.rotation.x = 0.2
  const orbitRadius = 3.5

  // A. Main Satellites (3 Data Cores)
  const coreCount = 3
  for (let i = 0; i < coreCount; i++) {
    const angle = (i / coreCount) * Math.PI * 2
    const coreGroup = new THREE.Group()
    coreGroup.position.set(Math.cos(angle) * orbitRadius, 0, Math.sin(angle) * orbitRadius)
    satellitesGroup.add(coreGroup)

    // Inner Core
    const innerGeo = new THREE.OctahedronGeometry(0.15)
    const innerMat = createTechMaterial(VISUAL_COLORS.WHITE, false, 1)
    coreGroup.add(new THREE.Mesh(innerGeo, innerMat))
    // Outer Shell
    const shellGeo = new THREE.BoxGeometry(0.4, 0.4, 0.4)
    const shellMat = createTechMaterial(VISUAL_COLORS.CYAN, true, 0.5)
    coreGroup.add(new THREE.Mesh(shellGeo, shellMat))
    // Ring Scanner
    const scanRingGeo = new THREE.TorusGeometry(0.3, 0.01, 8, 32)
    const scanRingMat = createTechMaterial(VISUAL_COLORS.BLUE, false, 0.8)
    coreGroup.add(new THREE.Mesh(scanRingGeo, scanRingMat))
  }

  // B. Particle Swarm (Micro-Satellites)
  const swarmCount = 80
  const swarmGeo = new THREE.BufferGeometry()
  const swarmPos = new Float32Array(swarmCount * 3)
  for (let i = 0; i < swarmCount; i++) {
    const angle = (i / swarmCount) * Math.PI * 2
    const r = orbitRadius + (Math.random() - 0.5) * 1.5 // Band width
    const y = Math.sin(angle * 6) * 0.4 + (Math.random() - 0.5) * 0.5

    swarmPos[i * 3] = Math.cos(angle) * r
    swarmPos[i * 3 + 1] = y
    swarmPos[i * 3 + 2] = Math.sin(angle) * r
  }
  swarmGeo.setAttribute('position', new THREE.BufferAttribute(swarmPos, 3))
  const swarmMat = new THREE.PointsMaterial({
    color: VISUAL_COLORS.CYAN,
    size: 0.06,
    transparent: true,
    opacity: 0.6,
    blending: THREE.AdditiveBlending
  })
  satellitesGroup.add(new THREE.Points(swarmGeo, swarmMat))

  // C. Energy Rings (Holographic Orbits)
  const ringGeo = new THREE.TorusGeometry(orbitRadius + 0.2, 0.02, 16, 100)
  const ringMat = createTechMaterial(VISUAL_COLORS.BLUE, false, 0.1)

  const ring1 = new THREE.Mesh(ringGeo, ringMat)
  ring1.rotation.x = Math.PI / 2
  satellitesGroup.add(ring1)
  const ring2 = new THREE.Mesh(ringGeo, ringMat)
  ring2.rotation.set(1.8, 0.2, 0)
  satellitesGroup.add(ring2)
  const ring3 = new THREE.Mesh(ringGeo, ringMat)
  ring3.rotation.set(1.2, -0.4, 0)
  satellitesGroup.add(ring3)

  return {
    robotGroup,
    headGroup,
    torsoGroup,
    leftArmGroup,
    rightArmGroup,
    coreReactor,
    visorMesh,
    satellitesGroup
  }
}

export const createEnvironment = (scene: THREE.Scene): void => {
  // 6. Background Particles
  const pGeo = new THREE.BufferGeometry()
  const pCount = 300
  const pPos = new Float32Array(pCount * 3)
  for (let i = 0; i < pCount; i++) {
    pPos[i * 3] = (Math.random() - 0.5) * 40
    pPos[i * 3 + 1] = (Math.random() - 0.5) * 40
    pPos[i * 3 + 2] = (Math.random() - 0.5) * 20 - 10
  }
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
  scene.add(
    new THREE.Points(
      pGeo,
      new THREE.PointsMaterial({
        size: 0.05,
        color: VISUAL_COLORS.BLUE,
        transparent: true,
        opacity: 0.3
      })
    )
  )
}
