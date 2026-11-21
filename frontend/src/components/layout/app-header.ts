import { LitElement, css, html } from 'lit';
import { customElement } from 'lit/decorators.js';

@customElement('app-header')
export class AppHeader extends LitElement {
  static styles = css`
    :host {
      display: block;
      border-bottom: 1px solid var(--app-color-border);
      background: var(--app-color-surface);
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--app-space-4);
      width: min(calc(100% - 2rem), 72rem);
      min-height: 4rem;
      margin: 0 auto;
      padding-block: var(--app-space-2);
    }

    a {
      color: var(--app-color-text);
      font-weight: 700;
      text-decoration: none;
    }

    .start {
      display: flex;
      gap: var(--app-space-3);
      min-width: 0;
    }

    ::slotted(nav) {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--app-space-3);
      min-width: 0;
    }

    @media (max-width: 40rem) {
      header {
        width: calc(100% - 1.5rem);
        gap: var(--app-space-2);
        min-height: 3.75rem;
      }

      ::slotted(nav) {
        gap: var(--app-space-1);
      }
    }
  `;

  render() {
    return html`
      <header>
        <div class="start">
          <slot name="start"></slot>
          <wa-button
            size="s"
            appearance="outlined"
            aria-label="Navigate to dashboard"
            href="/dashboard"
            >Hacknation 2026</wa-button
          >
        </div>
        <slot> </slot>
      </header>
    `;
  }
}
