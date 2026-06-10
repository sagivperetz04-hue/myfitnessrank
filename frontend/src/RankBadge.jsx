import { useEffect, useState } from 'react'
import './RankBadge.css'

// Shield paths shared by all tiers
const SHIELD = "M40,4 L76,17 V55 Q76,75 40,92 Q4,75 4,55 V17 Z"
const INNER  = "M40,13 L67,23 V53 Q67,69 40,82 Q13,69 13,53 V23 Z"
const STAR5  = "40,37 43.2,45.6 52.4,46 45.2,51.7 47.6,60.5 40,55.5 32.4,60.5 34.8,51.7 27.6,46 36.8,45.6"
const CROWN  = "M27,28 L27,21 L32,24.5 L40,15 L48,24.5 L53,21 L53,28 Z"

function Copper({ p }) {
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#d4894a"/>
          <stop offset="100%" stopColor="#7a4010"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#120500" transform="translate(2,3)" opacity="0.5"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#5c2800" strokeWidth="3"/>
      <path d={INNER}  fill="none" stroke="#7a4010" strokeWidth="1.5" opacity="0.6"/>
      {/* Single rank bar */}
      <rect x="20" y="47" width="40" height="8" rx="4" fill="#5c2800"/>
      <rect x="22" y="48.5" width="36" height="5" rx="2.5" fill="#c87535"/>
      <rect x="24" y="49.5" width="16" height="2" rx="1" fill="#e8a060" opacity="0.5"/>
    </svg>
  )
}

function Bronze({ p }) {
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#e8a048"/>
          <stop offset="100%" stopColor="#8b5010"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#120500" transform="translate(2,3)" opacity="0.5"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#6b3a10" strokeWidth="3"/>
      <path d={INNER}  fill="none" stroke="#a05818" strokeWidth="1.5" opacity="0.6"/>
      {/* Two chevrons */}
      <polyline points="22,43 40,54 58,43" stroke="#6b3a10" fill="none" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="22,43 40,54 58,43" stroke="#e8a048" fill="none" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="22,54 40,65 58,54" stroke="#6b3a10" fill="none" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points="22,54 40,65 58,54" stroke="#e8a048" fill="none" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function Silver({ p }) {
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#e8e8e8"/>
          <stop offset="100%" stopColor="#686868"/>
        </linearGradient>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#ffffff"/>
          <stop offset="100%" stopColor="#a0a0a0"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#111" transform="translate(2,3)" opacity="0.5"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#555" strokeWidth="3"/>
      <path d={INNER}  fill="none" stroke="#888" strokeWidth="1.5" opacity="0.6"/>
      {/* Star */}
      <polygon points={STAR5} fill="#444"/>
      <polygon points={STAR5} fill={`url(#${p}-str)`} transform="translate(-1,-1)"/>
    </svg>
  )
}

function Gold({ p }) {
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#ffe566"/>
          <stop offset="100%" stopColor="#a87800"/>
        </linearGradient>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fff8c0"/>
          <stop offset="100%" stopColor="#d4a000"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#1a1000" transform="translate(2,3)" opacity="0.5"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#a87800" strokeWidth="3"/>
      <path d={INNER}  fill="none" stroke="#c8a000" strokeWidth="1.5" opacity="0.7"/>
      {/* Short rays */}
      {[0,45,90,135,180,225,270,315].map(deg => {
        const r = deg * Math.PI / 180
        return <line key={deg}
          x1={(40 + 17*Math.cos(r)).toFixed(1)} y1={(50 + 17*Math.sin(r)).toFixed(1)}
          x2={(40 + 24*Math.cos(r)).toFixed(1)} y2={(50 + 24*Math.sin(r)).toFixed(1)}
          stroke="#a87800" strokeWidth="2" opacity="0.7"/>
      })}
      {/* Crown */}
      <path d={CROWN} fill="#a87800"/>
      <path d={CROWN} fill="#ffe066" transform="translate(-0.5,-0.5)"/>
      {/* Star */}
      <polygon points={STAR5} fill="#a87800"/>
      <polygon points={STAR5} fill={`url(#${p}-str)`} transform="translate(-1,-1)"/>
    </svg>
  )
}

function Platinum({ p }) {
  const DIAMOND = "40,35 52,48 40,62 28,48 Z"
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#1a3040"/>
          <stop offset="100%" stopColor="#071218"/>
        </linearGradient>
        <linearGradient id={`${p}-dia`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#70f0ff"/>
          <stop offset="100%" stopColor="#007aa0"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#001015" transform="translate(2,3)" opacity="0.5"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#00ced1" strokeWidth="3"/>
      <path d={INNER}  fill="none" stroke="#00ced1" strokeWidth="1.5" opacity="0.4"/>
      {/* Corner gems */}
      <circle cx="17" cy="32" r="3"   fill="#00ced1" opacity="0.7"/>
      <circle cx="63" cy="32" r="3"   fill="#00ced1" opacity="0.7"/>
      {/* Crown */}
      <path d={CROWN} fill="#00ced1" opacity="0.95"/>
      {/* Diamond */}
      <polygon points={DIAMOND} fill="#003848"/>
      <polygon points={DIAMOND} fill={`url(#${p}-dia)`} transform="translate(-1,-1)"/>
      <line x1="40" y1="35" x2="34" y2="44" stroke="white" strokeWidth="1.5" opacity="0.5"/>
    </svg>
  )
}

function Elite({ p }) {
  return (
    <svg viewBox="0 0 80 97" fill="none">
      <defs>
        <linearGradient id={`${p}-bg`} x1="25%" y1="0%" x2="75%" y2="100%">
          <stop offset="0%" stopColor="#2e0a42"/>
          <stop offset="100%" stopColor="#0e0020"/>
        </linearGradient>
        <linearGradient id={`${p}-str`} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#f0c0ff"/>
          <stop offset="100%" stopColor="#8020c0"/>
        </linearGradient>
      </defs>
      <path d={SHIELD} fill="#080010" transform="translate(2,3)" opacity="0.6"/>
      <path d={SHIELD} fill={`url(#${p}-bg)`} stroke="#9b59b6" strokeWidth="3"/>
      {/* Extra glow outline */}
      <path d={SHIELD} fill="none" stroke="#c084fc" strokeWidth="1" opacity="0.5"/>
      <path d={INNER}  fill="none" stroke="#9b59b6" strokeWidth="1.5" opacity="0.4"/>
      {/* 8 rays */}
      {[0,45,90,135,180,225,270,315].map(deg => {
        const r = deg * Math.PI / 180
        return <line key={deg}
          x1={(40 + 17*Math.cos(r)).toFixed(1)} y1={(50 + 17*Math.sin(r)).toFixed(1)}
          x2={(40 + 27*Math.cos(r)).toFixed(1)} y2={(50 + 27*Math.sin(r)).toFixed(1)}
          stroke="#9b59b6" strokeWidth="1.5" opacity="0.6"/>
      })}
      {/* Crown */}
      <path d={CROWN} fill="#7a30a0"/>
      <path d={CROWN} fill="#e0b0ff" transform="translate(-0.5,-0.5)"/>
      {/* Central star */}
      <polygon points={STAR5} fill="#4a0080"/>
      <polygon points={STAR5} fill={`url(#${p}-str)`} transform="translate(-1,-1)"/>
      {/* Accent dots */}
      <circle cx="21" cy="59" r="3.5" fill="#c084fc" opacity="0.85"/>
      <circle cx="59" cy="59" r="3.5" fill="#c084fc" opacity="0.85"/>
      <circle cx="40" cy="73" r="3"   fill="#c084fc" opacity="0.75"/>
    </svg>
  )
}

const BADGE_COMPONENTS = { copper: Copper, bronze: Bronze, silver: Silver, gold: Gold, platinum: Platinum, elite: Elite }

const TIER_COLORS = {
  copper:   '#b87333',
  bronze:   '#cd7f32',
  silver:   '#a8a9ad',
  gold:     '#ffd700',
  platinum: '#00ced1',
  elite:    '#9b59b6',
}

export function RankBadge({ tier, percentile, label, id }) {
  const [revealed, setRevealed] = useState(false)
  const [glowing,  setGlowing]  = useState(false)

  const tierKey  = tier?.toLowerCase() ?? 'copper'
  const BadgeSVG = BADGE_COMPONENTS[tierKey] ?? Copper
  const color    = TIER_COLORS[tierKey] ?? '#888'
  const prefix   = `${id ?? 'b'}-${tierKey}`

  useEffect(() => {
    setRevealed(false)
    setGlowing(false)
    const t1 = setTimeout(() => setRevealed(true), 80)
    const t2 = setTimeout(() => setGlowing(true),  80)
    const t3 = setTimeout(() => setGlowing(false), 950)
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3) }
  }, [tier])

  return (
    <div className="rb-wrap">
      <p className="rb-label">{label}</p>
      <div className={`rb-box ${revealed ? 'rb-revealed' : ''}`} style={{ '--tc': color }}>
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
