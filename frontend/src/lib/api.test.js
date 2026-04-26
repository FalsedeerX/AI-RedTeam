import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { registerClerkTokenGetter, apiGet } from './api'

describe('registerClerkTokenGetter', () => {
  beforeEach(() => {
    registerClerkTokenGetter(null)
    vi.restoreAllMocks()
  })

  it('accepts a function reference without throwing', () => {
    const fakeGetToken = async () => 'jwt-abc'
    expect(() => registerClerkTokenGetter(fakeGetToken)).not.toThrow()
  })

  it('accepts null to clear the registered getter (sign-out)', () => {
    registerClerkTokenGetter(async () => 'jwt-abc')
    expect(() => registerClerkTokenGetter(null)).not.toThrow()
  })

  it('ignores non-function values defensively', () => {
    expect(() => registerClerkTokenGetter('not-a-function')).not.toThrow()
    expect(() => registerClerkTokenGetter(42)).not.toThrow()
  })
})

describe('apiGet Authorization header', () => {
  beforeEach(() => {
    registerClerkTokenGetter(null)
  })

  afterEach(() => {
    vi.restoreAllMocks()
    registerClerkTokenGetter(null)
  })

  function mockFetchOk(captureHeaders) {
    return vi.fn(async (_url, init) => {
      captureHeaders(init?.headers ?? {})
      return {
        ok: true,
        status: 200,
        json: async () => ({ ok: true }),
      }
    })
  }

  it('includes Authorization: Bearer <token> when a getter is registered', async () => {
    const captured = {}
    global.fetch = mockFetchOk((headers) => Object.assign(captured, headers))
    registerClerkTokenGetter(async () => 'jwt-xyz')

    await apiGet('/users/me')

    expect(captured.Authorization).toBe('Bearer jwt-xyz')
  })

  it('omits Authorization header when no getter is registered', async () => {
    const captured = {}
    global.fetch = mockFetchOk((headers) => Object.assign(captured, headers))

    await apiGet('/users/me')

    expect(captured.Authorization).toBeUndefined()
  })

  it('omits Authorization header when getter returns null (unauthenticated)', async () => {
    const captured = {}
    global.fetch = mockFetchOk((headers) => Object.assign(captured, headers))
    registerClerkTokenGetter(async () => null)

    await apiGet('/users/me')

    expect(captured.Authorization).toBeUndefined()
  })
})

describe('extractError fallback behavior', () => {
  it('produces a status-based message when response has no JSON body', async () => {
    const fakeResponse = {
      status: 500,
      json: async () => { throw new Error('no body') },
    }

    async function extractError(response) {
      try {
        const body = await response.json()
        return body.detail ?? body.message ?? `Request failed: ${response.status}`
      } catch {
        return `Request failed: ${response.status}`
      }
    }

    const result = await extractError(fakeResponse)
    expect(result).toBe('Request failed: 500')
  })

  it('surfaces the detail field from a FastAPI error response', async () => {
    const fakeResponse = {
      status: 409,
      json: async () => ({ detail: 'Already exists' }),
    }

    async function extractError(response) {
      try {
        const body = await response.json()
        return body.detail ?? body.message ?? `Request failed: ${response.status}`
      } catch {
        return `Request failed: ${response.status}`
      }
    }

    const result = await extractError(fakeResponse)
    expect(result).toBe('Already exists')
  })
})
