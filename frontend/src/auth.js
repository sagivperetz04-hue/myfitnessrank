// Auth client for the online mode. The access token is held in memory only
// (never localStorage) so an XSS can't read it from storage; the refresh token
// lives in an HttpOnly cookie the JS can't touch and is replayed on reload.

let accessToken = null

export function getAccessToken() {
  return accessToken
}

// Mirrors the server-side checks in auth/services/security.py. These are UX —
// the auth service re-validates and is the real gate.
export const EMAIL_RE = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/

export function emailValid(email) {
  return EMAIL_RE.test(email ?? '')
}

export function passwordProblems(password) {
  const pw = password ?? ''
  const problems = []
  if (pw.length < 8) problems.push('at least 8 characters')
  if (!/[A-Z]/.test(pw)) problems.push('one uppercase letter')
  if (!/[0-9]/.test(pw)) problems.push('one number')
  if (!/[^A-Za-z0-9]/.test(pw)) problems.push('one special character')
  return problems
}

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

async function postCredentials(path, email, password) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const data = await readJson(res)
  accessToken = data.access_token
  return data.user
}

export function signup(email, password) {
  return postCredentials('/api/auth/signup', email, password)
}

export function login(email, password) {
  return postCredentials('/api/auth/login', email, password)
}

// Called on reload: exchanges the HttpOnly refresh cookie for a fresh access
// token. Returns the user, or null if there is no valid session.
export async function restoreSession() {
  const res = await fetch('/api/auth/refresh', { method: 'POST' })
  if (!res.ok) return null
  const data = await res.json()
  accessToken = data.access_token
  return data.user
}

export async function logout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } finally {
    accessToken = null
  }
}
