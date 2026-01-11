<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'

const props = defineProps<{
  isAdminMode: boolean
  isLoading: boolean
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

// Three.js State
let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let frameId: number

// Robot Parts
let robotGroup: THREE.Group
let headGroup: THREE.Group
let torsoGroup: THREE.Group
let satellitesGroup: THREE.Group
let leftArmGroup: THREE.Group
let rightArmGroup: THREE.Group
let coreReactor: THREE.Mesh
let visorMesh: THREE.Mesh
let laserGroup: THREE.Group | null = null

// Interaction State
let mouseX = 0
let mouseY = 0
 
let isLaserActive = false
let laserDuration = 0

// Knowledge Effect State
interface KnowledgeNode {
  id: number
  x: number // percent
  y: number // percent
  text: string
  vx: number
  vy: number
  opacity: number
  scale: number
}

interface NetworkLine {
  id: string
  from: number // Node ID
  to: number // Node ID
  opacity: number
}

const knowledgeNodes = ref<KnowledgeNode[]>([])
const networkLines = ref<NetworkLine[]>([])
let uiAnimFrame = 0
const isShaking = ref(false)

// Configuration
const COLOR_CYAN = 0x00FFFF
const COLOR_BLUE = 0x0066FF
const COLOR_RED = 0xFF0033
const COLOR_DARK = 0x111111
const COLOR_LASER_GLOW = 0x00FFFF // Ice Cyan
const COLOR_GOLD = 0xFFD700
const COLOR_WHITE = 0xFFFFFF

// --- Three.js Setup (Identical to previous) ---
const createTechMaterial = (color: number, wireframe = false, opacity = 1) => {
  return new THREE.MeshBasicMaterial({
    color: color,
    wireframe: wireframe,
    transparent: true,
    opacity: opacity,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending 
  })
}

const createSolidMaterial = (color: number) => {
  return new THREE.MeshPhongMaterial({
    color: color,
    emissive: color,
    emissiveIntensity: 0.1,
    shininess: 120,
    flatShading: true
  })
}

const initThreeJS = () => {
  if (!canvasRef.value) return

  // Scene
  scene = new THREE.Scene()
  scene.fog = new THREE.FogExp2(0x000000, 0.02)

  // Camera
  camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.1, 1000)
  camera.position.z = 14
  camera.position.y = 1

  // Renderer
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    alpha: true,
    antialias: true,
    powerPreference: "high-performance"
  })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  
  // Lighting
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.5)
  dirLight.position.set(5, 5, 5)
  scene.add(dirLight)
  const blueLight = new THREE.PointLight(COLOR_BLUE, 2, 50)
  blueLight.position.set(-5, 0, 5)
  scene.add(blueLight)
  const ambientLight = new THREE.AmbientLight(0x202020)
  scene.add(ambientLight)

  // --- Robot Assembly (Phase 2: Structured Mecha) ---
  robotGroup = new THREE.Group()
  robotGroup.position.set(6, -1, 0)
  scene.add(robotGroup)

  // 1. Torso: Industrial Frame
  torsoGroup = new THREE.Group()
  robotGroup.add(torsoGroup)
  
  // Central Spine (Visible Skeleton)
  const spineGeo = new THREE.CylinderGeometry(0.15, 0.12, 1.2, 8)
  const spineMat = createSolidMaterial(COLOR_DARK)
  // Spine Segment 1 (Upper)
  const spine1 = new THREE.Mesh(spineGeo, spineMat); spine1.position.y = 0.6; torsoGroup.add(spine1)
  // Spine Segment 2 (Lower)
  const spine2 = new THREE.Mesh(spineGeo, spineMat); spine2.position.y = -0.6; torsoGroup.add(spine2)
  // Spine Glow
  const spineGlow = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 2.5, 6), createTechMaterial(COLOR_CYAN, false, 0.8))
  torsoGroup.add(spineGlow)

  // Floating Armor Plating (Heavier, Mechanical)
  const plateGeo = new THREE.BoxGeometry(0.6, 1.0, 0.2)
  // Chest Left
  const lPlate = new THREE.Mesh(plateGeo, createTechMaterial(COLOR_BLUE, true)); lPlate.position.set(-0.6, 0.6, 0.4); lPlate.rotation.z = 0.1; lPlate.rotation.y = 0.3
  torsoGroup.add(lPlate)
  // Chest Right
  const rPlate = new THREE.Mesh(plateGeo, createTechMaterial(COLOR_BLUE, true)); rPlate.position.set(0.6, 0.6, 0.4); rPlate.rotation.z = -0.1; rPlate.rotation.y = -0.3
  torsoGroup.add(rPlate)
  // Stomach Guard
  const abPlate = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.6, 0.3), createTechMaterial(COLOR_CYAN, true)); abPlate.position.set(0, -0.4, 0.5)
  torsoGroup.add(abPlate)

  // Reactor (Deep in chest)
  coreReactor = new THREE.Mesh(new THREE.DodecahedronGeometry(0.3), createTechMaterial(COLOR_CYAN, false, 0.9))
  coreReactor.position.set(0, 0.6, 0)
  torsoGroup.add(coreReactor)

  // 2. Head: Layered Tactical Helmet
  headGroup = new THREE.Group()
  headGroup.position.y = 1.6
  robotGroup.add(headGroup)

  // Neck Joint
  const neck = new THREE.Mesh(new THREE.SphereGeometry(0.25), createSolidMaterial(COLOR_DARK)); neck.position.y = -0.4
  headGroup.add(neck)

  // Helmet Core
  const helmCore = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.7, 0.8), createTechMaterial(COLOR_BLUE, true, 0.5))
  headGroup.add(helmCore)
  
  // Ear/Comms Modules
  const earGeo = new THREE.BoxGeometry(0.2, 0.5, 0.5)
  const lEar = new THREE.Mesh(earGeo, createSolidMaterial(COLOR_DARK)); lEar.position.set(-0.55, 0, 0); headGroup.add(lEar)
  const rEar = new THREE.Mesh(earGeo, createSolidMaterial(COLOR_DARK)); rEar.position.set(0.55, 0, 0); headGroup.add(rEar)
  // Antennas
  const antGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.8)
  const lAnt = new THREE.Mesh(antGeo, createTechMaterial(COLOR_CYAN)); lAnt.position.set(-0.55, 0.4, 0); headGroup.add(lAnt)
  const rAnt = new THREE.Mesh(antGeo, createTechMaterial(COLOR_CYAN)); rAnt.position.set(0.55, 0.4, 0); headGroup.add(rAnt)

  // Faceplate
  const faceGeo = new THREE.BoxGeometry(0.85, 0.6, 0.1)
  const face = new THREE.Mesh(faceGeo, createTechMaterial(COLOR_BLUE)); face.position.set(0, -0.1, 0.45)
  headGroup.add(face)

  // Eyes (The Visor + Pupils)
  visorMesh = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.15, 0.05), createTechMaterial(COLOR_CYAN, false, 0.8))
  visorMesh.position.set(0, 0.05, 0.52)
  headGroup.add(visorMesh)
  // Pupils (Focus Points)
  const eyeGeo = new THREE.SphereGeometry(0.06); const eyeMat = createTechMaterial(COLOR_LASER_GLOW, false, 1)
  const lEye = new THREE.Mesh(eyeGeo, eyeMat); lEye.position.set(-0.2, 0.05, 0.55); headGroup.add(lEye)
  const rEye = new THREE.Mesh(eyeGeo, eyeMat); rEye.position.set(0.2, 0.05, 0.55); headGroup.add(rEye)

  // 3. Arms: Articulated Mecha Claws
  leftArmGroup = new THREE.Group(); leftArmGroup.position.set(-1.2, 0.8, 0); robotGroup.add(leftArmGroup)
  rightArmGroup = new THREE.Group(); rightArmGroup.position.set(1.2, 0.8, 0); robotGroup.add(rightArmGroup)

  // Shoulder Joint
  const shoulderSphere = new THREE.Mesh(new THREE.SphereGeometry(0.35), createSolidMaterial(COLOR_DARK))
  leftArmGroup.add(shoulderSphere.clone()); rightArmGroup.add(shoulderSphere.clone())
  
  // Shoulder Armor
  const shoulderArmor = new THREE.Mesh(new THREE.OctahedronGeometry(0.5, 0), createTechMaterial(COLOR_BLUE, true))
  shoulderArmor.position.y = 0.2
  leftArmGroup.add(shoulderArmor.clone()); rightArmGroup.add(shoulderArmor.clone())

  const createMechaArm = (group: THREE.Group, isRight: boolean) => {
      // Upper Arm (Floating but aligned)
      const upperArm = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.8, 0.3), createTechMaterial(COLOR_BLUE, true, 0.5))
      upperArm.position.y = -0.6
      group.add(upperArm)
      
      // Elbow Joint
      const elbow = new THREE.Mesh(new THREE.SphereGeometry(0.25), createSolidMaterial(COLOR_DARK))
      elbow.position.y = -1.1
      group.add(elbow)

      // Forearm (Gauntlet)
      const forearm = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.7, 0.4), createTechMaterial(COLOR_BLUE, true))
      forearm.position.y = -1.6
      group.add(forearm)

      // Wrist
      const wrist = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.15, 0.2), createSolidMaterial(COLOR_DARK))
      wrist.position.y = -2.0
      group.add(wrist)

      // Claw Hand (3 Fingers)
      const clawGroup = new THREE.Group()
      clawGroup.position.y = -2.1
      group.add(clawGroup)
      
      const thumb = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.4, 0.1), createTechMaterial(COLOR_CYAN))
      thumb.position.set(isRight ? -0.15 : 0.15, -0.2, 0.1); thumb.rotation.z = isRight ? 0.5 : -0.5
      clawGroup.add(thumb)
      
      const f1 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.5, 0.1), createTechMaterial(COLOR_CYAN))
      f1.position.set(isRight ? 0.1 : -0.1, -0.3, 0.1); f1.rotation.z = isRight ? -0.2 : 0.2
      clawGroup.add(f1)
       
      const f2 = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.45, 0.1), createTechMaterial(COLOR_CYAN))
      f2.position.set(0, -0.25, -0.15); f2.rotation.x = -0.5
      clawGroup.add(f2)
  }
  createMechaArm(leftArmGroup, false)
  createMechaArm(rightArmGroup, true)

  // 4. Thrusters (Floating Funnels)
  const funnelGeo = new THREE.ConeGeometry(0.2, 1.2, 4)
  const funnelMat = createTechMaterial(COLOR_CYAN, true, 0.8)
  
  // Left Funnels
  const lFunnelGroup = new THREE.Group(); lFunnelGroup.position.set(-1.0, 1.5, -0.8); lFunnelGroup.rotation.z = 0.4 
  for(let i=0; i<2; i++) {
     const f = new THREE.Mesh(funnelGeo, funnelMat)
     f.position.x = -i * 0.5; f.position.y = -i * 0.2; f.rotation.x = 0.2
     lFunnelGroup.add(f)
  }
  robotGroup.add(lFunnelGroup)

  // Right Funnels
  const rFunnelGroup = new THREE.Group(); rFunnelGroup.position.set(1.0, 1.5, -0.8); rFunnelGroup.rotation.z = -0.4
  for(let i=0; i<2; i++) {
     const f = new THREE.Mesh(funnelGeo, funnelMat)
     f.position.x = i * 0.5; f.position.y = -i * 0.2; f.rotation.x = 0.2
     rFunnelGroup.add(f)
  }
  robotGroup.add(rFunnelGroup)

  // 5. Satellites & Atmosphere (Phase 3+4)
  satellitesGroup = new THREE.Group(); robotGroup.add(satellitesGroup)
  satellitesGroup.rotation.z = 0.2; satellitesGroup.rotation.x = 0.2
  const orbitRadius = 3.5

  // A. Main Satellites (3 Data Cores)
  const coreCount = 3
  for(let i=0; i<coreCount; i++) {
    const angle = (i / coreCount) * Math.PI * 2
    const coreGroup = new THREE.Group()
    coreGroup.position.set(Math.cos(angle) * orbitRadius, 0, Math.sin(angle) * orbitRadius)
    satellitesGroup.add(coreGroup)

    // Inner Core
    const innerGeo = new THREE.OctahedronGeometry(0.15)
    const innerMat = createTechMaterial(COLOR_WHITE, false, 1)
    coreGroup.add(new THREE.Mesh(innerGeo, innerMat))
    // Outer Shell
    const shellGeo = new THREE.BoxGeometry(0.4, 0.4, 0.4)
    const shellMat = createTechMaterial(COLOR_CYAN, true, 0.5)
    coreGroup.add(new THREE.Mesh(shellGeo, shellMat))
    // Ring Scanner
    const scanRingGeo = new THREE.TorusGeometry(0.3, 0.01, 8, 32)
    const scanRingMat = createTechMaterial(COLOR_BLUE, false, 0.8)
    coreGroup.add(new THREE.Mesh(scanRingGeo, scanRingMat))
  }

  // B. Particle Swarm (Micro-Satellites)
  const swarmCount = 80
  const swarmGeo = new THREE.BufferGeometry()
  const swarmPos = new Float32Array(swarmCount * 3)
  for(let i=0; i<swarmCount; i++) {
      const angle = (i / swarmCount) * Math.PI * 2
      const r = orbitRadius + (Math.random() - 0.5) * 1.5 // Band width
      const y = Math.sin(angle * 6) * 0.4 + (Math.random() - 0.5) * 0.5
      
      swarmPos[i*3] = Math.cos(angle) * r
      swarmPos[i*3+1] = y
      swarmPos[i*3+2] = Math.sin(angle) * r
  }
  swarmGeo.setAttribute('position', new THREE.BufferAttribute(swarmPos, 3))
  const swarmMat = new THREE.PointsMaterial({ 
      color: COLOR_CYAN, size: 0.06, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending 
  })
  satellitesGroup.add(new THREE.Points(swarmGeo, swarmMat))

  // C. Energy Rings (Holographic Orbits) - Multi-crossed
  const ringGeo = new THREE.TorusGeometry(orbitRadius + 0.2, 0.02, 16, 100)
  const ringMat = createTechMaterial(COLOR_BLUE, false, 0.1)
  
  // Ring 1 (Flat)
  const ring1 = new THREE.Mesh(ringGeo, ringMat); ring1.rotation.x = Math.PI / 2; satellitesGroup.add(ring1)
  // Ring 2 (Tilted)
  const ring2 = new THREE.Mesh(ringGeo, ringMat); ring2.rotation.set(1.8, 0.2, 0); satellitesGroup.add(ring2)
  // Ring 3 (Crossed)
  const ring3 = new THREE.Mesh(ringGeo, ringMat); ring3.rotation.set(1.2, -0.4, 0); satellitesGroup.add(ring3)
  
  // 6. Background Particles (Dust)
  const pGeo = new THREE.BufferGeometry()
  const pCount = 300
  const pPos = new Float32Array(pCount * 3)
  for(let i=0; i<pCount; i++) {
    pPos[i*3] = (Math.random()-0.5) * 40
    pPos[i*3+1] = (Math.random()-0.5) * 40
    pPos[i*3+2] = (Math.random()-0.5) * 20 - 10
  }
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
  scene.add(new THREE.Points(pGeo, new THREE.PointsMaterial({ size: 0.05, color: COLOR_BLUE, transparent: true, opacity: 0.3 })))

  animate(0)
}

// --- KNOWLEDGE EFFECT LOGIC ---
const SYMBOLS_POOL = ['∑', '∫', 'π', 'λ', '√', '∞', '∇', '∂', 'Ω', 'μ', '{ }', '</>', 'f(x)', '≠', '≈']

const generateKnowledgeBurst = (xPercent: number, yPercent: number) => {
    const burstCount = 6 + Math.floor(Math.random() * 4) // 6-10 items
    const nodes: KnowledgeNode[] = []
    
    // Create Nodes (Symbols)
    for(let i=0; i<burstCount; i++) {
        const angle = Math.random() * Math.PI * 2
        const speed = 0.1 + Math.random() * 0.15
        nodes.push({
            id: Date.now() + i + Math.random(), // Add random to ensure unique IDs
            x: xPercent + (Math.random()-0.5)*1.5,
            y: yPercent + (Math.random()-0.5)*1.5,
            text: SYMBOLS_POOL[Math.floor(Math.random() * SYMBOLS_POOL.length)] || '∑',
            vx: Math.cos(angle) * speed,
            vy: Math.sin(angle) * speed - 0.1, // Float upward slightly
            opacity: 1,
            scale: 0.5 + Math.random() * 0.5
        })
    }
    knowledgeNodes.value.push(...nodes)

    // Create Connections (Neural Net) - Connect nearby nodes
    for(let i=0; i<nodes.length; i++) {
        const nI = nodes[i]
        for(let j=i+1; j<nodes.length; j++) {
            const nJ = nodes[j]
            if (nI && nJ && Math.random() > 0.5) { // 50% chance to connect
                 networkLines.value.push({
                     id: `${nI.id}-${nJ.id}`,
                     from: nI.id,
                     to: nJ.id,
                     opacity: 0.6
                 })
            }
        }
    }
}

const animateUI = () => {
    // Update Nodes
    knowledgeNodes.value.forEach(node => {
        node.x += node.vx
        node.y += node.vy
        node.opacity -= 0.006 // Much slower fade
        node.vy -= 0.002 // Gentler float
    })
    
    // Update Lines (inherit opacity from nodes) using average
    networkLines.value.forEach(line => {
        const n1 = knowledgeNodes.value.find(n => n.id === line.from)
        const n2 = knowledgeNodes.value.find(n => n.id === line.to)
        if (n1 && n2) {
            line.opacity = Math.min(n1.opacity, n2.opacity) * 0.5
        } else {
            line.opacity = 0
        }
    })

    // Cleanup
    knowledgeNodes.value = knowledgeNodes.value.filter(n => n.opacity > 0)
    networkLines.value = networkLines.value.filter(l => l.opacity > 0)

    if (knowledgeNodes.value.length > 0) {
        uiAnimFrame = requestAnimationFrame(animateUI)
    }
}

// Effects State
let muzzleGroup: THREE.Group | null = null
let impactGroup: THREE.Points | null = null

// Helper for template to avoid "implicit any" on `find`
const getNodeById = (id: number) => knowledgeNodes.value.find(n => n.id === id)

const fireLaser = () => {
    if (!visorMesh) return
    // 0. Cleanup
    if (laserGroup) { scene.remove(laserGroup); laserGroup = null }
    if (muzzleGroup) { scene.remove(muzzleGroup); muzzleGroup = null }
    if (impactGroup) { scene.remove(impactGroup); impactGroup = null }

    // 1. Math
    const origin = new THREE.Vector3(); visorMesh.getWorldPosition(origin)
    const vector = new THREE.Vector3(mouseX, mouseY, 0.5); vector.unproject(camera)
    const dir = vector.sub(camera.position).normalize()
    const distance = (0 - camera.position.z) / dir.z
    const target = camera.position.clone().add(dir.multiplyScalar(distance))

    // 2. Muzzle Flash (At Visor)
    muzzleGroup = new THREE.Group()
    muzzleGroup.position.copy(origin)
    scene.add(muzzleGroup)
    
    // Bright Core Flash
    const flashGeo = new THREE.SphereGeometry(0.5, 8, 8)
    const flashMat = new THREE.MeshBasicMaterial({ color: COLOR_WHITE, transparent: true, opacity: 1 })
    muzzleGroup.add(new THREE.Mesh(flashGeo, flashMat))
    // Energy Ring ring
    const flashRing = new THREE.Mesh(new THREE.TorusGeometry(0.6, 0.05, 4, 16), createTechMaterial(COLOR_CYAN))
    flashRing.lookAt(target)
    muzzleGroup.add(flashRing)


    
    // 3. The Beam (Ice Cyan Multi-Layer Gradient)
    laserGroup = new THREE.Group()
    const distanceVec = new THREE.Vector3().subVectors(target, origin)
    const len = distanceVec.length()
    
    // Core (Needle Sharp - White)
    const coreMat = new THREE.MeshBasicMaterial({ color: COLOR_WHITE, transparent: true, opacity: 1, blending: THREE.AdditiveBlending })
    const coreGeo = new THREE.CylinderGeometry(0.04, 0.04, len, 8); 
    coreGeo.rotateX(-Math.PI / 2); coreGeo.translate(0, 0, len / 2)
    laserGroup.add(new THREE.Mesh(coreGeo, coreMat))

    // Multi-Layer Glow (Soft Gradient Bloom)
    const layers = [
       { r: 0.15, op: 0.6 }, // Inner High Energy
       { r: 0.3,  op: 0.3 }, // Mid Glow
       { r: 0.6,  op: 0.1 }  // Outer Halo
    ]

    layers.forEach((layer, idx) => {
        const mat = new THREE.MeshBasicMaterial({ 
            color: props.isAdminMode ? COLOR_RED : COLOR_LASER_GLOW, 
            transparent: true, 
            opacity: layer.op, 
            blending: THREE.AdditiveBlending,
            depthWrite: false // Important for layering transparency
        })
        const geo = new THREE.CylinderGeometry(layer.r, layer.r * 1.2, len, 8); // Slight taper
        geo.rotateX(-Math.PI / 2); geo.translate(0, 0, len / 2)
        const mesh = new THREE.Mesh(geo, mat)
        mesh.name = `glow_${idx}`
        laserGroup!.add(mesh)
    })
    
    laserGroup.position.copy(origin); laserGroup.lookAt(target); scene.add(laserGroup)
    
    // 4. Impact Sparks (At Hit)
    const pCount = 30
    const pGeo = new THREE.BufferGeometry()
    const pPos = new Float32Array(pCount * 3)
    const pVel: number[] = [] // Store velocities in JS array for simple anim
    for(let i=0; i<pCount; i++) {
        pPos[i*3] = target.x; pPos[i*3+1] = target.y; pPos[i*3+2] = target.z
        pVel.push((Math.random()-0.5)*0.5, (Math.random()-0.5)*0.5, (Math.random()-0.5)*0.5)
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
    pGeo.userData = { vel: pVel } // Attach data
    impactGroup = new THREE.Points(pGeo, new THREE.PointsMaterial({ color: COLOR_GOLD, size: 0.15, transparent: true, blending: THREE.AdditiveBlending }))
    scene.add(impactGroup)

    isLaserActive = true; laserDuration = 50 // Longer duration

    // 5. Knowledge/Neural UI Trigger
    generateKnowledgeBurst((mouseX + 1) * 50, (-mouseY + 1) * 50)
    if (knowledgeNodes.value.length < 20) animateUI() // Start loop if not running excessively
}

function animate(time: number) {
  frameId = requestAnimationFrame(animate)
  time *= 0.001

  // Robot Patrol Movement (Figure-8)
  // Full-screen range: X ~ [-10, 10], Y ~ [-5, 5]
  // Slow, elegant flight path
  const patrolSpeed = 0.5
  robotGroup.position.x = Math.cos(time * patrolSpeed) * 9
  robotGroup.position.y = Math.sin(time * patrolSpeed * 2) * 4 - 1 // -1 is vertical offset
  
  const hover = Math.sin(time * 2) * 0.1
  // Add hover to the calculated position
  robotGroup.position.y += hover
  
  // Satellites (Horizontal Spin)
  satellitesGroup.rotation.y = time * 0.5 
  
  // Data Cores Animation (Local Spin for all 3)
  // [0] is coreGroup. Children: [0]inner, [1]shell, [2]ring
  satellitesGroup.children.forEach(child => {
      if (child instanceof THREE.Group && child.children.length === 3) {
          const inner = child.children[0];
          const shell = child.children[1];
          const ring = child.children[2];
          
          if (inner) { inner.rotation.y = time * 2; inner.rotation.z = time }
          if (shell) { shell.rotation.x = time; shell.rotation.y = -time * 0.5 }
          if (ring) { ring.rotation.x = Math.PI / 2 + Math.sin(time) * 0.5 }
      }
  })
  
  leftArmGroup.position.y = 0.5 - hover; rightArmGroup.position.y = 0.5 - hover
  coreReactor.rotation.x = time * 2; coreReactor.rotation.y = time * 3


  const targetRotY = mouseX * 0.6; const targetRotX = -mouseY * 0.4
  headGroup.rotation.y += (targetRotY - headGroup.rotation.y) * 0.08
  headGroup.rotation.x += (targetRotX - headGroup.rotation.x) * 0.08
  torsoGroup.rotation.y = headGroup.rotation.y * 0.2

  // Laser
  // Laser Effects Animation
  if (isLaserActive) {
    if (laserDuration > 0) {
      // Beam Pulse (Multi-Layer)
      if (laserGroup) {
          const baseJitter = 0.8 + Math.random() * 0.4
          laserGroup.traverse((child) => {
              if (child.name.startsWith("glow_")) {
                  // Outer layers jitter more
                  const jitter = baseJitter + Math.random() * 0.2
                  child.scale.set(jitter, 1, jitter)
              }
          })
          laserGroup.position.copy(new THREE.Vector3().setFromMatrixPosition(visorMesh.matrixWorld)) 
      }
      
      // Muzzle Flash Logic (Ephemeral: only visible for 5 frames)
      // Total duration is 50, so if laserDuration < 45, hide it.
      if (muzzleGroup) {
          if (laserDuration > 45) {
             const s = 1 + Math.random() * 0.5
             muzzleGroup.scale.set(s, s, s)
             muzzleGroup.rotation.z += 0.5
             // Keep muzzle attached to head
             muzzleGroup.position.copy(new THREE.Vector3().setFromMatrixPosition(visorMesh.matrixWorld))
          } else {
             scene.remove(muzzleGroup)
             muzzleGroup = null
          }
      }

      // Impact Sparks Explosion
      if (impactGroup) {
          const posAttribute = impactGroup.geometry.attributes.position
          const vel = impactGroup.geometry.userData.vel
          if (posAttribute) {
            for(let i=0; i < posAttribute.count; i++) {
                posAttribute.setXYZ(i, 
                    posAttribute.getX(i) + vel[i*3],
                    posAttribute.getY(i) + vel[i*3+1],
                    posAttribute.getZ(i) + vel[i*3+2]
                )
            }
            posAttribute.needsUpdate = true
          }
          if (!Array.isArray(impactGroup.material)) impactGroup.material.opacity *= 0.9 // Fade out
      }
      
      laserDuration--
    } else {
      isLaserActive = false
      if (laserGroup) { scene.remove(laserGroup); laserGroup = null }
      if (muzzleGroup) { scene.remove(muzzleGroup); muzzleGroup = null }
      if (impactGroup) { scene.remove(impactGroup); impactGroup = null }
    }
  } else {
      // Auto-fire logic
      if (Math.random() > 0.99) { // Rare auto fire
         // fireLaser() // Optional: Enable if you want auto-play
      }
  }
  renderer.render(scene, camera)
}

const onWindowResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
    if (window.innerWidth < 1024) { robotGroup.scale.set(0.7, 0.7, 0.7) } 
    else { robotGroup.scale.set(1, 1, 1) }
  }
}
const onMouseMove = (e: MouseEvent) => { mouseX = (e.clientX / window.innerWidth) * 2 - 1; mouseY = -(e.clientY / window.innerHeight) * 2 + 1 }
const onMouseDown = () => { fireLaser() }

watch(() => props.isAdminMode, (newVal) => {
  const targetColor = newVal ? COLOR_RED : COLOR_CYAN
   robotGroup.traverse((child) => {
     if (child instanceof THREE.Mesh) {
         const mat = child.material
         if (!Array.isArray(mat) && mat instanceof THREE.MeshBasicMaterial) {
            if (mat.color.getHex() !== COLOR_GOLD) {
                mat.color.setHex(targetColor)
            }
         }
     }
  })
})

onMounted(() => { 
    initThreeJS(); 
    window.addEventListener('resize', onWindowResize); 
    window.addEventListener('mousemove', onMouseMove); 
    window.addEventListener('mousedown', onMouseDown);
    onWindowResize() 
})
onUnmounted(() => { 
    window.removeEventListener('resize', onWindowResize); 
    window.removeEventListener('mousemove', onMouseMove); 
    window.removeEventListener('mousedown', onMouseDown);
    cancelAnimationFrame(frameId);
    cancelAnimationFrame(uiAnimFrame) 
    if (renderer) renderer.dispose() 
})
</script>

<template>
  <div class="absolute inset-0 z-0 pointer-events-none" :class="{ 'animate-impact-shake': isShaking }">
    <canvas ref="canvasRef" class="w-full h-full opacity-90"></canvas>
    
    <!-- Knowledge / Neural Network Overlay -->
    <svg class="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
      
       <!-- Neural Connections -->
       <line v-for="line in networkLines" :key="line.id"
             :x1="getNodeById(line.from)?.x + '%'"
             :y1="getNodeById(line.from)?.y + '%'"
             :x2="getNodeById(line.to)?.x + '%'"
             :y2="getNodeById(line.to)?.y + '%'"
             stroke="cyan"
             stroke-width="1"
             :stroke-opacity="line.opacity"
             stroke-linecap="round"
       />
    </svg>
    
    <!-- Floating Math Symbols -->
    <div v-for="node in knowledgeNodes" :key="node.id"
         class="absolute text-cyan-400 font-mono font-bold select-none pointer-events-none flex items-center justify-center transform -translate-x-1/2 -translate-y-1/2"
         :style="{ 
            left: node.x + '%', 
            top: node.y + '%', 
            opacity: node.opacity,
            fontSize: (1.2 * node.scale) + 'rem',
            textShadow: '0 0 10px rgba(0, 255, 255, 0.8)'
         }">
         {{ node.text }}
    </div>

    <div class="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#000000_100%)] opacity-30"></div>
    
    <!-- Hidden Filter Defs (Global) -->
    <svg width="0" height="0" class="absolute">
      <defs>
        <filter id="glass-fracture">
           <!-- Brighten edges -->
           <feComponentTransfer in="SourceGraphic" result="bright">
              <feFuncR type="linear" slope="1.5" />
              <feFuncG type="linear" slope="1.5" />
              <feFuncB type="linear" slope="1.5" />
           </feComponentTransfer>
           <!-- Inner Glow -->
           <feGaussianBlur stdDeviation="0.5" result="blur"/>
           <feComposite in="bright" in2="blur" operator="over" />
        </filter>
      </defs>
    </svg>
  </div>
</template>

<style scoped>
@keyframes impactShake {
  0% { transform: translate(0, 0); }
  10% { transform: translate(-10px, 10px) rotate(-1deg); }
  20% { transform: translate(10px, -10px) rotate(1deg); }
  30% { transform: translate(-8px, 6px); }
  50% { transform: translate(5px, -4px); }
  75% { transform: translate(-2px, 2px); }
  100% { transform: translate(0, 0); }
}
.animate-impact-shake {
  animation: impactShake 0.5s cubic-bezier(.36,.07,.19,.97) both;
}
</style>
