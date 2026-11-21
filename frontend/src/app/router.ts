import { Router } from '@lit-labs/router';
import type { ReactiveControllerHost } from 'lit';
import { html } from 'lit';
import { loginStore } from '../auth/auth.api';
import {
  getCurrentReturnPath,
  requireAuthentication,
} from '../auth/auth.guard';

let activeRouter: Router | undefined;

export function createApplicationRouter(
  host: ReactiveControllerHost & HTMLElement,
): Router {
  const protectedEnter = async (): Promise<boolean> =>
    requireAuthentication(
      Boolean(loginStore.get()),
      navigateTo,
      getCurrentReturnPath(),
    );

  const router = new Router(host, [
    {
      path: '/login',
      enter: async () => {
        await import('../pages/login/login.page');
        return true;
      },
      render: () => html`<login-page></login-page>`,
    },
    {
      path: '/dashboard',
      enter: async () => {
        if (!(await protectedEnter())) return false;
        await import('../pages/dashboard/dashboard.page');
        return true;
      },
      render: () => html`<dashboard-page></dashboard-page>`,
    },
    {
      path: '/dashboard/:section',
      enter: async ({ section }) => {
        if (!(await protectedEnter())) return false;
        await import('../pages/dashboard/dashboard.page');
        return Boolean(section);
      },
      render: ({ section }) =>
        html`<dashboard-page .section=${section!}></dashboard-page>`,
    },
    {
      path: '/map',
      enter: async () => {
        if (!(await protectedEnter())) return false;
        await import('../pages/map/map.page');
        return true;
      },
      render: () => html`<map-page></map-page>`,
    },
    {
      path: '/three',
      enter: async () => {
        if (!(await protectedEnter())) return false;
        await import('../pages/three/three.page');
        return true;
      },
      render: () => html`<three-page></three-page>`,
    },
    {
      path: '/forbidden',
      enter: async () => {
        await import('../pages/forbidden/forbidden.page');
        return true;
      },
      render: () => html`<forbidden-page></forbidden-page>`,
    },
    {
      path: '/*',
      enter: async () => {
        await import('../pages/not-found/not-found.page');
        return true;
      },
      render: () => html`<not-found-page></not-found-page>`,
    },
  ]);
  activeRouter = router;
  return router;
}

export async function navigateTo(url: string): Promise<void> {
  if (!activeRouter) {
    throw new Error('Application router has not been initialized.');
  }
  const destination = new URL(url, window.location.href);
  if (destination.origin !== window.location.origin) {
    throw new Error('Application navigation must stay on the current origin.');
  }
  const browserUrl = `${destination.pathname}${destination.search}${destination.hash}`;
  window.history.pushState({}, '', browserUrl);
  await activeRouter.goto(destination.pathname);
}
