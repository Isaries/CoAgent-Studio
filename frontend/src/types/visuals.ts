export interface KnowledgeNode {
  id: number
  x: number // percent
  y: number // percent
  text: string
  vx: number
  vy: number
  opacity: number
  scale: number
}

export interface NetworkLine {
  id: string
  from: number // Node ID
  to: number // Node ID
  opacity: number
}

export const VISUAL_COLORS = {
  CYAN: 0x00ffff,
  BLUE: 0x0066ff,
  RED: 0xff0033,
  DARK: 0x111111,
  LASER_GLOW: 0x00ffff, // Ice Cyan
  GOLD: 0xffd700,
  WHITE: 0xffffff,
  DARK_RED: 0x8b0000
}

export const SYMBOLS_POOL = [
  '∑',
  '∫',
  'π',
  'λ',
  '√',
  '∞',
  '∇',
  '∂',
  'Ω',
  'μ',
  '{ }',
  '</>',
  'f(x)',
  '≠',
  '≈'
]
