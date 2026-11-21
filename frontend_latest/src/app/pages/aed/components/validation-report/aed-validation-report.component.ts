import { isPlatformBrowser, NgClass, NgFor, NgIf } from '@angular/common';
import { Component, computed, inject, input, PLATFORM_ID, signal } from '@angular/core';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';

import { filterIssues, issuesToCsv } from '@app/pages/aed/services/aed-filters';
import { AedIssue, AedValidationReport } from '@app/pages/aed/services/aed.models';

export type AedIssueLevelFilter = 'ALL' | 'ERROR' | 'WARNING';

/** Validation report: summary, error/warning filter, table of problems and CSV export. */
@Component({
  selector: 'app-aed-validation-report',
  standalone: true,
  imports: [NgIf, NgFor, NgClass, TranslatePipe],
  templateUrl: './aed-validation-report.component.html',
  styleUrl: './aed-validation-report.component.scss',
})
export class AedValidationReportComponent {
  private readonly translate = inject(TranslateService);
  private readonly platformId = inject(PLATFORM_ID);

  readonly report = input.required<AedValidationReport>();
  readonly fileName = input<string>('');
  readonly headingLevel = input<2 | 3>(2);

  readonly level = signal<AedIssueLevelFilter>('ALL');
  readonly levels: AedIssueLevelFilter[] = ['ALL', 'ERROR', 'WARNING'];
  readonly issues = computed(() => filterIssues(this.report().problemy, this.level()));

  message(issue: AedIssue): string {
    return this.translate.currentLang === 'en' ? issue.komunikat_en : issue.komunikat_pl;
  }

  setLevel(level: AedIssueLevelFilter) {
    this.level.set(level);
  }

  exportCsv() {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    const csv = issuesToCsv(this.issues(), this.translate.currentLang);
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `raport_AED_v1${this.fileName() ? '_' + this.fileName().replace(/\.[^.]+$/, '') : ''}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }
}
