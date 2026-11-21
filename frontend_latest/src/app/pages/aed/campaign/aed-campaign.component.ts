import { AsyncPipe, DecimalPipe, NgIf } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LocalizeRouterPipe } from '@gilsdav/ngx-translate-router';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AedEmergencyBannerComponent } from '@app/pages/aed/components/emergency-banner/aed-emergency-banner.component';
import { AedConfig, AedStats } from '@app/pages/aed/services/aed.models';
import { AedService } from '@app/pages/aed/services/aed.service';
import { SeoService } from '@app/services/seo.service';

/** Campaign page /aed: name, slogan and logo from backend config (AED_CAMPAIGN_*), counters and two main actions. */
@Component({
  selector: 'app-aed-campaign',
  standalone: true,
  imports: [NgIf, AsyncPipe, DecimalPipe, RouterLink, LocalizeRouterPipe, TranslatePipe, AedEmergencyBannerComponent],
  templateUrl: './aed-campaign.component.html',
  styleUrl: './aed-campaign.component.scss',
})
export class AedCampaignComponent implements OnInit {
  private readonly aedService = inject(AedService);
  private readonly seo = inject(SeoService);

  config$: Observable<AedConfig | null>;
  stats$: Observable<AedStats | null>;

  ngOnInit() {
    this.seo.setPageTitleByTranslationKey(['Aed.Campaign.Title']);
    this.config$ = this.aedService.getConfig();
    this.stats$ = this.aedService.getStats().pipe(catchError(() => of(null)));
  }
}
