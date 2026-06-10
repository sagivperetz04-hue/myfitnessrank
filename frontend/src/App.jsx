import { useState, useEffect } from 'react'
import { RankBadge } from './RankBadge'

const TIER_COLORS = {
  copper:   '#b87333',
  bronze:   '#cd7f32',
  silver:   '#a8a9ad',
  gold:     '#ffd700',
  platinum: '#00ced1',
  elite:    '#9b59b6',
}

const EXERCISES = ['squat', 'bench', 'deadlift', 'total']

const DEFAULT_FORM = {
  exercise:     'squat',
  weight_kg:    '',
  reps:         '',
  bodyweight_kg:'',
  sex:          'M',
}


function ResultCard({ result }) {
  return (
    <div className="result-card">
      <div className="result-stats">
        <div className="stat">
          <span className="stat-label">Estimated 1RM</span>
          <span className="stat-value">{result.one_rm_kg.toFixed(1)} kg</span>
        </div>
        <div className="stat">
          <span className="stat-label">Weight Class</span>
          <span className="stat-value">{result.weight_class_kg} kg</span>
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

function LiftForm({ username, onResult }) {
  const [form, setForm] = useState(DEFAULT_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  const isTotal = form.exercise === 'total'

  async function handleSubmit(e) {
    e.preventDefault()
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
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? `HTTP ${res.status}`)
      onResult(data)
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

      {error && <p className="error">{error}</p>}

      <button type="submit" disabled={loading}>
        {loading ? 'Calculating…' : 'Get My Rank'}
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
    setLoading(true)
    setError(null)
    const params = exercise ? `?exercise=${exercise}` : ''
    fetch(`/api/users/${encodeURIComponent(username)}/history${params}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error)
        setLogs(data.logs)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
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
      {error   && <p className="error">{error}</p>}

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
            {logs.map((row, i) => (
              <tr key={i}>
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

export default function App() {
  const [username, setUsername] = useState(
    () => localStorage.getItem('mfr_username') ?? ''
  )
  const [draftUsername, setDraftUsername] = useState(username)
  const [view, setView] = useState('log')
  const [result, setResult] = useState(null)

  function saveUsername(e) {
    e.preventDefault()
    const val = draftUsername.trim()
    setUsername(val)
    localStorage.setItem('mfr_username', val)
    setResult(null)
  }

  return (
    <div className="app">
      <header>
        <h1>MyFitnessRank</h1>
        <form className="username-form" onSubmit={saveUsername}>
          <input
            type="text"
            placeholder="Username"
            value={draftUsername}
            onChange={(e) => setDraftUsername(e.target.value)}
          />
          <button type="submit">Set</button>
        </form>
        {username && <span className="active-user">Logged in as <strong>{username}</strong></span>}
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
        {view === 'log' && (
          <>
            {!username && <p className="hint">Set a username above to get started.</p>}
            {username && (
              <LiftForm
                username={username}
                onResult={(r) => setResult(r)}
              />
            )}
            {result && <ResultCard result={result} />}
          </>
        )}

        {view === 'history' && <HistoryView username={username} />}
      </main>
    </div>
  )
}
