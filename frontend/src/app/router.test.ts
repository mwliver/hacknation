import 'urlpattern-polyfill';
import { LitElement } from 'lit';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { clearSession, loginStore } from '../auth/auth.api';
import { createApplicationRouter, navigateTo } from './router';

class RouterTestHost extends LitElement {}
customElements.define('router-test-host', RouterTestHost);

describe('application router authentication', () => {
  afterEach(() => {
    clearSession();
    vi.useRealTimers();
  });

  it('allows the dashboard after a direct login query and redirects after clearing it', async () => {
    vi.useFakeTimers();
    window.history.replaceState({}, '', '/login');
    const router = createApplicationRouter(new RouterTestHost());
    const login = loginStore.set({
      email: 'person@example.com',
      password: 'prototype-password',
    });
    await vi.advanceTimersByTimeAsync(2000);
    await login;

    await navigateTo('/dashboard/reports?range=week');
    expect(window.location.pathname).toBe('/dashboard/reports');
    expect(window.location.search).toBe('?range=week');
    expect(router.params.section).toBe('reports');

    clearSession();
    await navigateTo('/dashboard');
    expect(window.location.pathname).toBe('/login');
    expect(window.location.search).toBe('?returnTo=%2Fdashboard');
  });
});
