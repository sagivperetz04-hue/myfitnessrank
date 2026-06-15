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

// Mirrors username_problems in auth/services/security.py.
export function usernameProblems(username) {
  const u = username ?? ''
  const problems = []
  if (u.length < 3 || u.length > 20) problems.push('3 to 20 characters')
  if (u && /[^a-zA-Z0-9_]/.test(u)) problems.push('only letters, numbers, and underscores')
  return problems
}

// Live availability check for the signup form. The unique constraint on the
// accounts table is the real gate — this is UX so the user knows before submit.
export async function usernameAvailable(username, signal) {
  const res = await fetch(
    `/api/auth/username-available?username=${encodeURIComponent(username)}`,
    { signal },
  )
  const data = await readJson(res)
  return data.available
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

async function postSession(path, body) {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await readJson(res)
  accessToken = data.access_token
  return data.user
}

export function signup(email, username, password) {
  return postSession('/api/auth/signup', { email, username, password })
}

export function login(email, password) {
  return postSession('/api/auth/login', { email, password })
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
