<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { createRobot, createEnvironment, type RobotParts } from '../utils/robot-factory'
import { disposeGroup } from '../utils/three-utils'
import { useKnowledgeEffect } from '../composables/useKnowledgeEffect'
import { VISUAL_COLORS } from '../types/visuals'

const props = defineProps<{
  isAdminMode: boolean
  isLoading: boolean
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)

// Three.js State
let scene: THREE.Scene | undefined
let camera: THREE.PerspectiveCamera | undefined
let renderer: THREE.WebGLRenderer | undefined
let frameId: number

// Robot Instances
interface RobotInstance extends RobotParts {
  // Gesture State
  action: 'idle' | 'scan' | 'inspect'
  actionTimer: number
  // Target Rotations for smooth lerping
  leftArmTargetX: number
  leftArmTargetZ: number
  rightArmTargetX: number
  rightArmTargetZ: number
  // Holograms
  scanHologram: THREE.Group 
  inspectHologram: THREE.Mesh
  // Physics
  recoilImpulse: number
}
let robots: RobotInstance[] = []

// Smoke System
interface SmokeParticle {
  mesh: THREE.Mesh
  vel: THREE.Vector3
  life: number
  maxLife: number
}
let smokeParticles: SmokeParticle[] = []

// Interaction State
let mouseX = 0
let mouseY = 0

let isLaserActive = false
let laserDuration = 0

// Knowledge Effect Composable
const {
  knowledgeNodes,
  networkLines,
  generateKnowledgeBurst,
  animateUI,
  cleanupEffect,
  getNodeById
} = useKnowledgeEffect()
const isShaking = ref(false)

const createRobotInstance = (scene: THREE.Scene, x: number, y: number, z: number): RobotInstance => {
  const parts = createRobot(scene, x, y, z)
  
  // --- Create Holograms ---
  
  // 1. Scan Hologram Group (Left Hand)
  const scanGroup = new THREE.Group()
  scanGroup.position.set(0, -2.5, 0) // Tip at wrist/hand
  parts.leftArmGroup.add(scanGroup)

  // A. Scan Beam (The Cone)
  const scanGeo = new THREE.ConeGeometry(0.3, 1.5, 32, 1, true)
  scanGeo.translate(0, -0.75, 0) // Pivot at tip
  scanGeo.rotateX(-Math.PI / 2) // Point forward
  const scanMat = new THREE.MeshBasicMaterial({
    color: VISUAL_COLORS.CYAN,
    transparent: true,
    opacity: 0,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    wireframe: true
  })
  const scanBeam = new THREE.Mesh(scanGeo, scanMat)
  scanBeam.name = 'scanBeam'
  scanGroup.add(scanBeam)

  // B. The Crystal (Floating inside)
  const crystalGeo = new THREE.OctahedronGeometry(0.3, 0)
  const crystalMat = new THREE.MeshBasicMaterial({
    color: VISUAL_COLORS.WHITE, // White core
    transparent: true,
    opacity: 0,
    wireframe: true, // Tech crystal
    blending: THREE.AdditiveBlending
  })
  const crystal = new THREE.Mesh(crystalGeo, crystalMat)
  crystal.position.set(0, 0, 1.2) // Position inside the cone (Z-axis alignment)
  crystal.rotation.x = -Math.PI / 2 // Align with cone logic
  crystal.name = 'scanCrystal'
  scanGroup.add(crystal)

  // 2. Inspect Screen (Right Hand)
  const screenGeo = new THREE.PlaneGeometry(0.8, 0.5)
  const screenMat = new THREE.MeshBasicMaterial({
    color: VISUAL_COLORS.CYAN,
    transparent: true,
    opacity: 0,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  })
  const inspectHologram = new THREE.Mesh(screenGeo, screenMat)
  inspectHologram.position.set(0, -2.5, 0.5) // Floating above hand
  inspectHologram.rotation.x = -Math.PI / 4 // Angled up
  parts.rightArmGroup.add(inspectHologram)

  // Store original colors for Admin switching
  scanMat.userData = { originalColor: VISUAL_COLORS.CYAN }
  crystalMat.userData = { originalColor: VISUAL_COLORS.WHITE }
  screenMat.userData = { originalColor: VISUAL_COLORS.CYAN }

  return {
    ...parts,
    action: 'idle',
    actionTimer: 0,
    leftArmTargetX: 0,
    leftArmTargetZ: 0,
    rightArmTargetX: 0,
    rightArmTargetZ: 0,
    scanHologram: scanGroup,
    inspectHologram,
    recoilImpulse: 0
  }
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
    powerPreference: 'high-performance'
  })
  renderer.setSize(window.innerWidth, window.innerHeight)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))

  // Lighting
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.5)
  dirLight.position.set(5, 5, 5)
  scene.add(dirLight)
  const blueLight = new THREE.PointLight(VISUAL_COLORS.BLUE, 2, 50)
  blueLight.position.set(-5, 0, 5)
  scene.add(blueLight)
  const ambientLight = new THREE.AmbientLight(0x202020)
  scene.add(ambientLight)

  // --- Environment ---
  createEnvironment(scene)

  // --- Robot Assembly (Dual Robots) ---
  // Left Guard
  robots.push(createRobotInstance(scene, -7, -1, 0))
  // Right Guard
  robots.push(createRobotInstance(scene, 7, -1, 0))

  animate(0)
}

// Effects State
let muzzleGroups: THREE.Group[] = []
let laserGroups: THREE.Group[] = []
let impactGroups: THREE.Points[] = []

const cleanupLaserEffects = () => {
  if (!scene) return

  laserGroups.forEach((g) => {
    scene!.remove(g)
    disposeGroup(g)
  })
  laserGroups = []

  muzzleGroups.forEach((g) => {
    scene!.remove(g)
    disposeGroup(g)
  })
  muzzleGroups = []

  impactGroups.forEach((g) => {
    scene!.remove(g)
    disposeGroup(g)
  })
  impactGroups = []
}

const fireLaser = () => {
  if (robots.length === 0 || !camera || !scene) return

  // 0. Cleanup previous shots
  cleanupLaserEffects()

  // 1. Target Calculation
  const vector = new THREE.Vector3(mouseX, mouseY, 0.5)
  vector.unproject(camera)
  const dir = vector.sub(camera.position).normalize()
  const distance = (0 - camera.position.z) / dir.z
  const target = camera.position.clone().add(dir.multiplyScalar(distance))

  // 2. Trigger for EACH robot
  robots.forEach((robot) => {
    const visor = robot.visorMesh
    if (!visor) return

    // Trigger Mechanical Recoil
    robot.recoilImpulse = 0.6 // Sharp kickback

    const origin = new THREE.Vector3()
    visor.getWorldPosition(origin)

    // --- Smoke Eject ---
    for(let i=0; i<12; i++) {
        const size = 0.1 + Math.random() * 0.2
        const smokeGeo = new THREE.PlaneGeometry(size, size)
        smokeGeo.rotateZ(Math.random() * Math.PI)
        const smokeMat = new THREE.MeshBasicMaterial({
            color: 0xaaaaaa,
            transparent: true,
            opacity: 0.4 + Math.random() * 0.2,
            depthWrite: false,
            side: THREE.DoubleSide
        })
        const mesh = new THREE.Mesh(smokeGeo, smokeMat)
        mesh.position.copy(origin)
        // Offset slightly
        mesh.position.x += (Math.random() - 0.5) * 0.2
        mesh.position.y += (Math.random() - 0.5) * 0.2
        mesh.position.z += (Math.random() - 0.5) * 0.2
        
        // Upward velocity with drift
        const vel = new THREE.Vector3(
            (Math.random() - 0.5) * 0.02,
            0.03 + Math.random() * 0.03, // Up
            (Math.random() - 0.5) * 0.02
        )
        
        scene!.add(mesh) // 262
        smokeParticles.push({
            mesh,
            vel,
            life: 0,
            maxLife: 60 + Math.random() * 40
        })
    }

    // --- Muzzle Flash ---
    const muzzleGroup = new THREE.Group()
    muzzleGroup.position.copy(origin)
    scene!.add(muzzleGroup) // 274
    muzzleGroups.push(muzzleGroup)

    const flashGeo = new THREE.SphereGeometry(0.5, 8, 8)
    const flashMat = new THREE.MeshBasicMaterial({
      color: VISUAL_COLORS.WHITE,
      transparent: true,
      opacity: 1
    })
    muzzleGroup.add(new THREE.Mesh(flashGeo, flashMat))
    const flashRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.6, 0.05, 4, 16),
      new THREE.MeshBasicMaterial({ color: VISUAL_COLORS.CYAN, transparent: true })
    )
    flashRing.lookAt(target)
    muzzleGroup.add(flashRing)

    // --- The Beam ---
    const laserGroup = new THREE.Group()
    const distanceVec = new THREE.Vector3().subVectors(target, origin)
    const len = distanceVec.length()

    // Core
    const coreMat = new THREE.MeshBasicMaterial({
      color: VISUAL_COLORS.WHITE,
      transparent: true,
      opacity: 1,
      blending: THREE.AdditiveBlending
    })
    const coreGeo = new THREE.CylinderGeometry(0.04, 0.04, len, 8)
    coreGeo.rotateX(-Math.PI / 2)
    coreGeo.translate(0, 0, len / 2)
    laserGroup.add(new THREE.Mesh(coreGeo, coreMat))

    // Layers
    const layers = [
      { r: 0.15, op: 0.6 },
      { r: 0.3, op: 0.3 },
      { r: 0.6, op: 0.1 }
    ]
    layers.forEach((layer, idx) => {
      const mat = new THREE.MeshBasicMaterial({
        color: props.isAdminMode ? VISUAL_COLORS.RED : VISUAL_COLORS.LASER_GLOW,
        transparent: true,
        opacity: layer.op,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
      const geo = new THREE.CylinderGeometry(layer.r, layer.r * 1.2, len, 8)
      geo.rotateX(-Math.PI / 2)
      geo.translate(0, 0, len / 2)
      const mesh = new THREE.Mesh(geo, mat)
      mesh.name = `glow_${idx}`
      laserGroup.add(mesh)
    })

    laserGroup.position.copy(origin)
    laserGroup.lookAt(target)
    scene!.add(laserGroup)
    laserGroups.push(laserGroup)

    // --- Impact Sparks ---
    const pCount = 30
    const pGeo = new THREE.BufferGeometry()
    const pPos = new Float32Array(pCount * 3)
    const pVel: number[] = []
    for (let i = 0; i < pCount; i++) {
      pPos[i * 3] = target.x
      pPos[i * 3 + 1] = target.y
      pPos[i * 3 + 2] = target.z
      pVel.push(
        (Math.random() - 0.5) * 0.5,
        (Math.random() - 0.5) * 0.5,
        (Math.random() - 0.5) * 0.5
      )
    }
    pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
    pGeo.userData = { vel: pVel }
    const impactGroup = new THREE.Points(
      pGeo,
      new THREE.PointsMaterial({
        color: VISUAL_COLORS.GOLD,
        size: 0.15,
        transparent: true,
        blending: THREE.AdditiveBlending
      })
    )
    scene!.add(impactGroup)
    impactGroups.push(impactGroup)
  }) // End robots loop

  isLaserActive = true
  laserDuration = 15

  // 5. Knowledge/Neural UI Trigger
  generateKnowledgeBurst((mouseX + 1) * 50, (-mouseY + 1) * 50)
  animateUI()
}

function animate(time: number) {
  frameId = requestAnimationFrame(animate)
  if (!camera || !scene || !renderer) return

  time *= 0.001

  // 1. Calculate World Mouse Position (Z=4 plane approx 'focus')
  const vector = new THREE.Vector3(mouseX, mouseY, 0.5)
  vector.unproject(camera)
  const dir = vector.sub(camera.position).normalize()
  const distance = (4 - camera.position.z) / dir.z // Project to Z=4 (closer to robots) to feel more "in their face"
  const worldMouse = camera.position.clone().add(dir.multiplyScalar(distance))

  // Update Smoke Particles
  for (let i = smokeParticles.length - 1; i >= 0; i--) {
     const p = smokeParticles[i]
     if (!p) continue

     p.life++
     p.mesh.position.add(p.vel)
     p.mesh.lookAt(camera.position) // Billboard
     
     // Fade out
     const material = p.mesh.material as THREE.MeshBasicMaterial
     material.opacity = 0.6 * (1 - p.life / p.maxLife)
     
     if (p.life >= p.maxLife) {
        scene.remove(p.mesh)
        smokeParticles.splice(i, 1)
     }
  }

  // Animate ALL robots
  robots.forEach((robot, index) => {
    if (!robot.robotGroup) return

    const {
      robotGroup,
      headGroup,
      torsoGroup,
      satellitesGroup,
      leftArmGroup,
      rightArmGroup,
      coreReactor,
      scanHologram,
      inspectHologram
    } = robot

    // --- Orbital Patrol (Lissajous Curve) ---
    // A wide figure-8 knot that covers the screen but avoids collision via Z-depth
    const t = time * 0.2 + (index * Math.PI) // Phase shift of 180 degrees for second robot

    // Visual Range Config
    const ampX = 11  // Wide horizontal sweep
    const ampY = 4   // Vertical variation
    const ampZ = 4   // Depth (to pass behind/in-front)

    // The Path
    const targetX = Math.cos(t) * ampX
    const targetY = Math.sin(2 * t) * ampY - 1 // -1 vertical offset to center on screen
    const targetZ = Math.sin(t) * ampZ         // Z-depth ensures they don't collide at crossing

    // Smooth lerp to target (adds weight/inertia)
    // Note: Since 't' is continuous, direct assignment is fine, but lerp softens sudden jumps if t resets (it shouldn't)
    robotGroup.position.x = targetX
    robotGroup.position.y = targetY
    robotGroup.position.z = targetZ

    // Bank/Tilt into the turn (Dynamic flying effect)
    // We calculate the derivative (velocity) to know where it's going
    const velX = -Math.sin(t) * ampX
    // const velY = 2 * Math.cos(2 * t) * ampY
    
    // Tilt body based on horizontal velocity
    robotGroup.rotation.z = -velX * 0.05 
    // Slight forward lean
    robotGroup.rotation.x = 0.1

    // --- True 3D LookAt Logic ---
    if (headGroup) {
       // 1. Store current rotation
       const startQ = headGroup.quaternion.clone()
       
       // 2. Calculate target rotation
       // We force the head to look at worldMouse
       headGroup.lookAt(worldMouse)
       const targetQ = headGroup.quaternion.clone()
       
       // 3. Revert and Slerp
       headGroup.quaternion.copy(startQ)
       headGroup.quaternion.slerp(targetQ, 0.15) // 0.15 speed for snappy but smooth tracking
       
       // 4. Apply Mechanical Recoil (Additive PITCH UP)
       if (robot.recoilImpulse > 0.01) {
          headGroup.rotateX(-robot.recoilImpulse * 0.5) // Kick back (Negative X is usually up/back for head)
          robot.recoilImpulse *= 0.85 // Decay
       } else {
          robot.recoilImpulse = 0
       }
    }
    
    // --- Random Gestures State Machine ---
    let targetScanOpacity = 0
    let targetInspectOpacity = 0

    if (robot.action === 'idle') {
      // 0.5% chance to trigger an action per frame
      if (Math.random() < 0.005) {
         if (Math.random() > 0.5) {
           robot.action = 'scan'
           robot.actionTimer = 200 // Frames to hold
           // Left arm scans forward
           robot.leftArmTargetX = -1.5 
           robot.leftArmTargetZ = 0.5
           // Right arm relaxed
           robot.rightArmTargetX = 0
           robot.rightArmTargetZ = 0
         } else {
           robot.action = 'inspect'
           robot.actionTimer = 150
           // Both arms inspect
           robot.leftArmTargetX = -0.5
           robot.leftArmTargetZ = 0.3
           robot.rightArmTargetX = -0.5
           robot.rightArmTargetZ = -0.3
         }
      } else {
        // Idle sway
        robot.leftArmTargetX = Math.sin(time * 2) * 0.05
        robot.rightArmTargetX = Math.sin(time * 2 + 1) * 0.05
        robot.leftArmTargetZ = 0
        robot.rightArmTargetZ = 0
      }
    } else {
      robot.actionTimer--
      if (robot.action === 'scan') targetScanOpacity = 0.4
      if (robot.action === 'inspect') targetInspectOpacity = 0.7

      if (robot.actionTimer <= 0) {
        robot.action = 'idle'
      }
    }

    // Hologram Animation
    // Traverse scanGroup (Beam + Crystal)
    scanHologram.children.forEach((child) => {
      if (child instanceof THREE.Mesh) {
         // Lerp Opacity
         child.material.opacity += (targetScanOpacity - child.material.opacity) * 0.05
         
         // Rotate Beam
         if (child.name === 'scanBeam') {
           child.rotation.z += 0.05
         }
         // Rotate Crystal (Artifact) - Tumble on 3 axes
         if (child.name === 'scanCrystal') {
           child.rotation.x += 0.02
           child.rotation.y += 0.03
         }
      }
    })

    if (!Array.isArray(inspectHologram.material)) {
        inspectHologram.material.opacity += (targetInspectOpacity - inspectHologram.material.opacity) * 0.05
    }

    // Smoothly Lerp Arms to Target
    const lerpSpeed = 0.05
    if (leftArmGroup) {
       leftArmGroup.rotation.x += (robot.leftArmTargetX - leftArmGroup.rotation.x) * lerpSpeed
       leftArmGroup.rotation.z += (robot.leftArmTargetZ - leftArmGroup.rotation.z) * lerpSpeed
       // Add bobbing
       leftArmGroup.position.y = 0.5 + Math.sin(time * 2) * 0.05
    }
    if (rightArmGroup) {
       rightArmGroup.rotation.x += (robot.rightArmTargetX - rightArmGroup.rotation.x) * lerpSpeed
       rightArmGroup.rotation.z += (robot.rightArmTargetZ - rightArmGroup.rotation.z) * lerpSpeed
       // Add bobbing
       rightArmGroup.position.y = 0.5 + Math.sin(time * 2 + 1) * 0.05
    }

    // Satellites (Horizontal Spin)
    if (satellitesGroup) satellitesGroup.rotation.y = time * 0.5

    // Data Cores Animation
    if (satellitesGroup) {
      satellitesGroup.children.forEach((child) => {
        if (child instanceof THREE.Group && child.children.length === 3) {
          const inner = child.children[0]
          const shell = child.children[1]
          const ring = child.children[2]

          if (inner) {
            inner.rotation.y = time * 2
            inner.rotation.z = time
          }
          if (shell) {
            shell.rotation.x = time
            shell.rotation.y = -time * 0.5
          }
          if (ring) {
            ring.rotation.x = Math.PI / 2 + Math.sin(time) * 0.5
          }
        }
      })
    }

    if (coreReactor) {
      coreReactor.rotation.x = time * 2
      coreReactor.rotation.y = time * 3
    }

    // Head Tracking
    const targetRotY = mouseX * 0.6
    const targetRotX = -mouseY * 0.4
    if (headGroup) {
      headGroup.rotation.y += (targetRotY - headGroup.rotation.y) * 0.08
      headGroup.rotation.x += (targetRotX - headGroup.rotation.x) * 0.08
      if (torsoGroup) torsoGroup.rotation.y = headGroup.rotation.y * 0.2
    }
  })

  // Laser Effects
  if (isLaserActive) {
    if (laserDuration > 0) {
      // Animate Beams
      if (laserGroups.length > 0) {
        const baseJitter = 0.8 + Math.random() * 0.4
        laserGroups.forEach((lg, idx) => {
          // Update beam position if robot moved (though movement is slow)
          // Ideally we re-calculate position, but simpler to just jitter here
          lg.traverse((child) => {
            if (child.name.startsWith('glow_')) {
              const jitter = baseJitter + Math.random() * 0.2
              child.scale.set(jitter, 1, jitter)
            }
          })
          // Sync with visor position
          const robot = robots[idx]
          if (robot && robot.visorMesh) {
            lg.position.copy(
              new THREE.Vector3().setFromMatrixPosition(robot.visorMesh.matrixWorld)
            )
          }
        })
      }

      // Animate Muzzles
      if (muzzleGroups.length > 0) {
        muzzleGroups.forEach((mg, idx) => {
          if (laserDuration > 12) {
            const s = 1 + Math.random() * 0.5
            mg.scale.set(s, s, s)
            mg.rotation.z += 0.5
            const robot = robots[idx]
            if (robot && robot.visorMesh) {
              mg.position.copy(
                new THREE.Vector3().setFromMatrixPosition(robot.visorMesh.matrixWorld)
              )
            }
          } else {
            mg.visible = false
          }
        })
      }

      // Animate Impacts
      if (impactGroups.length > 0) {
        impactGroups.forEach((ig) => {
          const posAttribute = ig.geometry.attributes.position
          const vel = ig.geometry.userData.vel
          if (posAttribute) {
            for (let i = 0; i < posAttribute.count; i++) {
              posAttribute.setXYZ(
                i,
                posAttribute.getX(i) + vel[i * 3],
                posAttribute.getY(i) + vel[i * 3 + 1],
                posAttribute.getZ(i) + vel[i * 3 + 2]
              )
            }
            posAttribute.needsUpdate = true
          }
          if (!Array.isArray(ig.material)) ig.material.opacity *= 0.9
        })
      }

      laserDuration--
    } else {
      isLaserActive = false
      cleanupLaserEffects()
    }
  }

  renderer.render(scene, camera)
}

const onWindowResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
    // Scale is applied in init/animate logic individually now?
    // Actually scale was applied to robotGroup.
    // We should apply scale to ALL robots
    const scale = window.innerWidth < 1024 ? 0.7 : 1
    robots.forEach((r) => r.robotGroup.scale.set(scale, scale, scale))
  }
}
const onMouseMove = (e: MouseEvent) => {
  mouseX = (e.clientX / window.innerWidth) * 2 - 1
  mouseY = -(e.clientY / window.innerHeight) * 2 + 1
}
const onMouseDown = () => {
  fireLaser()
}

watch(
  () => props.isAdminMode,
  (isAdmin) => {
    robots.forEach((robot) => {
      robot.robotGroup.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          const mat = child.material
          // Check if we have the original color stored
          if (mat.userData && mat.userData.originalColor !== undefined) {
             const original = mat.userData.originalColor
             
             if (isAdmin) {
               // Admin Mode: Map colors to Red/Dark style
               if (original === VISUAL_COLORS.CYAN) {
                 mat.color.setHex(VISUAL_COLORS.RED)
               } else if (original === VISUAL_COLORS.BLUE) {
                 mat.color.setHex(VISUAL_COLORS.DARK_RED)
               } else {
                 // Keep White / Gold / Dark / Others as acts
                 mat.color.setHex(original)
               }
             } else {
               // Guest Mode: Revert to exact original
               mat.color.setHex(original)
             }
          }
        }
      })
    })
  }
)

onMounted(() => {
  initThreeJS()
  window.addEventListener('resize', onWindowResize)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mousedown', onMouseDown)
  onWindowResize()
})
onUnmounted(() => {
  window.removeEventListener('resize', onWindowResize)
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mousedown', onMouseDown)
  cancelAnimationFrame(frameId)
  cleanupEffect()
  cleanupLaserEffects()

  robots.forEach(r => disposeGroup(r.robotGroup))
  robots = []

  // Dispose Scene
  if (scene) disposeGroup(scene)
  if (renderer) renderer.dispose()
})
</script>

<template>
  <div
    class="absolute inset-0 z-0 pointer-events-none"
    :class="{ 'animate-impact-shake': isShaking }"
  >
    <canvas ref="canvasRef" class="w-full h-full opacity-90"></canvas>

    <!-- Knowledge / Neural Network Overlay -->
    <svg class="absolute inset-0 w-full h-full pointer-events-none overflow-visible">
      <!-- Neural Connections -->
      <line
        v-for="line in networkLines"
        :key="line.id"
        :x1="getNodeById(line.from)?.x + '%'"
        :y1="getNodeById(line.from)?.y + '%'"
        :x2="getNodeById(line.to)?.x + '%'"
        :y2="getNodeById(line.to)?.y + '%'"
        :stroke="isAdminMode ? '#FF0033' : 'cyan'"
        stroke-width="1"
        :stroke-opacity="line.opacity"
        stroke-linecap="round"
      />
    </svg>

    <!-- Floating Math Symbols -->
    <div
      v-for="node in knowledgeNodes"
      :key="node.id"
      class="absolute font-mono font-bold select-none pointer-events-none flex items-center justify-center transform -translate-x-1/2 -translate-y-1/2"
      :class="isAdminMode ? 'text-red-500' : 'text-cyan-400'"
      :style="{
        left: node.x + '%',
        top: node.y + '%',
        opacity: node.opacity,
        fontSize: 2.0 * node.scale + 'rem',
        textShadow: isAdminMode
          ? '0 0 10px rgba(255, 0, 51, 0.8)'
          : '0 0 10px rgba(0, 255, 255, 0.8)'
      }"
    >
      {{ node.text }}
    </div>

    <div
      class="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,#000000_100%)] opacity-30"
    ></div>

    <!-- Hidden Filter Defs (Global) -->
    <svg width="0" height="0" class="absolute">
      <defs>
        <filter id="glass-fracture">
          <feComponentTransfer in="SourceGraphic" result="bright">
            <feFuncR type="linear" slope="1.5" />
            <feFuncG type="linear" slope="1.5" />
            <feFuncB type="linear" slope="1.5" />
          </feComponentTransfer>
          <feGaussianBlur stdDeviation="0.5" result="blur" />
          <feComposite in="bright" in2="blur" operator="over" />
        </filter>
      </defs>
    </svg>
  </div>
</template>

<style scoped>
@keyframes impactShake {
  0% {
    transform: translate(0, 0);
  }
  10% {
    transform: translate(-10px, 10px) rotate(-1deg);
  }
  20% {
    transform: translate(10px, -10px) rotate(1deg);
  }
  30% {
    transform: translate(-8px, 6px);
  }
  50% {
    transform: translate(5px, -4px);
  }
  75% {
    transform: translate(-2px, 2px);
  }
  100% {
    transform: translate(0, 0);
  }
}
.animate-impact-shake {
  animation: impactShake 0.5s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}
</style>
