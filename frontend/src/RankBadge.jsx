import { useEffect, useState } from 'react'
import { TIER_COLORS } from './tiers'
import './RankBadge.css'

// Tier motifs drawn on the plate hub (plate center is 50,52)
const STAR  = "50,42 53,50 61.5,50.4 55,55.6 57.2,63.6 50,59 42.8,63.6 45,55.6 38.5,50.4 47,50"
const CROWN = "42,38 42,31 46,34.5 50,27 54,34.5 58,31 58,38 Z"

const BOLT_ANGLES = [270, 342, 54, 126, 198]

function boltPos(deg) {
  const r = (deg * Math.PI) / 180
  return { cx: (50 + 26.5 * Math.cos(r)).toFixed(1), cy: (52 + 26.5 * Math.sin(r)).toFixed(1) }
}

// Bumper plate: colored rim, rubber ring, machined hub with bolts
function Plate({ p, rim1, rim2, edge, glow, children }) {
  return (
    <svg viewBox="0 0 100 104" fill="none">
      <defs>
        <linearGradient id={`${p}-rim`} x1="20%" y1="0%" x2="80%" y2="100%">
          <stop offset="0%" stopColor={rim1}/>
          <stop offset="100%" stopColor={rim2}/>
        </linearGradient>
        <radialGradient id={`${p}-hub`} cx="40%" cy="35%" r="80%">
          <stop offset="0%" stopColor="#2b2b36"/>
          <stop offset="100%" stopColor="#101016"/>
        </radialGradient>
      </defs>
      <ellipse cx="52" cy="56" rx="44" ry="44" fill="#000" opacity="0.45"/>
      <circle cx="50" cy="52" r="44" fill={`url(#${p}-rim)`} stroke={edge} strokeWidth="3"/>
      {glow && <circle cx="50" cy="52" r="47" fill="none" stroke={glow} strokeWidth="1.5" opacity="0.6"/>}
      <circle cx="50" cy="52" r="34" fill="#14141a" stroke={edge} strokeWidth="1.5" opacity="0.9"/>
      <circle cx="50" cy="52" r="21" fill={`url(#${p}-hub)`} stroke={edge} strokeWidth="2"/>
      {BOLT_ANGLES.map((deg) => {
        const { cx, cy } = boltPos(deg)
        return <circle key={deg} cx={cx} cy={cy} r="2.2" fill={edge} opacity="0.85"/>
      })}
      {/* grip cutouts */}
      <ellipse cx="22" cy="52" rx="3.2" ry="7" fill="#000" opacity="0.4"/>
      <ellipse cx="78" cy="52" rx="3.2" ry="7" fill="#000" opacity="0.4"/>
      {/* top sheen */}
      <path d="M16,38 A38,38 0 0,1 84,38" stroke="#fff" strokeWidth="2.5" opacity="0.18" fill="none"/>
      {children}
    </svg>
  )
}

function Copper({ p }) {
  return (
    <Plate p={p} rim1="#d4894a" rim2="#7a4010" edge="#5c2800">
      <rect x="38" y="49" width="24" height="6" rx="3" fill="#5c2800"/>
      <rect x="40" y="50.2" width="20" height="3.6" rx="1.8" fill="#c87535"/>
    </Plate>
  )
}

function Bronze({ p }) {
  return (
    <Plate p={p} rim1="#e8a048" rim2="#8b5010" edge="#6b3a10">
      <polyline points="40,45 50,52 60,45" stroke="#6b3a10" fill="none" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="40,45 50,52 60,45" stroke="#e8a048" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="40,53 50,60 60,53" stroke="#6b3a10" fill="none" strokeWidth="4.5" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="40,53 50,60 60,53" stroke="#e8a048" fill="none" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </Plate>
  )
}

function Silver({ p }) {
  return (
    <Plate p={p} rim1="#e8e8e8" rim2="#686868" edge="#4a4a52">
      <defs>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffffff"/>
          <stop offset="100%" stopColor="#a0a0a0"/>
        </linearGradient>
      </defs>
      <polygon points={STAR} fill="#3a3a42"/>
      <polygon points={STAR} fill={`url(#${p}-str)`} transform="translate(-0.8,-0.8)"/>
    </Plate>
  )
}

function Gold({ p }) {
  return (
    <Plate p={p} rim1="#ffe566" rim2="#a87800" edge="#8a6200" glow="#ffd700">
      <defs>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fff8c0"/>
          <stop offset="100%" stopColor="#d4a000"/>
        </linearGradient>
      </defs>
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
        const r = (deg * Math.PI) / 180
        return <line key={deg}
          x1={(50 + 23 * Math.cos(r)).toFixed(1)} y1={(52 + 23 * Math.sin(r)).toFixed(1)}
          x2={(50 + 31 * Math.cos(r)).toFixed(1)} y2={(52 + 31 * Math.sin(r)).toFixed(1)}
          stroke="#ffd700" strokeWidth="2" opacity="0.55"/>
      })}
      <path d={CROWN} fill="#8a6200"/>
      <path d={CROWN} fill="#ffe066" transform="translate(-0.5,-0.5)"/>
      <polygon points={STAR} fill="#8a6200"/>
      <polygon points={STAR} fill={`url(#${p}-str)`} transform="translate(-0.8,-0.8)"/>
    </Plate>
  )
}

function Platinum({ p }) {
  const DIAMOND = "50,42 59,52 50,63 41,52 Z"
  return (
    <Plate p={p} rim1="#1a3040" rim2="#071218" edge="#00ced1" glow="#00ced1">
      <defs>
        <linearGradient id={`${p}-dia`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#70f0ff"/>
          <stop offset="100%" stopColor="#007aa0"/>
        </linearGradient>
      </defs>
      <circle cx="29" cy="36" r="2.6" fill="#00ced1" opacity="0.8"/>
      <circle cx="71" cy="36" r="2.6" fill="#00ced1" opacity="0.8"/>
      <path d={CROWN} fill="#00ced1" opacity="0.95"/>
      <polygon points={DIAMOND} fill="#003848"/>
      <polygon points={DIAMOND} fill={`url(#${p}-dia)`} transform="translate(-0.8,-0.8)"/>
      <line x1="50" y1="42" x2="45" y2="50" stroke="white" strokeWidth="1.2" opacity="0.5"/>
    </Plate>
  )
}

function Elite({ p }) {
  return (
    <Plate p={p} rim1="#2e0a42" rim2="#0e0020" edge="#9b59b6" glow="#c084fc">
      <defs>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f0c0ff"/>
          <stop offset="100%" stopColor="#8020c0"/>
        </linearGradient>
      </defs>
      {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => {
        const r = (deg * Math.PI) / 180
        return <line key={deg}
          x1={(50 + 23 * Math.cos(r)).toFixed(1)} y1={(52 + 23 * Math.sin(r)).toFixed(1)}
          x2={(50 + 32 * Math.cos(r)).toFixed(1)} y2={(52 + 32 * Math.sin(r)).toFixed(1)}
          stroke="#9b59b6" strokeWidth="1.5" opacity="0.6"/>
      })}
      <path d={CROWN} fill="#7a30a0"/>
      <path d={CROWN} fill="#e0b0ff" transform="translate(-0.5,-0.5)"/>
      <polygon points={STAR} fill="#4a0080"/>
      <polygon points={STAR} fill={`url(#${p}-str)`} transform="translate(-0.8,-0.8)"/>
      <circle cx="32" cy="64" r="2.8" fill="#c084fc" opacity="0.85"/>
      <circle cx="68" cy="64" r="2.8" fill="#c084fc" opacity="0.85"/>
    </Plate>
  )
}

const BADGE_COMPONENTS = { copper: Copper, bronze: Bronze, silver: Silver, gold: Gold, platinum: Platinum, elite: Elite }

export function RankBadge({ tier, percentile, label, id }) {
  const [revealed, setRevealed] = useState(false)
  const [glowing,  setGlowing]  = useState(false)

  const tierKey  = tier?.toLowerCase() ?? 'copper'
  const BadgeSVG = BADGE_COMPONENTS[tierKey] ?? Copper
  const color    = TIER_COLORS[tierKey] ?? '#888'
  const prefix   = `${id ?? 'b'}-${tierKey}`

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reveal animation must restart from hidden when the tier changes
    setRevealed(false)
    setGlowing(false)
    const t1 = setTimeout(() => setRevealed(true), 80)
    const t2 = setTimeout(() => setGlowing(true),  80)
    const t3 = setTimeout(() => setGlowing(false), 1100)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [tier])

  return (
    <div className="rb-wrap">
      <p className="rb-label">{label}</p>
      <div className={`rb-box ${revealed ? 'rb-revealed' : ''} ${tierKey === 'elite' ? 'rb-elite' : ''}`} style={{ '--tc': color }}>
        {glowing && <div className="rb-glow"/>}
        <BadgeSVG p={prefix}/>
      </div>
      <div className={`rb-info ${revealed ? 'rb-revealed' : ''}`}>
        <span className="rb-tier" style={{ color }}>{tier?.toUpperCase()}</span>
        <span className="rb-pct">top {percentile}%</span>
      </div>
    </div>
  )
}
