import { loginStore } from '@/auth/auth.api';
import { LitElement, css, html } from 'lit';
import { customElement } from 'lit/decorators.js';
import { navigateTo } from '../../app/router';
import { isSafeReturnTo } from '../../auth/auth.guard';
import { createQuery } from '@/api/endpoints/create-query';
import { delayResolve } from '@/utils/delay-resolve';
import type { LoginCredential, User } from '@/auth/auth.types';
import { users } from '@/auth/auth.mocks';

@customElement('login-page')
export class LoginPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      box-sizing: border-box;
      width: min(100%, 28rem);
      margin: clamp(0rem, 5vh, 3rem) auto;
      padding: clamp(1.25rem, 5vw, var(--app-space-8));
      border: 1px solid var(--app-color-border);
      border-radius: var(--app-radius-lg);
      background: var(--app-color-surface);
    }

    h1 {
      margin: 0 0 var(--app-space-3);
      font-size: clamp(1.5rem, 6vw, 2rem);
    }

    p {
      line-height: 1.55;
    }

    form {
      display: grid;
      gap: var(--app-space-4);
    }

    wa-input,
    wa-button {
      display: block;
      width: 100%;
      min-width: 0;
    }

    wa-input {
      --wa-form-control-border-color: #68758a;
    }

    wa-input:hover {
      --wa-form-control-border-color: var(--wa-color-neutral-border-loud);
    }

    wa-input:focus-within {
      --wa-form-control-border-color: var(--wa-form-control-activated-color);
    }

    wa-button {
      min-height: 2.75rem;
      margin-top: var(--app-space-2);
    }

    wa-button[disabled] {
      opacity: 0.58;
    }

    .error {
      color: var(--app-color-error);
      overflow-wrap: anywhere;
    }

    @media (max-width: 40rem) {
      :host {
        margin-block: 0.5rem;
        border-radius: var(--app-radius-md);
      }
    }
  `;

  render() {
    loginStore.observe(this);
    dummyLogin.observe(this);

    return html`
      <h1>Sign in</h1>
      <p>Use any email and password to enter the prototype.</p>
      <form @submit=${this.handleSubmit}>
        <wa-input
          label="Email"
          name="email"
          type="email"
          placeholder="you@example.com"
          autocomplete="username"
          required
        ></wa-input>
        <wa-input
          label="Password"
          name="password"
          type="password"
          placeholder="Enter your password"
          autocomplete="current-password"
          required
        ></wa-input>
        <wa-button
          type="submit"
          variant="brand"
          .disabled=${dummyLogin.isLoading}
        >
          ${dummyLogin.isLoading ? 'Signing in' : 'Sign in'}
        </wa-button>
      </form>
    `;
  }

  private async handleSubmit(event: SubmitEvent): Promise<void> {
    event.preventDefault();
    const form = event.currentTarget;
    if (!(form instanceof HTMLFormElement)) return;
    const data = new FormData(form);

    const email = String(data.get('email') ?? '');
    const password = String(data.get('password') ?? '');

    const user = await dummyLogin.call({ email, password });

    if (!user) return;

    loginStore.set(user);

    const returnTo = new URLSearchParams(window.location.search).get(
      'returnTo',
    );
    await navigateTo(isSafeReturnTo(returnTo) ? returnTo : '/dashboard');
  }
}

export const findUser = ({
  email,
  password,
}: LoginCredential): User | undefined => {
  return users.find(
    (user) => user.email === email && user.password === password,
  );
};

const dummyLogin = createQuery((user: LoginCredential) =>
  delayResolve(500, findUser(user)),
);
