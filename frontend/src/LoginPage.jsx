import { useEffect, useState } from 'react'
import {
  emailValid,
  login,
  passwordProblems,
  signup,
  usernameAvailable,
  usernameProblems,
} from './auth'

const DEFAULT = { email: '', username: '', password: '' }

export function LoginPage({ onGuest, onAuthed, forceOnline = false }) {
  const [tab, setTab] = useState('login') // 'login' | 'signup'
  const [form, setForm] = useState(DEFAULT)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  // null | 'checking' | 'available' | 'taken'
  const [usernameStatus, setUsernameStatus] = useState(null)

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  const emailOk = emailValid(form.email)
  // Only enforce username/password rules while signing up — login just checks
  // the email/password pair against the account.
  const username = form.username.trim()
  const unameProblems = tab === 'signup' ? usernameProblems(username) : []
  const pwProblems = tab === 'signup' ? passwordProblems(form.password) : []
  const canSubmit =
    emailOk &&
    form.password &&
    pwProblems.length === 0 &&
    (tab === 'login' || (unameProblems.length === 0 && usernameStatus === 'available'))

  // Debounced live availability check. The unique constraint server-side is the
  // real gate; this just tells the user before they submit.
  useEffect(() => {
    if (tab !== 'signup') return
    if (usernameProblems(username).length > 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clear stale status when the field becomes invalid
      setUsernameStatus(null)
      return
    }
    setUsernameStatus('checking')
    const controller = new AbortController()
    const t = setTimeout(() => {
      usernameAvailable(username, controller.signal)
        .then((ok) => setUsernameStatus(ok ? 'available' : 'taken'))
        .catch((err) => {
          if (err.name !== 'AbortError') setUsernameStatus(null)
        })
    }, 400)
    return () => {
      clearTimeout(t)
      controller.abort()
    }
  }, [username, tab])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setError(null)
    setLoading(true)
    try {
      const user =
        tab === 'signup'
          ? await signup(form.email, username, form.password)
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
    setUsernameStatus(null)
  }

  return (
    <div className="login-page">
      <div className="login-brand">
        <h1 className="wordmark">MyFitness<span>Rank</span></h1>
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

          {tab === 'signup' && (
            <>
              <label>
                Username
                <input
                  type="text"
                  autoComplete="username"
                  placeholder="Choose a username"
                  value={form.username}
                  onChange={set('username')}
                />
              </label>
              {form.username && unameProblems.length > 0 && (
                <p className="field-hint">Username needs {unameProblems.join(', ')}.</p>
              )}
              {unameProblems.length === 0 && usernameStatus === 'checking' && (
                <p className="field-hint">Checking availability…</p>
              )}
              {unameProblems.length === 0 && usernameStatus === 'taken' && (
                <p className="field-hint error">That username is taken.</p>
              )}
              {unameProblems.length === 0 && usernameStatus === 'available' && (
                <p className="field-hint available">That username is available.</p>
              )}
            </>
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
