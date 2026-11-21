import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearSession, loginStore } from './auth.api';

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
      const login = loginStore.set({ email, password: 'prototype-password' });
      await vi.advanceTimersByTimeAsync(2000);
      await login;

      expect(loginStore.get()?.email).toBe(email);
      await clearSession();
      expect(loginStore.get()?.password).toBeUndefined();
    }

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      new URL('/api/logout', window.location.origin),
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
