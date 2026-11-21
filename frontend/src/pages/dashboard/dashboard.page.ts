import { createQuery, queryOptions } from '@/api/endpoints/create-query';
import type { CreateUserRequest, UserModel } from '@/api/models/user.model';
import { delayResolve } from '@/utils/delay-resolve';
import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { navigateTo } from '../../app/router';
import { loginStore, clearSession } from '../../auth/auth.api';

const users: UserModel[] = [];
const allUsers = createQuery(async () => users);
const createNewUser = createQuery(async (userModel: CreateUserRequest) => {
  await delayResolve(2000, null);
  users.push({
    id: Math.random().toString(),
    ...userModel,
  });
  allUsers.call(queryOptions({ ignoreCache: true, keepPreviousData: true }));
});

@customElement('dashboard-page')
export class DashboardPage extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    section {
      margin-top: var(--app-space-6);
      padding: var(--app-space-6);
      border: 1px solid var(--app-color-border);
      border-radius: var(--app-radius-md);
      background: var(--app-color-surface);
    }

    h1,
    h2,
    p {
      overflow-wrap: anywhere;
    }

    h1 {
      font-size: clamp(1.5rem, 6vw, 2rem);
    }

    wa-button {
      min-height: 2.75rem;
      max-width: 100%;
    }

    .muted {
      color: var(--app-color-text-muted);
    }

    .error {
      color: var(--app-color-error);
    }

    @media (max-width: 40rem) {
      section {
        margin-top: var(--app-space-4);
        padding: var(--app-space-4);
      }

      section wa-button {
        display: block;
        width: 100%;
        margin-block: var(--app-space-2);
      }
    }
  `;

  @property()
  section = '';


  render() {
    loginStore.observe(this)
    allUsers.observe(this);
    createNewUser.observe(this);
    const currentUser = loginStore.get();
    return html`
      <h1>Dashboard${this.section ? `: ${this.section}` : ''}</h1>
      <p class="muted">
        You are signed in as ${currentUser?.email}
        (${currentUser?.email}).
      </p>
      <wa-button variant="brand" @click=${this.handleLogout}
        >Sign out</wa-button
      >

      <section>
        <h2>Server-state example</h2>
        <p class="muted">
          This optional sample calls <code>UsersApi.getAll()</code> and
          demonstrates query caching. Configure an API server to load data.
        </p>
        <wa-button
          appearance="outlined"
          ?disabled=${allUsers.isLoading}
          @click=${() => void allUsers.call()}
          >${allUsers.isLoading ? 'Loading…' : 'Load users'}</wa-button
        >
        ${
          allUsers.isError
            ? html`<p class="error" role="alert">${allUsers.error.message}</p>`
            : ''
        }
        ${allUsers.data ? html`<p>${allUsers.data.length} users loaded.</p>` : ''}
        <wa-button
          appearance="outlined"
          ?disabled=${createNewUser.isLoading}
          @click=${this.createSampleUser}
        >
          ${createNewUser.isLoading ? 'Creating...' : 'Create sample user'}
        </wa-button>
        ${
          createNewUser.isError
            ? html`<p class="error" role="alert">
                ${createNewUser.error.message}
              </p>`
            : ''
        }
      </section>
    `;
  }

  private async handleLogout(): Promise<void> {
    await clearSession();
    await navigateTo('/login');
  }

  private async createSampleUser(): Promise<void> {
    await createNewUser.call({
      name: 'Sample User',
      email: `sample-${Date.now()}@example.test`,
    });
  }
}
