import { useState } from 'react'
import { emailValid, login, passwordProblems, signup } from './auth'

const DEFAULT = { email: '', password: '' }

export function LoginPage({ onGuest, onAuthed, forceOnline = false }) {
  const [tab, setTab] = useState('login') // 'login' | 'signup'
  const [form, setForm] = useState(DEFAULT)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  const emailOk = emailValid(form.email)
  // Only nag about password rules while signing up — login just checks the pair.
  const pwProblems = tab === 'signup' ? passwordProblems(form.password) : []
  const canSubmit = emailOk && form.password && pwProblems.length === 0

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setLoading(true)
    try {
      const user =
        tab === 'signup'
          ? await signup(form.email, form.password)
          : await login(form.email, form.password)
      onAuthed(user)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function switchTab(next) {
    setTab(next)
    setError(null)
  }

  return (
    <div className="login-page">
      <div className="login-brand">
        <h1><span className="logo-emoji">🏋️</span> MyFitnessRank</h1>
        <p className="login-tagline">Know exactly where your lifts stand.</p>
      </div>

      <div className="login-card">
        <div className="login-tabs">
          <button
            type="button"
            className={tab === 'login' ? 'active' : ''}
            onClick={() => switchTab('login')}
          >
            Log in
          </button>
          <button
            type="button"
            className={tab === 'signup' ? 'active' : ''}
            onClick={() => switchTab('signup')}
          >
            Sign up
          </button>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              value={form.email}
              onChange={set('email')}
            />
          </label>
          {form.email && !emailOk && (
            <p className="field-hint">Enter a valid email address.</p>
          )}

          <label>
            Password
            <input
              type="password"
              autoComplete={tab === 'signup' ? 'new-password' : 'current-password'}
              value={form.password}
              onChange={set('password')}
            />
          </label>
          {tab === 'signup' && form.password && pwProblems.length > 0 && (
            <p className="field-hint">Password needs {pwProblems.join(', ')}.</p>
          )}

          {error && <p className="error" role="alert">{error}</p>}

          <button type="submit" disabled={loading || !canSubmit}>
            {loading ? 'Please wait…' : tab === 'signup' ? 'Create account' : 'Log in'}
          </button>
        </form>
      </div>

      {!forceOnline && (
        <button type="button" className="guest-link" onClick={onGuest}>
          Continue as guest →
        </button>
      )}
    </div>
  )
}
