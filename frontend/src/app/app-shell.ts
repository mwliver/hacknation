import { QueryClientProvider } from '@tanstack/lit-query';
import { css, html } from 'lit';
import { customElement, state } from 'lit/decorators.js';
import { queryClient } from './query-client';
import { createApplicationRouter } from './router';
import '../components/layout/app-header';
import '../components/layout/app-nav-drawer';
import '../components/ui/web-components';
import { loginQuery } from '../auth/auth.api';
import { appStorage, type ThemePreference } from '../storage/app-storage';

@customElement('app-shell')
export class AppShell extends QueryClientProvider {
  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--app-color-background);
      color: var(--app-color-text);
    }

    main {
      width: min(calc(100% - 2rem), 72rem);
      margin: 0 auto;
      padding: clamp(1.25rem, 4vw, var(--app-space-8)) 0;
    }

    app-header nav a:hover {
      color: var(--app-color-primary);
      background: var(--app-color-background);
    }

    app-header wa-button {
      min-height: 2.75rem;
    }

    @media (max-width: 40rem) {
      main {
        width: min(calc(100% - 1.5rem), 72rem);
        padding-block: 1.25rem;
      }

      app-header nav a {
        padding-inline: var(--app-space-1);
      }
    }
  `;

  @state()
  private theme: ThemePreference = appStorage.theme.get();

  private readonly router = createApplicationRouter(this);
  private unsubscribeTheme?: () => void;

  constructor() {
    super();
    this.client = queryClient;
  }

  connectedCallback(): void {
    super.connectedCallback();
    this.dataset.theme = this.theme;
    document.documentElement.dataset.theme = this.theme;
    document.documentElement.classList.toggle('wa-dark', this.theme === 'dark');
    document.documentElement.classList.toggle(
      'wa-light',
      this.theme === 'light',
    );
    this.unsubscribeTheme = appStorage.theme.subscribe((theme) => {
      this.theme = theme;
      this.dataset.theme = theme;
      document.documentElement.dataset.theme = theme;
      document.documentElement.classList.toggle('wa-dark', theme === 'dark');
      document.documentElement.classList.toggle('wa-light', theme === 'light');
    });
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    this.unsubscribeTheme?.();
    this.unsubscribeTheme = undefined;
  }

  render() {
    loginQuery.observe(this);
    const currentUser = loginQuery.data;
    return html`
      <app-header>
        ${currentUser
          ? html`<app-nav-drawer
              slot="start"
              .user=${currentUser}
            ></app-nav-drawer>`
          : ''}
        <nav aria-label="Main navigation">
          <wa-button
            size="s"
            appearance="plain"
            aria-label="Toggle color theme"
            title="Toggle color theme"
            @click=${this.toggleTheme}
          >
            <wa-icon name=${this.theme === 'light' ? 'moon' : 'sun'}></wa-icon>
          </wa-button>
        </nav>
      </app-header>
      <main>${this.router.outlet()}</main>
    `;
  }

  private toggleTheme(): void {
    appStorage.theme.set(this.theme === 'light' ? 'dark' : 'light');
  }
}
