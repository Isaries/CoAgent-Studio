import * as THREE from 'three'

/**
 * Recursively disposes of a Three.js object, its children, geometries, and materials.
 * Essential for preventing memory leaks when removing objects from the scene.
 */
export const disposeGroup = (object: THREE.Object3D) => {
  if (!object) return

  object.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      if (child.geometry) {
        child.geometry.dispose()
      }

      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach((material) => material.dispose())
        } else {
          child.material.dispose()
        }
      }
    }
  })
}
