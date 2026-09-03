import { describe, expect, it } from 'vitest'
import { ApiError, friendlyError, PROVIDER_ERROR_COPY } from './api'

describe('friendlyError', () => {
  it('maps provider status codes to the Settings copy', () => {
    expect(friendlyError(new ApiError(401, 'Invalid API key'))).toBe(
      'Invalid API key. Please check Settings.',
    )
    expect(friendlyError(new ApiError(408, 'LLM request timed out'))).toBe(
      'Request timed out. Try again.',
    )
    expect(friendlyError(new ApiError(429, 'Rate limit exceeded'))).toBe(
      PROVIDER_ERROR_COPY[429],
    )
    expect(friendlyError(new ApiError(503, 'Cannot reach LLM service'))).toBe(
      'Cannot reach LLM service. Check your connection.',
    )
  })
})
