<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { createCyberDroid } from '../utils/robot-factory'
import { disposeGroup } from '../utils/three-utils'
import { useKnowledgeEffect } from '../composables/useKnowledgeEffect'
import { VISUAL_COLORS } from '../types/visuals'

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

  // --- Robot Assembly via Factory ---
  const parts = createCyberDroid(scene)
  robotGroup = parts.robotGroup
  headGroup = parts.headGroup
  torsoGroup = parts.torsoGroup
  satellitesGroup = parts.satellitesGroup
  leftArmGroup = parts.leftArmGroup
  rightArmGroup = parts.rightArmGroup
  coreReactor = parts.coreReactor
  visorMesh = parts.visorMesh

  animate(0)
}

// Effects State
let muzzleGroup: THREE.Group | null = null
let impactGroup: THREE.Points | null = null

const fireLaser = () => {
  if (!visorMesh) return
  // 0. Cleanup (Fix Memory Leaks)
  if (laserGroup) {
    scene.remove(laserGroup)
    disposeGroup(laserGroup)
    laserGroup = null
  }
  if (muzzleGroup) {
    scene.remove(muzzleGroup)
    disposeGroup(muzzleGroup)
    muzzleGroup = null
  }
  if (impactGroup) {
    scene.remove(impactGroup)
    disposeGroup(impactGroup)
    impactGroup = null
  }

  // 1. Math
  const origin = new THREE.Vector3()
  visorMesh.getWorldPosition(origin)
  const vector = new THREE.Vector3(mouseX, mouseY, 0.5)
  vector.unproject(camera)
  const dir = vector.sub(camera.position).normalize()
  const distance = (0 - camera.position.z) / dir.z
  const target = camera.position.clone().add(dir.multiplyScalar(distance))

  // 2. Muzzle Flash (At Visor)
  muzzleGroup = new THREE.Group()
  muzzleGroup.position.copy(origin)
  scene.add(muzzleGroup)

  // Bright Core Flash
  const flashGeo = new THREE.SphereGeometry(0.5, 8, 8)
  const flashMat = new THREE.MeshBasicMaterial({
    color: VISUAL_COLORS.WHITE,
    transparent: true,
    opacity: 1
  })
  muzzleGroup.add(new THREE.Mesh(flashGeo, flashMat))
  // Energy Ring ring
  const flashRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.6, 0.05, 4, 16),
    new THREE.MeshBasicMaterial({ color: VISUAL_COLORS.CYAN, transparent: true })
  )
  flashRing.lookAt(target)
  muzzleGroup.add(flashRing)

  // 3. The Beam (Ice Cyan Multi-Layer Gradient)
  laserGroup = new THREE.Group()
  const distanceVec = new THREE.Vector3().subVectors(target, origin)
  const len = distanceVec.length()

  // Core (Needle Sharp - White)
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

  // Multi-Layer Glow (Soft Gradient Bloom)
  const layers = [
    { r: 0.15, op: 0.6 }, // Inner High Energy
    { r: 0.3, op: 0.3 }, // Mid Glow
    { r: 0.6, op: 0.1 } // Outer Halo
  ]

  layers.forEach((layer, idx) => {
    const mat = new THREE.MeshBasicMaterial({
      color: props.isAdminMode ? VISUAL_COLORS.RED : VISUAL_COLORS.LASER_GLOW,
      transparent: true,
      opacity: layer.op,
      blending: THREE.AdditiveBlending,
      depthWrite: false // Important for layering transparency
    })
    const geo = new THREE.CylinderGeometry(layer.r, layer.r * 1.2, len, 8) // Slight taper
    geo.rotateX(-Math.PI / 2)
    geo.translate(0, 0, len / 2)
    const mesh = new THREE.Mesh(geo, mat)
    mesh.name = `glow_${idx}`
    laserGroup!.add(mesh)
  })

  laserGroup.position.copy(origin)
  laserGroup.lookAt(target)
  scene.add(laserGroup)

  // 4. Impact Sparks (At Hit)
  const pCount = 30
  const pGeo = new THREE.BufferGeometry()
  const pPos = new Float32Array(pCount * 3)
  const pVel: number[] = [] // Store velocities in JS array for simple anim
  for (let i = 0; i < pCount; i++) {
    pPos[i * 3] = target.x
    pPos[i * 3 + 1] = target.y
    pPos[i * 3 + 2] = target.z
    pVel.push((Math.random() - 0.5) * 0.5, (Math.random() - 0.5) * 0.5, (Math.random() - 0.5) * 0.5)
  }
  pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3))
  pGeo.userData = { vel: pVel } // Attach data
  impactGroup = new THREE.Points(
    pGeo,
    new THREE.PointsMaterial({
      color: VISUAL_COLORS.GOLD,
      size: 0.15,
      transparent: true,
      blending: THREE.AdditiveBlending
    })
  )
  scene.add(impactGroup)

  isLaserActive = true
  laserDuration = 15 // Short pulse

  // 5. Knowledge/Neural UI Trigger
  generateKnowledgeBurst((mouseX + 1) * 50, (-mouseY + 1) * 50)
  // animateUI is handled by composable, but we need to ensure it starts if loop stopped
  // The composable handles loop internally if we call animateUI once.
  // But better to check if loop is running references logic in composable?
  // Actually the composable checks length > 0 at end of frame.
  // So if length was 0, loop stopped. We need to restart it.
  // Let's call it once.
  animateUI()
}

function animate(time: number) {
  frameId = requestAnimationFrame(animate)
  time *= 0.001

  if (!robotGroup) return

  // Robot Patrol Movement (Figure-8)
  const patrolSpeed = 0.5
  robotGroup.position.x = Math.cos(time * patrolSpeed) * 9
  robotGroup.position.y = Math.sin(time * patrolSpeed * 2) * 4 - 1 // -1 is vertical offset

  const hover = Math.sin(time * 2) * 0.1
  robotGroup.position.y += hover

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

  if (leftArmGroup) leftArmGroup.position.y = 0.5 - hover
  if (rightArmGroup) rightArmGroup.position.y = 0.5 - hover
  if (coreReactor) {
    coreReactor.rotation.x = time * 2
    coreReactor.rotation.y = time * 3
  }

  const targetRotY = mouseX * 0.6
  const targetRotX = -mouseY * 0.4
  if (headGroup) {
    headGroup.rotation.y += (targetRotY - headGroup.rotation.y) * 0.08
    headGroup.rotation.x += (targetRotX - headGroup.rotation.x) * 0.08
    if (torsoGroup) torsoGroup.rotation.y = headGroup.rotation.y * 0.2
  }

  // Laser Effects Animation
  if (isLaserActive) {
    if (laserDuration > 0) {
      if (laserGroup && visorMesh) {
        const baseJitter = 0.8 + Math.random() * 0.4
        laserGroup.traverse((child) => {
          if (child.name.startsWith('glow_')) {
            const jitter = baseJitter + Math.random() * 0.2
            child.scale.set(jitter, 1, jitter)
          }
        })
        laserGroup.position.copy(new THREE.Vector3().setFromMatrixPosition(visorMesh.matrixWorld))
      }

      if (muzzleGroup) {
        if (laserDuration > 12) {
          const s = 1 + Math.random() * 0.5
          muzzleGroup.scale.set(s, s, s)
          muzzleGroup.rotation.z += 0.5
          if (visorMesh)
            muzzleGroup.position.copy(
              new THREE.Vector3().setFromMatrixPosition(visorMesh.matrixWorld)
            )
        } else {
          scene.remove(muzzleGroup)
          disposeGroup(muzzleGroup)
          muzzleGroup = null
        }
      }

      if (impactGroup) {
        const posAttribute = impactGroup.geometry.attributes.position
        const vel = impactGroup.geometry.userData.vel
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
        if (!Array.isArray(impactGroup.material)) impactGroup.material.opacity *= 0.9 // Fade out
      }

      laserDuration--
    } else {
      isLaserActive = false
      if (laserGroup) {
        scene.remove(laserGroup)
        disposeGroup(laserGroup)
        laserGroup = null
      }
      if (muzzleGroup) {
        scene.remove(muzzleGroup)
        disposeGroup(muzzleGroup)
        muzzleGroup = null
      }
      if (impactGroup) {
        scene.remove(impactGroup)
        disposeGroup(impactGroup)
        impactGroup = null
      }
    }
  } else {
    if (Math.random() > 0.99) {
      // Random idle behavior or auto-fire
    }
  }
  renderer.render(scene, camera)
}

const onWindowResize = () => {
  if (camera && renderer) {
    camera.aspect = window.innerWidth / window.innerHeight
    camera.updateProjectionMatrix()
    renderer.setSize(window.innerWidth, window.innerHeight)
    if (window.innerWidth < 1024) {
      robotGroup.scale.set(0.7, 0.7, 0.7)
    } else {
      robotGroup.scale.set(1, 1, 1)
    }
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
  (newVal) => {
    const targetColor = newVal ? VISUAL_COLORS.RED : VISUAL_COLORS.CYAN
    if (robotGroup) {
      robotGroup.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          const mat = child.material
          if (!Array.isArray(mat) && mat instanceof THREE.MeshBasicMaterial) {
            if (mat.color.getHex() !== VISUAL_COLORS.GOLD) {
              mat.color.setHex(targetColor)
            }
          }
        }
      })
    }
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
