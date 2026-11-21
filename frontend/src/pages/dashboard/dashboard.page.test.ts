import { fixture, html } from '@open-wc/testing';
import { afterEach, expect, it, vi } from 'vitest';
import { loginQuery, signOut } from '../../auth/auth.api';
import { DashboardPage } from './dashboard.page';

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
  signOut();
});

it('updates from direct login and session changes while connected', async () => {
  const page = await fixture<DashboardPage>(
    html`<dashboard-page></dashboard-page>`,
  );
  const userText = () => page.shadowRoot!.querySelector('p')!.textContent;
  const signIn = async (email: string) => {
    const login = loginQuery.call({ email, password: 'prototype-password' });
    await vi.advanceTimersByTimeAsync(2000);
    await login;
    await page.updateComplete;
  };
  vi.useFakeTimers();

  await signIn('first@example.com');
  expect(userText()).toContain('first@example.com');

  signOut();
  await page.updateComplete;
  expect(userText()).not.toContain('first@example.com');

  const parent = page.parentElement!;
  page.remove();
  const requestUpdate = vi.spyOn(page, 'requestUpdate');
  await signIn('second@example.com');
  expect(requestUpdate).not.toHaveBeenCalled();

  parent.append(page);
  await page.updateComplete;
  expect(userText()).toContain('second@example.com');
});
