import { fixture, html } from '@open-wc/testing';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { navigateTo } from '../../app/router';
import { loginQuery } from '../../auth/auth.api';
import './login.page';

vi.mock('../../app/router', () => ({
  navigateTo: vi.fn(async () => {}),
}));

describe('login page', () => {
  afterEach(() => {
    loginQuery.reset();
    vi.useRealTimers();
  });

  it('signs in through the query before navigating to the requested page', async () => {
    window.history.replaceState({}, '', '/login?returnTo=%2Fdashboard%2Freports');
    const element = await fixture(html`<login-page></login-page>`);
    const form = element.shadowRoot!.querySelector('form')!;
    form.insertAdjacentHTML(
      'beforeend',
      '<input name="email" value="person@example.com"><input name="password" value="prototype-password">',
    );
    vi.useFakeTimers();
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    await vi.advanceTimersByTimeAsync(2000);

    expect(loginQuery.data?.email).toBe('person@example.com');
    expect(navigateTo).toHaveBeenCalledWith('/dashboard/reports');
  });
});
