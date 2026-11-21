import { NgIf } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LocalizeRouterPipe } from '@gilsdav/ngx-translate-router';
import { TranslatePipe } from '@ngx-translate/core';

export interface AedValidationSummary {
  standard: string;
  zgodny: boolean | null;
  liczba_bledow?: number;
  liczba_ostrzezen?: number;
}

/**
 * "AED v1 standard" badge with the validation status, shown on dataset and resource pages.
 * Rendered only for resources marked as AED v1 by a backend with AED enabled (``aed_validation`` is not null).
 */
@Component({
  selector: 'app-aed-standard-badge',
  standalone: true,
  imports: [NgIf, RouterLink, LocalizeRouterPipe, TranslatePipe],
  template: `
    <span *ngIf="visible()" class="aed-standard" [class.aed-standard--error]="status() === 'errors'">
      <span class="aed-standard__name">{{ 'Aed.Badge.Standard' | translate }}</span>
      <span class="aed-standard__status">
        <span aria-hidden="true">{{ status() === 'compliant' ? '✔' : status() === 'errors' ? '✖' : '…' }}</span>
        {{ 'Aed.Badge.' + status() | translate: { errors: validation()?.liczba_bledow } }}
      </span>
      <a
        *ngIf="resourceId() && status() !== 'pending'"
        class="aed-standard__link"
        [routerLink]="['/!aed', '!udostepnij'] | localize"
        [queryParams]="{ raport: resourceId() }">
        {{ 'Aed.Badge.ShowReport' | translate }}
      </a>
    </span>
  `,
  styles: [
    `
      .aed-standard {
        display: inline-flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.5rem;
        padding: 0.25rem 0.6rem;
        border: 1px solid #1b5e20;
        border-radius: 0.25rem;
        color: #1b5e20;
        background: #e8f5e9;
        font-size: 0.875rem;
      }
      .aed-standard--error {
        border-color: #b71c1c;
        color: #b71c1c;
        background: #ffebee;
      }
      .aed-standard__name {
        font-weight: 700;
      }
      .aed-standard__link {
        color: inherit;
        text-decoration: underline;
      }
    `,
  ],
})
export class AedStandardBadgeComponent {
  readonly dataStandard = input<string | null>(null);
  readonly validation = input<AedValidationSummary | null>(null);
  readonly resourceId = input<string | number | null>(null);

  readonly visible = computed(() => this.dataStandard() === 'AED_V1' && !!this.validation());
  readonly status = computed(() => {
    const value = this.validation()?.zgodny;
    return value === true ? 'compliant' : value === false ? 'errors' : 'pending';
  });
}
