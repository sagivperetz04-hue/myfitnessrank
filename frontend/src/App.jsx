import { useState, useEffect } from 'react'
import { RankBadge } from './RankBadge'
import { TIER_COLORS } from './tiers'
import { LoginPage } from './LoginPage'
import { logout, restoreSession } from './auth'

const EXERCISES = ['squat', 'bench', 'deadlift', 'total']

// Open / super-heavyweight classes have no upper bound — show their key as "NNN+"
const OPEN_CLASS_LABELS = { 140: '120+', 100: '84+' }
const formatWeightClass = (kg) => OPEN_CLASS_LABELS[kg] ?? kg

// All-time world records (kg); inputs are capped at WR + 2
const WORLD_RECORDS = {
  squat:    525,
  bench:    355,
  deadlift: 505,
  total:    1152.5,
}
const WR_MARGIN_KG = 2

// Backend errors come as JSON, but a dead upstream answers with nginx HTML —
// parse defensively so the user sees the status, not a JSON SyntaxError
async function readJson(res) {
  let data = null
  try {
    data = await res.json()
  } catch {
    // non-JSON body (e.g. nginx error page) — fall through to the status check
  }
  if (!res.ok) throw new Error(data?.error ?? `HTTP ${res.status}`)
  return data
}

const DEFAULT_FORM = {
  exercise:     'squat',
  weight_kg:    '',
  reps:         '',
  bodyweight_kg:'',
  sex:          'M',
}

function useCountUp(target, ms = 900) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    let raf
    const start = performance.now()
    const tick = (now) => {
      const t = Math.min((now - start) / ms, 1)
      setVal(target * (1 - Math.pow(1 - t, 3)))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return val
}

// Competition-colored plates, mirrored on both sleeves
const PLATES = [
  { offset: 0,  w: 14, h: 96, c1: '#ff5050', c2: '#a00000', edge: '#700' },
  { offset: 15, w: 12, h: 76, c1: '#4080ff', c2: '#0030a0', edge: '#025' },
  { offset: 28, w: 10, h: 58, c1: '#ffd040', c2: '#b08000', edge: '#860' },
  { offset: 39, w: 8,  h: 42, c1: '#40c860', c2: '#107030', edge: '#052' },
]

function BarbellSVG() {
  return (
    <svg className="intro-barbell" viewBox="0 0 260 140">
      <defs>
        <linearGradient id="bar-steel" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#f0f0f8"/>
          <stop offset="50%" stopColor="#a8a8b8"/>
          <stop offset="100%" stopColor="#70707e"/>
        </linearGradient>
      </defs>
      <rect x="6" y="66" width="248" height="8" rx="4" fill="url(#bar-steel)"/>
      {[104, 112, 120, 128, 136, 144, 152].map((x) => (
        <rect key={x} x={x} y="67.5" width="2" height="5" fill="#60606e" opacity="0.6"/>
      ))}
      {PLATES.map(({ offset, w, h, c1, c2, edge }) => {
        const y = 70 - h / 2
        return (
          <g key={offset}>
            <defs>
              <linearGradient id={`pl-${offset}`} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={c1}/>
                <stop offset="100%" stopColor={c2}/>
              </linearGradient>
            </defs>
            <rect x={58 - offset - w} y={y} width={w} height={h} rx="4" fill={`url(#pl-${offset})`} stroke={edge} strokeWidth="1.5"/>
            <rect x={202 + offset} y={y} width={w} height={h} rx="4" fill={`url(#pl-${offset})`} stroke={edge} strokeWidth="1.5"/>
          </g>
        )
      })}
      <rect x="62" y="58" width="6" height="24" rx="2" fill="#c8c8d4" stroke="#888" strokeWidth="1"/>
      <rect x="192" y="58" width="6" height="24" rx="2" fill="#c8c8d4" stroke="#888" strokeWidth="1"/>
    </svg>
  )
}

function LiftIntro({ username, onDone }) {
  useEffect(() => {
    const t = setTimeout(onDone, 2700)
    window.addEventListener('keydown', onDone)
    return () => {
      clearTimeout(t)
      window.removeEventListener('keydown', onDone)
    }
  }, [onDone])

  return (
    <div className="intro-overlay" onClick={onDone}>
      <div className="intro-stage">
        <BarbellSVG/>
        <div className="intro-shadow"/>
      </div>
      <p className="intro-welcome">WELCOME BACK</p>
      <p className="intro-name">{username}</p>
      <p className="intro-skip">click anywhere or press a key to skip</p>
    </div>
  )
}

function ResultCard({ result }) {
  const oneRm = useCountUp(result.one_rm_kg)
  return (
    <div className="result-card">
      <div className="result-stats">
        <div className="stat">
          <span className="stat-label">Estimated 1RM</span>
          <span className="stat-value">{oneRm.toFixed(1)} kg</span>
        </div>
        <div className="stat">
          <span className="stat-label">Weight Class</span>
          <span className="stat-value">{formatWeightClass(result.weight_class_kg)} kg</span>
        </div>
      </div>
      <div className="rank-row">
        <RankBadge
          id="comp"
          label="vs. Professional lifters"
          tier={result.competition.tier}
          percentile={result.competition.percentile}
        />
        <RankBadge
          id="avg"
          label="vs. Average gym goers"
          tier={result.world_avg.tier}
          percentile={result.world_avg.percentile}
        />
      </div>
    </div>
  )
}

export function LiftForm({ username, onResult }) {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  const isTotal = form.exercise === 'total'
  const weightLimit = WORLD_RECORDS[form.exercise] + WR_MARGIN_KG
  const overLimit = parseFloat(form.weight_kg) > weightLimit

  async function handleSubmit(e) {
    e.preventDefault()
    if (overLimit) return
    setError(null)
    setLoading(true)
    try {
      const res = await fetch('/api/rank', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          exercise:      form.exercise,
          weight_kg:     parseFloat(form.weight_kg),
          reps:          isTotal ? 1 : parseInt(form.reps, 10),
          bodyweight_kg: parseFloat(form.bodyweight_kg),
          sex:           form.sex,
        }),
      })
      onResult(await readJson(res))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form className="lift-form" onSubmit={handleSubmit}>
      <label>
        Exercise
        <select value={form.exercise} onChange={set('exercise')}>
          {EXERCISES.map((ex) => (
            <option key={ex} value={ex}>{ex.charAt(0).toUpperCase() + ex.slice(1)}</option>
          ))}
        </select>
      </label>

      <div className="form-row">
        <label>
          {isTotal ? 'Total (kg)' : 'Weight (kg)'}
          <input
            type="number" min="1" step="0.5" required
            value={form.weight_kg} onChange={set('weight_kg')}
          />
        </label>
        {!isTotal && (
          <label>
            Reps (1–20)
            <input
              type="number" min="1" max="20" required
              value={form.reps} onChange={set('reps')}
            />
          </label>
        )}
      </div>

      <div className="form-row">
        <label>
          Bodyweight (kg)
          <input
            type="number" min="1" step="0.5" required
            value={form.bodyweight_kg} onChange={set('bodyweight_kg')}
          />
        </label>
        <label>
          Sex
          <select value={form.sex} onChange={set('sex')}>
            <option value="M">Male</option>
            <option value="F">Female</option>
          </select>
        </label>
      </div>

      {overLimit && (
        <p className="over-limit" role="alert">
          😞 Really? if yes go to compete and set a new world record
        </p>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      <button type="submit" disabled={loading || overLimit}>
        {loading ? 'Calculating…' : 'Get My Rank 🏋️'}
      </button>
    </form>
  )
}

function HistoryView({ username }) {
  const [logs, setLogs] = useState(null)
  const [exercise, setExercise] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!username) return
    const controller = new AbortController()
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading flag must flip before the fetch resolves
    setLoading(true)
    setError(null)
    const params = exercise ? `?exercise=${exercise}` : ''
    fetch(`/api/users/${encodeURIComponent(username)}/history${params}`, {
      signal: controller.signal,
    })
      .then(readJson)
      .then((data) => {
        setLogs(data.logs)
        setLoading(false)
      })
      .catch((err) => {
        if (err.name === 'AbortError') return
        setError(err.message)
        setLoading(false)
      })
    return () => controller.abort()
  }, [username, exercise])

  if (!username) return <p className="hint">Set your username above first.</p>

  return (
    <div className="history">
      <div className="history-filters">
        <label>
          Filter by exercise
          <select value={exercise} onChange={(e) => setExercise(e.target.value)}>
            <option value="">All</option>
            {EXERCISES.map((ex) => (
              <option key={ex} value={ex}>{ex.charAt(0).toUpperCase() + ex.slice(1)}</option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="hint">Loading…</p>}
      {error   && <p className="error" role="alert">{error}</p>}

      {logs && logs.length === 0 && <p className="hint">No logs yet. Log a lift first.</p>}

      {logs && logs.length > 0 && (
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Exercise</th>
              <th>Weight</th>
              <th>Reps</th>
              <th>1RM</th>
              <th>vs. Comp.</th>
              <th>vs. World</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((row) => (
              <tr key={row.id}>
                <td>{new Date(row.logged_at).toLocaleDateString()}</td>
                <td>{row.exercise}</td>
                <td>{row.weight_kg} kg</td>
                <td>{row.reps}</td>
                <td>{parseFloat(row.one_rm_kg).toFixed(1)} kg</td>
                <td style={{ color: TIER_COLORS[row.competition.tier] }}>
                  {row.competition.tier} (top {row.competition.percentile}%)
                </td>
                <td style={{ color: TIER_COLORS[row.world_avg.tier] }}>
                  {row.world_avg.tier} (top {row.world_avg.percentile}%)
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

// The ranking app shell. `editable` username = guest mode (browser-local
// identity); a fixed identity = online mode (the signed-in account).
function RankApp({ identity, editable, onExit, exitLabel }) {
  const [username, setUsername] = useState(identity)
  const [draftUsername, setDraftUsername] = useState(identity)
  const [view, setView] = useState('log')
  const [result, setResult] = useState(null)
  const [intro, setIntro] = useState(() => Boolean(identity))

  function saveUsername(e) {
    e.preventDefault()
    const val = draftUsername.trim()
    setUsername(val)
    localStorage.setItem('mfr_username', val)
    setResult(null)
    if (val) setIntro(true)
  }

  return (
    <div className="app">
      {intro && username && <LiftIntro username={username} onDone={() => setIntro(false)}/>}

      <header>
        <h1><span className="logo-emoji">🏋️</span> MyFitnessRank</h1>
        {editable && (
          <form className="username-form" onSubmit={saveUsername}>
            <input
              type="text"
              placeholder="Username"
              aria-label="Username"
              value={draftUsername}
              onChange={(e) => setDraftUsername(e.target.value)}
            />
            <button type="submit">Set</button>
          </form>
        )}
        {username && (
          <span className="active-user">
            <span className="user-dot"/> Logged in as <strong>{username}</strong>
          </span>
        )}
        <button type="button" className="exit-btn" onClick={onExit}>
          {exitLabel}
        </button>
      </header>

      <nav>
        <button
          className={view === 'log' ? 'active' : ''}
          onClick={() => setView('log')}
        >
          Log Lift
        </button>
        <button
          className={view === 'history' ? 'active' : ''}
          onClick={() => setView('history')}
        >
          History
        </button>
      </nav>

      <main>
        {/* key remount re-triggers the view slide-in on every tab switch */}
        <div className="view" key={view}>
          {view === 'log' && (
            <>
              {!username && <p className="hint">Set a username above to get started.</p>}
              {username && (
                <LiftForm
                  username={username}
                  onResult={(r) => setResult(r)}
                />
              )}
              {result && <ResultCard result={result}/>}
            </>
          )}

          {view === 'history' && <HistoryView username={username}/>}
        </div>
      </main>
    </div>
  )
}

export default function App() {
  // null = no choice yet (show login page); 'guest' | 'online' otherwise
  const [mode, setMode] = useState(() => localStorage.getItem('mfr_mode'))
  const [account, setAccount] = useState(null)
  const [checking, setChecking] = useState(() => localStorage.getItem('mfr_mode') === 'online')

  // On reload in online mode, trade the HttpOnly refresh cookie for a session.
  useEffect(() => {
    if (mode !== 'online') return
    let active = true
    restoreSession()
      .then((user) => { if (active) setAccount(user) })
      .catch(() => { if (active) setAccount(null) })
      .finally(() => { if (active) setChecking(false) })
    return () => { active = false }
  }, [mode])

  function chooseGuest() {
    localStorage.setItem('mfr_mode', 'guest')
    setMode('guest')
  }

  function onAuthed(user) {
    localStorage.setItem('mfr_mode', 'online')
    setAccount(user)
    setChecking(false)
    setMode('online')
  }

  async function exitOnline() {
    await logout()
    setAccount(null)
    localStorage.removeItem('mfr_mode')
    setMode(null)
  }

  function exitGuest() {
    localStorage.removeItem('mfr_mode')
    setMode(null)
  }

  if (mode === 'online' && checking) {
    return <div className="app"><p className="hint">Restoring session…</p></div>
  }
  if (!mode) {
    return <LoginPage onGuest={chooseGuest} onAuthed={onAuthed}/>
  }
  if (mode === 'online' && !account) {
    return <LoginPage onGuest={chooseGuest} onAuthed={onAuthed} forceOnline/>
  }
  if (mode === 'online') {
    return (
      <RankApp
        identity={account.username}
        editable={false}
        onExit={exitOnline}
        exitLabel="Log out"
      />
    )
  }
  return (
    <RankApp
      identity={localStorage.getItem('mfr_username') ?? ''}
      editable
      onExit={exitGuest}
      exitLabel="Exit guest"
    />
  )
}
