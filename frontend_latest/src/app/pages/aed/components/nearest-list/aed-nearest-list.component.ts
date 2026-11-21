import { NgFor, NgIf } from '@angular/common';
import { Component, inject, input, output } from '@angular/core';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';

import { AedReadinessBadgeComponent } from '@app/pages/aed/components/readiness-badge/aed-readiness-badge.component';
import { formatDistance } from '@app/pages/aed/services/aed-filters';
import { AedRecord } from '@app/pages/aed/services/aed.models';

/**
 * Text list of AEDs – the equivalent of the map (everything visible on the map can be found here).
 * Shows distance, facility, location description, hours, "open now" and readiness (text + icon).
 */
@Component({
  selector: 'app-aed-nearest-list',
  standalone: true,
  imports: [NgFor, NgIf, TranslatePipe, AedReadinessBadgeComponent],
  templateUrl: './aed-nearest-list.component.html',
  styleUrl: './aed-nearest-list.component.scss',
})
export class AedNearestListComponent {
  private readonly translate = inject(TranslateService);

  readonly records = input<AedRecord[]>([]);
  readonly selectedId = input<string | null>(null);
  readonly emptyMessageKey = input<string>('Aed.List.Empty');
  readonly listLabelKey = input<string>('Aed.List.NearestLabel');
  readonly selected = output<AedRecord>();

  distance(record: AedRecord): string {
    return formatDistance(record.odleglosc_m, this.translate.currentLang);
  }

  openNowKey(record: AedRecord): string {
    if (record.otwarte_teraz === true) {
      return 'Aed.OpenNow.Open';
    }
    return record.otwarte_teraz === false ? 'Aed.OpenNow.Closed' : 'Aed.OpenNow.Unknown';
  }

  select(record: AedRecord) {
    this.selected.emit(record);
  }

  trackById(_: number, record: AedRecord) {
    return record.id_aed_krajowe;
  }
}
