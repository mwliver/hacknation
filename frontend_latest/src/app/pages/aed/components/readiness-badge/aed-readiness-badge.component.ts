import { Component, computed, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';

import { READINESS_PRESENTATION } from '@app/pages/aed/services/aed-filters';
import { AedReadiness } from '@app/pages/aed/services/aed.models';

/** Readiness shown as text + icon + colour (never colour only – WCAG 1.4.1). */
@Component({
  selector: 'app-aed-readiness-badge',
  standalone: true,
  imports: [TranslatePipe],
  template: `
    <span class="aed-readiness {{ presentation().css }}">
      <span class="aed-readiness__icon" aria-hidden="true">{{ presentation().icon }}</span>
      <span class="visually-hidden">{{ 'Aed.Readiness.Label' | translate }}:</span>
      {{ 'Aed.Readiness.' + readiness() | translate }}
    </span>
  `,
  styleUrl: './aed-readiness-badge.component.scss',
})
export class AedReadinessBadgeComponent {
  readonly readiness = input.required<AedReadiness>();
  readonly presentation = computed(() => READINESS_PRESENTATION[this.readiness()] ?? READINESS_PRESENTATION.NIEZNANY);
}
