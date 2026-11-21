import { DOCUMENT, NgFor, NgIf } from '@angular/common';
import { AfterViewInit, Component, computed, ElementRef, inject, input, output, ViewChild } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LocalizeRouterPipe } from '@gilsdav/ngx-translate-router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';

import { AedReadinessBadgeComponent } from '@app/pages/aed/components/readiness-badge/aed-readiness-badge.component';
import { formatDistance, navigationUrl } from '@app/pages/aed/services/aed-filters';
import { AedRecord } from '@app/pages/aed/services/aed.models';

/** Details of one AED. Receives focus when opened, so keyboard and screen reader users land on it. */
@Component({
  selector: 'app-aed-details',
  standalone: true,
  imports: [NgIf, NgFor, RouterLink, LocalizeRouterPipe, TranslatePipe, AedReadinessBadgeComponent],
  templateUrl: './aed-details.component.html',
  styleUrl: './aed-details.component.scss',
})
export class AedDetailsComponent implements AfterViewInit {
  private readonly document = inject(DOCUMENT);
  private readonly translate = inject(TranslateService);

  readonly record = input.required<AedRecord>();
  readonly closed = output<void>();

  @ViewChild('heading') heading: ElementRef<HTMLElement>;

  readonly address = computed(() => {
    const r = this.record();
    const street = [r.ulica, r.nr_budynku].filter(Boolean).join(' ');
    return [street, [r.kod_pocztowy, r.miejscowosc].filter(Boolean).join(' ')].filter(Boolean).join(', ');
  });

  readonly navigateUrl = computed(() =>
    navigationUrl(this.record(), this.document.defaultView?.navigator?.userAgent ?? ''),
  );

  /** Problem report goes to the source resource of the winning data provider (existing feedback form). */
  readonly reportSource = computed(() => this.record().zrodla?.find((s) => s.zasob_id && s.zbior_id) ?? null);
  readonly reportUrl = computed(() => {
    const source = this.reportSource();
    if (!source) {
      return null;
    }
    const origin = this.document.location?.origin ?? '';
    return `${origin}/${this.translate.currentLang}/dataset/${source.zbior_id}/resource/${source.zasob_id}`;
  });

  ngAfterViewInit() {
    this.heading?.nativeElement.focus();
  }

  distance(): string {
    return formatDistance(this.record().odleglosc_m, this.translate.currentLang);
  }

  close() {
    this.closed.emit();
  }
}
