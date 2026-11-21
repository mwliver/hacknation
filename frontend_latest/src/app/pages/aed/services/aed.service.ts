import { DOCUMENT } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { CookieService } from 'ngx-cookie-service';
import { LocalStorageService } from 'ngx-localstorage';
import { Observable, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

import {
  AedConfig,
  AedFilters,
  AedListResult,
  AedLocation,
  AedRecord,
  AedSchema,
  AedStats,
  AedValidationReport,
} from '@app/pages/aed/services/aed.models';
import { filtersToParams } from '@app/pages/aed/services/aed-filters';
import { ApiConfig } from '@app/services/api';
import { LoginService } from '@app/services/login-service';
import { NotificationsService } from '@app/services/notifications.service';
import { RestService } from '@app/services/rest.service';
import { TemplateHelper } from '@app/shared/helpers';

export interface AedBounds {
  minLon: number;
  minLat: number;
  maxLon: number;
  maxLat: number;
}

/**
 * Client of the AED API (backend app mcod/aed). Endpoints exist only when the backend runs with AED_ENABLED=True.
 */
@Injectable({
  providedIn: 'root',
})
export class AedService extends RestService {
  private config$: Observable<AedConfig | null>;

  constructor(
    protected http: HttpClient,
    public translate: TranslateService,
    public router: Router,
    public notificationService: NotificationsService,
    public storageService: LocalStorageService,
    public cookieService: CookieService,
    public loginService: LoginService,
    @Inject(DOCUMENT) public document: Document,
    @Inject(PLATFORM_ID) public platformId: string,
  ) {
    super(
      http,
      translate,
      router,
      notificationService,
      storageService,
      cookieService,
      loginService,
      document,
      platformId,
    );
  }

  /** Campaign config; ``null`` when the AED feature is disabled in the backend (route returns 404). */
  getConfig(): Observable<AedConfig | null> {
    if (!this.config$) {
      this.config$ = this.get(ApiConfig.aedConfig, undefined, true).pipe(
        map((res) => res.data.attributes as AedConfig),
        catchError(() => of(null)),
        shareReplay(1),
      );
    }
    return this.config$;
  }

  getStats(): Observable<AedStats> {
    return this.get(ApiConfig.aedStats).pipe(map((res) => res.data.attributes as AedStats));
  }

  getSchema(): Observable<AedSchema> {
    return this.get(ApiConfig.aedSchema);
  }

  getNearest(location: AedLocation, filters: AedFilters, limit = 5, maxKm = 2): Observable<AedRecord[]> {
    const params = new HttpParams({
      fromObject: { lat: location.lat, lon: location.lon, limit, max_km: maxKm, ...filtersToParams(filters) },
    });
    return this.get(ApiConfig.aedNearest, params).pipe(map((res) => this.records(res)));
  }

  getInBounds(
    bounds: AedBounds,
    filters: AedFilters,
    precision: number,
    perPage = 100,
    page = 1,
  ): Observable<AedListResult> {
    const bbox = [bounds.minLon, bounds.minLat, bounds.maxLon, bounds.maxLat].map((v) => v.toFixed(5)).join(',');
    const params = new HttpParams({
      fromObject: { bbox, klastry: 'true', precyzja: precision, per_page: perPage, page, ...filtersToParams(filters) },
    });
    return this.get(ApiConfig.aed, params).pipe(
      map((res) => ({
        items: this.records(res),
        count: res.meta?.count ?? 0,
        clusters: res.meta?.aggregations?.klastry ?? [],
      })),
    );
  }

  getDetails(id: string): Observable<AedRecord> {
    return this.get(TemplateHelper.parseUrl(ApiConfig.aedDetails, { id })).pipe(
      map((res) => res.data.attributes as AedRecord),
    );
  }

  getResourceReport(resourceId: string | number): Observable<AedValidationReport> {
    const url = TemplateHelper.parseUrl(ApiConfig.aedReport, { resourceId: String(resourceId) });
    return this.get(url, undefined, true).pipe(map((res) => res.data.attributes as AedValidationReport));
  }

  /** Checks a file against the AED v1 standard. Nothing is published or stored by the backend. */
  validateFile(file: File): Observable<AedValidationReport> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.post(ApiConfig.aedValidate, form).pipe(map((res) => res.data.attributes as AedValidationReport));
  }

  templateUrl(format: 'csv' | 'xlsx'): string {
    return this.base_url + (format === 'csv' ? ApiConfig.aedTemplateCsv : ApiConfig.aedTemplateXlsx);
  }

  private records(res: { data?: { attributes: AedRecord }[] }): AedRecord[] {
    return (res?.data ?? []).map((item) => item.attributes);
  }
}
