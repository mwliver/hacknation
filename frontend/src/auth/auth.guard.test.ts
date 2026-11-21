import { describe, expect, it, vi } from 'vitest';
import {
  isSafeReturnTo,
  loginUrlFor,
  requireAuthentication,
} from './auth.guard';

describe('authentication route guard', () => {
  it('allows authenticated access without navigating', async () => {
    const navigate = vi.fn(async () => {});

    await expect(
      requireAuthentication(true, navigate, '/dashboard'),
    ).resolves.toBe(true);
    expect(navigate).not.toHaveBeenCalled();
  });

  it('redirects unauthenticated users and preserves their requested route', async () => {
    const navigate = vi.fn(async () => {});

    await expect(
      requireAuthentication(false, navigate, '/dashboard/reports?range=week'),
    ).resolves.toBe(false);
    expect(navigate).toHaveBeenCalledWith(
      '/login?returnTo=%2Fdashboard%2Freports%3Frange%3Dweek',
    );
  });

  it('only accepts same-origin relative return paths', () => {
    expect(isSafeReturnTo('/dashboard')).toBe(true);
    expect(isSafeReturnTo('//attacker.example')).toBe(false);
    expect(isSafeReturnTo('https://attacker.example')).toBe(false);
    expect(loginUrlFor('/dashboard')).toBe('/login?returnTo=%2Fdashboard');
  });
});
