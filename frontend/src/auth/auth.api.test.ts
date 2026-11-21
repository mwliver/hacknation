import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearSession, loginQuery, signOut } from './auth.api';

describe('signOut', () => {
  afterEach(() => {
    clearSession();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('sends a fresh logout request and clears the user after each sign-out', async () => {
    vi.useFakeTimers();
    const fetch = vi.fn(async () => new Response(null, { status: 204 }));
    vi.stubGlobal('fetch', fetch);

    for (const email of ['first@example.com', 'second@example.com']) {
      const login = loginQuery.call({ email, password: 'prototype-password' });
      await vi.advanceTimersByTimeAsync(2000);
      await login;

      expect(loginQuery.data?.email).toBe(email);
      await signOut();
      expect(loginQuery.data).toBeUndefined();
    }

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      new URL('/api/logout', window.location.origin),
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
