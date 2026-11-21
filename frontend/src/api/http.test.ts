import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearSession, loginQuery } from '../auth/auth.api';
import { ApiError, httpClient } from './http';
import { navigateTo } from '../app/router';

vi.mock('../app/router', () => ({
  navigateTo: vi.fn(async () => {}),
}));

describe('HttpClient', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 204 })),
    );
    vi.mocked(navigateTo).mockClear();
    clearSession();
  });

  it('serializes query parameters and JSON request bodies', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );

    await expect(
      httpClient.post<{ ok: boolean }, { name: string }>(
        'items',
        { name: 'Example' },
        { query: { page: 2, skipped: null, ignored: undefined } },
      ),
    ).resolves.toEqual({ ok: true });

    const [url, options] = vi.mocked(fetch).mock.calls[0] ?? [];
    expect(String(url)).toContain('page=2');
    expect(new Headers(options?.headers).get('Content-Type')).toBe(
      'application/json',
    );
    expect(options?.body).toBe('{"name":"Example"}');
  });

  it('normalizes API 404 responses without redirecting', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ message: 'User missing' }), {
        status: 404,
        headers: { 'content-type': 'application/json' },
      }),
    );

    await expect(httpClient.get('users/missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
      message: 'User missing',
    });
    expect(navigateTo).not.toHaveBeenCalled();
  });

  it('clears authentication and redirects on 401', async () => {
    await loginQuery.call({
      email: 'person@example.com',
      password: 'prototype-password',
    });
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 401 }));

    await expect(httpClient.get('private')).rejects.toBeInstanceOf(ApiError);

    expect(loginQuery.data).toBeUndefined();
    expect(navigateTo).toHaveBeenCalledWith(
      expect.stringMatching(/^\/login\?returnTo=/),
    );
  });

  it('redirects on 403 without logging out', async () => {
    await loginQuery.call({
      email: 'person@example.com',
      password: 'prototype-password',
    });
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 403 }));

    await expect(httpClient.get('restricted')).rejects.toMatchObject({
      status: 403,
    });

    expect(loginQuery.data?.email).toBe('person@example.com');
    expect(navigateTo).toHaveBeenCalledWith('/forbidden');
  });

  it('keeps API 404 errors as normal endpoint errors', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 404 }));

    await expect(httpClient.get('unknown')).rejects.toBeInstanceOf(ApiError);
    expect(navigateTo).not.toHaveBeenCalled();
  });
});
