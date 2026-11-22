import { DOCUMENT } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { EMPTY } from 'rxjs';

import { AedService } from '@app/pages/aed/services/aed.service';
import { AedShareComponent } from '@app/pages/aed/share/aed-share.component';
import { SeoService } from '@app/services/seo.service';
import { environment } from '@env/environment';

describe('AedShareComponent admin panel link', () => {
  const originalProduction = environment.production;

  afterEach(() => {
    environment.production = originalProduction;
  });

  it.each([
    [false, 'localhost', 'https://admin.mcod.local'],
    [true, 'www.dane.gov.pl', 'https://admin.dane.gov.pl'],
    [true, 'int.dane.gov.pl', 'https://admin.int.dane.gov.pl'],
  ])('links to the correct panel for production=%s and hostname=%s', (production, hostname, expected) => {
    environment.production = production;
    TestBed.configureTestingModule({
      providers: [
        { provide: DOCUMENT, useValue: { location: { protocol: 'https:', hostname } } },
        { provide: AedService, useValue: {} },
        { provide: ActivatedRoute, useValue: {} },
        { provide: SeoService, useValue: {} },
        { provide: TranslateService, useValue: { onLangChange: EMPTY, currentLang: 'pl' } },
      ],
    });

    const component = TestBed.runInInjectionContext(() => new AedShareComponent());
    expect(component.adminPanelUrl).toBe(expected);
  });
});
