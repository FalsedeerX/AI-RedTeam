// Shared API helper — reads base URL from Vite env so the hardcoded
// demo address (127.0.0.1:5000) is replaced in exactly one place.
// Set VITE_API_BASE_URL in frontend/web/.env to point to the new backend.
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

// Module-level auth state. Call setAuthUserId(id) after login/register.
// Every subsequent API call will include X-User-Id automatically.
let _userId = null;

export function setAuthUserId(id) {
  _userId = id;
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (_userId) headers['X-User-Id'] = _userId;
  return headers;
}

/**
 * Extract a human-readable message from a failed response body.
 * FastAPI uses `detail`; the old Flask demo uses `message`.
 */
async function extractError(response) {
  try {
    const body = await response.json();
    // Surface the status code so callers can branch on 409, 401, etc.
    const msg = body.detail ?? body.message ?? `Request failed: ${response.status}`;
    return `${response.status} ${msg}`;
  } catch {
    return `Request failed: ${response.status}`;
  }
}

export async function apiGet(path) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return response.json();
}

export async function apiPost(path, body = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  return response.json();
}

export async function apiDelete(path) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  if (!response.ok) {
    throw new Error(await extractError(response));
  }
  // 204 No Content has no body
  if (response.status === 204) return null;
  return response.json().catch(() => null);
}
