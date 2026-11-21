import { LitElement, css, html } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('forbidden-page')
export class ForbiddenPage extends LitElement {
  static styles = css`
    :host {
      display: block;
      box-sizing: border-box;
      max-width: 100%;
      padding: clamp(1.25rem, 5vw, var(--app-space-8));
      border: 1px solid var(--app-color-border);
      border-radius: var(--app-radius-lg);
      background: var(--app-color-surface);
    }

    h1,
    p {
      overflow-wrap: anywhere;
    }

    p {
      line-height: 1.55;
    }

    a {
      display: inline-flex;
      align-items: center;
      min-height: 2.75rem;
    }
  `;

  render() {
    return html`
      <h1>Access denied</h1>
      <p>You do not have permission to access the requested resource.</p>
      <a href="/dashboard">Return to dashboard</a>
    `;
  }
}
