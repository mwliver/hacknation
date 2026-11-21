import { Component } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';

/** Permanent notice shown on top of AED pages. */
@Component({
  selector: 'app-aed-emergency-banner',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <div class="aed-emergency" role="note">
      <svg class="icon" aria-hidden="true"><use href="/assets/icomoon/sprite/sprite.svg#icon-info"></use></svg>
      <p class="mb-0">
        <strong>{{ 'Aed.Emergency.Text' | translate }}</strong>
        <a class="aed-emergency__call" href="tel:112">{{ 'Aed.Emergency.Call' | translate }}</a>
      </p>
    </div>
  `,
  styles: [
    `
      .aed-emergency {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        background: #b71c1c;
        color: #fff;
        border-radius: 0.25rem;
      }
      .aed-emergency .icon {
        width: 1.5rem;
        height: 1.5rem;
        fill: #fff;
        flex-shrink: 0;
      }
      .aed-emergency__call {
        display: inline-flex;
        align-items: center;
        min-height: 44px;
        min-width: 44px;
        margin-left: 0.5rem;
        padding: 0 0.75rem;
        color: #b71c1c;
        background: #fff;
        border-radius: 0.25rem;
        font-weight: 700;
        text-decoration: none;
      }
      .aed-emergency__call:focus-visible {
        outline: 3px solid #ffd54f;
        outline-offset: 2px;
      }
    `,
  ],
})
export class AedEmergencyBannerComponent {}
