import { isPlatformBrowser, NgClass, NgFor, NgIf } from '@angular/common';
import {
  Component,
  computed,
  ElementRef,
  inject,
  OnInit,
  PLATFORM_ID,
  QueryList,
  signal,
  ViewChildren,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { map } from 'rxjs/operators';

import { AedEmergencyBannerComponent } from '@app/pages/aed/components/emergency-banner/aed-emergency-banner.component';
import { AedValidationReportComponent } from '@app/pages/aed/components/validation-report/aed-validation-report.component';
import { AedSchema, AedSchemaField, AedValidationReport } from '@app/pages/aed/services/aed.models';
import { AedService } from '@app/pages/aed/services/aed.service';
import { SeoService } from '@app/services/seo.service';

export const AED_ALLOWED_EXTENSIONS = ['csv', 'xlsx'];
export const AED_MAX_FILE_SIZE_MB = 10;
export const AED_ADMIN_PANEL_URL = 'https://admin.dane.gov.pl';

/** Data provider wizard /aed/udostepnij: template -> upload & check -> report -> how to publish. */
@Component({
  selector: 'app-aed-share',
  standalone: true,
  imports: [NgIf, NgFor, NgClass, TranslatePipe, AedEmergencyBannerComponent, AedValidationReportComponent],
  templateUrl: './aed-share.component.html',
  styleUrl: './aed-share.component.scss',
})
export class AedShareComponent implements OnInit {
  private readonly aedService = inject(AedService);
  private readonly translate = inject(TranslateService);
  private readonly route = inject(ActivatedRoute);
  private readonly seo = inject(SeoService);
  private readonly platformId = inject(PLATFORM_ID);

  @ViewChildren('stepHeading') stepHeadings: QueryList<ElementRef<HTMLElement>>;

  readonly steps = [1, 2, 3, 4];
  readonly step = signal(1);
  readonly schema = signal<AedSchema | null>(null);
  readonly file = signal<File | null>(null);
  readonly fileError = signal('');
  readonly validating = signal(false);
  readonly report = signal<AedValidationReport | null>(null);
  readonly reportForResource = signal<string | null>(null);
  readonly adminPanelUrl = AED_ADMIN_PANEL_URL;
  readonly maxSizeMb = AED_MAX_FILE_SIZE_MB;

  private readonly lang = toSignal(this.translate.onLangChange.pipe(map((e) => e.lang)), {
    initialValue: this.translate.currentLang,
  });
  readonly fields = computed(() => this.schema()?.fields ?? []);
  readonly fileRules = computed(() => this.schema()?.['x-aed-file-rules'] ?? []);

  ngOnInit() {
    this.seo.setPageTitleByTranslationKey(['Aed.Share.Title']);
    this.aedService.getSchema().subscribe((schema) => this.schema.set(schema));
    const resourceId = this.route.snapshot.queryParamMap.get('raport');
    if (resourceId) {
      this.reportForResource.set(resourceId);
      this.aedService.getResourceReport(resourceId).subscribe({
        next: (report) => {
          this.report.set(report);
          this.goTo(3);
        },
        error: () => this.reportForResource.set(null),
      });
    }
  }

  text(value: { pl: string; en: string }): string {
    return this.lang() === 'en' ? value.en : value.pl;
  }

  presenceKey(field: AedSchemaField): string {
    return 'Aed.Share.Presence.' + field['x-aed-presence'];
  }

  templateUrl(format: 'csv' | 'xlsx'): string {
    return this.aedService.templateUrl(format);
  }

  goTo(step: number) {
    this.step.set(step);
    if (isPlatformBrowser(this.platformId)) {
      setTimeout(() =>
        this.stepHeadings?.find((h) => h.nativeElement.dataset['step'] === String(step))?.nativeElement.focus(),
      );
    }
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.fileError.set(this.checkFile(file));
    this.file.set(this.fileError() ? null : file);
  }

  checkFile(file: File | null): string {
    if (!file) {
      return this.translate.instant('Aed.Share.Upload.NoFile');
    }
    const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : '';
    if (!AED_ALLOWED_EXTENSIONS.includes(ext)) {
      return this.translate.instant('Aed.Share.Upload.WrongType');
    }
    if (file.size > AED_MAX_FILE_SIZE_MB * 1024 * 1024) {
      return this.translate.instant('Aed.Share.Upload.TooLarge', { mb: AED_MAX_FILE_SIZE_MB });
    }
    return '';
  }

  validate() {
    const file = this.file();
    const error = this.checkFile(file);
    this.fileError.set(error);
    if (error) {
      return;
    }
    this.validating.set(true);
    this.reportForResource.set(null);
    this.aedService.validateFile(file).subscribe({
      next: (report) => {
        this.validating.set(false);
        this.report.set(report);
        this.goTo(3);
      },
      error: () => {
        this.validating.set(false);
        this.fileError.set(this.translate.instant('Aed.Share.Upload.ServerError'));
      },
    });
  }
}
