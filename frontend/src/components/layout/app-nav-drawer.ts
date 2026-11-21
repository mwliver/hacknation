import { LitElement, css, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { navigateTo } from '../../app/router';
import { signOut } from '../../auth/auth.api';
import type { User } from '../../auth/auth.types';

@customElement('app-nav-drawer')
export class AppNavDrawer extends LitElement {
  static styles = css`
    :host {
      display: inline-flex;
    }

    nav {
      display: flex;
      flex-direction: column;
      gap: var(--app-space-1);
    }

    nav a {
      display: flex;
      align-items: center;
      gap: var(--app-space-2);
      min-height: 2.75rem;
      padding-inline: var(--app-space-2);
      border-radius: var(--app-radius-sm);
      color: var(--app-color-text);
      text-decoration: none;
    }

    nav a:hover {
      color: var(--app-color-primary);
      background: var(--app-color-background);
    }

    .footer {
      display: flex;
      flex-direction: column;
      gap: var(--app-space-3);
      width: 100%;
    }

    .user-info {
      display: flex;
      flex-direction: column;
      gap: var(--app-space-1);
      min-width: 0;
    }

    .user-name {
      font-weight: 700;
      overflow-wrap: anywhere;
    }

    .user-email {
      color: var(--app-color-text-muted);
      font-size: 0.875rem;
      overflow-wrap: anywhere;
    }

    wa-button {
      min-height: 2.75rem;
    }
  `;

  @property({ attribute: false })
  user?: User;

  @state()
  private open = false;

  render() {
    return html`
      <wa-button
        size="s"
        appearance="plain"
        aria-label="Open navigation menu"
        title="Open navigation menu"
        @click=${this.openDrawer}
      >
        <wa-icon name="bars"></wa-icon>
      </wa-button>
      <wa-drawer
        label="Navigation"
        placement="start"
        light-dismiss
        ?open=${this.open}
        @wa-hide=${this.handleHide}
      >
        <nav aria-label="Drawer navigation">
          <a href="/dashboard" @click=${this.handleDashboardClick}>
            <wa-icon name="gauge"></wa-icon>
            Dashboard
          </a>
          <a href="/map" @click=${this.handleMapClick}>
            <wa-icon name="map"></wa-icon>
            Map
          </a>
          <a href="/three" @click=${this.handleThreeClick}>
            <wa-icon name="cube"></wa-icon>
            3D Demo
          </a>
        </nav>
        <div slot="footer" class="footer">
          <div class="user-info">
            <span class="user-name">${this.user?.name}</span>
            <span class="user-email">${this.user?.email}</span>
          </div>
          <wa-button
            appearance="outlined"
            aria-label="Sign out"
            @click=${this.handleLogout}
          >
            Logout
          </wa-button>
        </div>
      </wa-drawer>
    `;
  }

  private openDrawer(): void {
    this.open = true;
  }

  private handleHide(event: Event): void {
    // Ignore wa-hide events bubbling from nested components (e.g. buttons).
    if ((event.target as HTMLElement).tagName === 'WA-DRAWER') {
      this.open = false;
    }
  }

  private async handleDashboardClick(event: MouseEvent): Promise<void> {
    event.preventDefault();
    this.open = false;
    await navigateTo('/dashboard');
  }

  private async handleMapClick(event: MouseEvent): Promise<void> {
    event.preventDefault();
    this.open = false;
    await navigateTo('/map');
  }

  private async handleThreeClick(event: MouseEvent): Promise<void> {
    event.preventDefault();
    this.open = false;
    await navigateTo('/three');
  }

  private async handleLogout(): Promise<void> {
    this.open = false;
    await signOut();
    await navigateTo('/login');
  }
}
