// Shared API helper — reads base URL from Vite env so the hardcoded
// address is replaced in exactly one place.
// Set VITE_API_BASE_URL in frontend/.env to point to the backend.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

// Module-level reference to Clerk's getToken() function.
// main.jsx wires this up inside <ClerkProvider> via registerClerkTokenGetter.
// Kept outside of React so fetch helpers can be called from any layer.
let _getToken = null

export function registerClerkTokenGetter(getToken) {
  _getToken = typeof getToken === 'function' ? getToken : null
}

async function authHeaders() {
  const headers = { 'Content-Type': 'application/json' }
  if (_getToken) {
    try {
      const token = await _getToken()
      if (token) headers['Authorization'] = `Bearer ${token}`
    } catch {
      // Unauthenticated callers still get the request — backend will 401.
    }
  }
  return headers
}

/**
 * Extract a human-readable message from a failed response body.
 * FastAPI uses `detail`; the old Flask demo uses `message`.
 */
async function extractError(response) {
  try {
    const body = await response.json()
    return body.detail ?? body.message ?? `Request failed: ${response.status}`
  } catch {
    return `Request failed: ${response.status}`
  }
}

export async function apiGet(path) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: await authHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractError(response))
  }
  return response.json()
}

export async function apiPost(path, body = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: await authHeaders(),
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(await extractError(response))
  }
  return response.json()
}

export async function apiDelete(path) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'DELETE',
    headers: await authHeaders(),
  })
  if (!response.ok) {
    throw new Error(await extractError(response))
  }
  if (response.status === 204) return null
  return response.json().catch(() => null)
}
