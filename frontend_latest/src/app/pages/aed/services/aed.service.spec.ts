import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { CookieService } from 'ngx-cookie-service';
import { provideNgxLocalstorage } from 'ngx-localstorage';

import { DEFAULT_AED_FILTERS } from '@app/pages/aed/services/aed-filters';
import { AedService } from '@app/pages/aed/services/aed.service';
import { NotificationsService } from '@app/services/notifications.service';

describe('AedService', () => {
  let service: AedService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    // like ServiceTestbed, but provideHttpClientTesting() must come after provideHttpClient(),
    // otherwise the real HTTP backend is used and requests cannot be asserted
    TestBed.configureTestingModule({
      imports: [TranslateModule.forRoot()],
      providers: [
        AedService,
        NotificationsService,
        CookieService,
        provideNgxLocalstorage({ prefix: 'mcod' }),
        provideRouter([]),
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    });
    service = TestBed.inject(AedService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('requests nearest AEDs with location, limit and active filters only', () => {
    let result;
    service
      .getNearest({ lat: 52.105, lon: 21.26 }, { ...DEFAULT_AED_FILTERS, openNow: true }, 5, 2)
      .subscribe((records) => (result = records));

    const req = httpMock.expectOne((r) => r.url.endsWith('/aed/nearest'));
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('lat')).toBe('52.105');
    expect(req.request.params.get('lon')).toBe('21.26');
    expect(req.request.params.get('limit')).toBe('5');
    expect(req.request.params.get('max_km')).toBe('2');
    expect(req.request.params.get('otwarte_teraz')).toBe('true');
    expect(req.request.params.has('dostep_publiczny')).toBe(false);
    req.flush({ data: [{ attributes: { id_aed_krajowe: 'a', odleglosc_m: 12 } }] });

    expect(result).toEqual([{ id_aed_krajowe: 'a', odleglosc_m: 12 }]);
  });

  it('requests AEDs in map bounds with clusters and maps meta', () => {
    let result;
    service
      .getInBounds({ minLon: 21, minLat: 52, maxLon: 21.5, maxLat: 52.3 }, DEFAULT_AED_FILTERS, 4)
      .subscribe((r) => (result = r));

    const req = httpMock.expectOne((r) => r.url.endsWith('/aed'));
    expect(req.request.params.get('bbox')).toBe('21.00000,52.00000,21.50000,52.30000');
    expect(req.request.params.get('klastry')).toBe('true');
    expect(req.request.params.get('precyzja')).toBe('4');
    req.flush({
      data: [],
      meta: { count: 250, aggregations: { klastry: [{ geohash: 'u3q', liczba: 250, lat: 52, lon: 21 }] } },
    });

    expect(result.count).toBe(250);
    expect(result.clusters.length).toBe(1);
    expect(result.items).toEqual([]);
  });

  it('sends the file as multipart form data to validation', () => {
    let report;
    const file = new File(['id_aed\n'], 'aed.csv', { type: 'text/csv' });
    service.validateFile(file).subscribe((r) => (report = r));

    const req = httpMock.expectOne((r) => r.url.endsWith('/aed/validate'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body instanceof FormData).toBe(true);
    expect((req.request.body as FormData).get('file')).toBeTruthy();
    req.flush({ data: { attributes: { zgodny: false, liczba_bledow: 2, problemy: [] } } });

    expect(report.liczba_bledow).toBe(2);
  });

  it('returns null config when the AED feature is disabled (404) and caches the answer', () => {
    const values = [];
    service.getConfig().subscribe((c) => values.push(c));
    httpMock.expectOne((r) => r.url.endsWith('/aed/config')).flush({}, { status: 404, statusText: 'Not Found' });
    service.getConfig().subscribe((c) => values.push(c));
    httpMock.expectNone((r) => r.url.endsWith('/aed/config'));
    expect(values).toEqual([null, null]);
  });

  it('builds template download urls', () => {
    expect(service.templateUrl('csv')).toMatch(/\/aed\/template\.csv$/);
    expect(service.templateUrl('xlsx')).toMatch(/\/aed\/template\.xlsx$/);
  });
});
