import { isPlatformBrowser, NgFor, NgIf } from '@angular/common';
import {
  AfterViewInit,
  Component,
  DestroyRef,
  ElementRef,
  inject,
  NgZone,
  OnInit,
  PLATFORM_ID,
  signal,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { LayerGroup, Map } from 'leaflet';
import { Subject } from 'rxjs';
import { debounceTime, switchMap } from 'rxjs/operators';

import { AedDetailsComponent } from '@app/pages/aed/components/aed-details/aed-details.component';
import { AedEmergencyBannerComponent } from '@app/pages/aed/components/emergency-banner/aed-emergency-banner.component';
import { AedNearestListComponent } from '@app/pages/aed/components/nearest-list/aed-nearest-list.component';
import { AedGeolocationError, AedGeolocationService } from '@app/pages/aed/services/aed-geolocation.service';
import { activeFiltersCount, DEFAULT_AED_FILTERS, zoomToGeohashPrecision } from '@app/pages/aed/services/aed-filters';
import {
  AED_READINESS_VALUES,
  AedCluster,
  AedFilters,
  AedLocation,
  AedReadiness,
  AedRecord,
} from '@app/pages/aed/services/aed.models';
import { AedBounds, AedService } from '@app/pages/aed/services/aed.service';
import { LeafletService } from '@app/services/leflet.service';
import { NominatimGeocodeService } from '@app/services/nominatim-geocode.service';
import { SeoService } from '@app/services/seo.service';

const POLAND_CENTER: [number, number] = [52.07, 19.48];
const POLAND_ZOOM = 6;
const LOCATED_ZOOM = 15;
const NEAREST_LIMIT = 5;
const NEAREST_MAX_KM = 5;
const IN_VIEW_LIMIT = 100;
const MARKER_COLORS: Record<AedReadiness, string> = {
  GOTOWY: '#1b5e20',
  WYMAGA_UWAGI: '#b35c00',
  NIEZNANY: '#455a64',
  NIEGOTOWY: '#b71c1c',
};

@Component({
  selector: 'app-aed-map',
  standalone: true,
  imports: [
    NgIf,
    NgFor,
    FormsModule,
    TranslatePipe,
    AedEmergencyBannerComponent,
    AedNearestListComponent,
    AedDetailsComponent,
  ],
  templateUrl: './aed-map.component.html',
  styleUrl: './aed-map.component.scss',
})
export class AedMapComponent implements OnInit, AfterViewInit {
  private readonly aedService = inject(AedService);
  private readonly geolocation = inject(AedGeolocationService);
  private readonly geocoder = inject(NominatimGeocodeService);
  private readonly leaflet = inject(LeafletService);
  private readonly translate = inject(TranslateService);
  private readonly seo = inject(SeoService);
  private readonly zone = inject(NgZone);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);

  @ViewChild('mapRef') mapRef: ElementRef<HTMLElement>;
  @ViewChild('addressInput') addressInput: ElementRef<HTMLInputElement>;

  readonly readinessValues = AED_READINESS_VALUES;
  filters: AedFilters = { ...DEFAULT_AED_FILTERS };
  address = '';

  readonly location = signal<AedLocation | null>(null);
  readonly nearest = signal<AedRecord[]>([]);
  readonly inView = signal<AedRecord[]>([]);
  readonly inViewCount = signal(0);
  readonly selected = signal<AedRecord | null>(null);
  readonly loading = signal(false);
  readonly statusMessage = signal('');
  readonly addressError = signal('');

  private map: Map;
  private markersLayer: LayerGroup;
  private userLayer: LayerGroup;
  private readonly boundsChanged$ = new Subject<void>();

  ngOnInit() {
    this.seo.setPageTitleByTranslationKey(['Aed.Map.Title']);
  }

  ngAfterViewInit() {
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }
    this.map = this.leaflet.createMap(this.mapRef, {
      center: POLAND_CENTER,
      zoom: POLAND_ZOOM,
      keyboard: true,
      minZoom: 5,
    });
    this.leaflet
      .tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      })
      .addTo(this.map);
    this.markersLayer = this.leaflet.layerGroup().addTo(this.map);
    this.userLayer = this.leaflet.layerGroup().addTo(this.map);
    this.map.on('moveend', () => this.zone.run(() => this.boundsChanged$.next()));

    this.boundsChanged$
      .pipe(
        debounceTime(300),
        switchMap(() =>
          this.aedService.getInBounds(
            this.bounds(),
            this.filters,
            zoomToGeohashPrecision(this.map.getZoom()),
            IN_VIEW_LIMIT,
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((result) => {
        this.inViewCount.set(result.count);
        this.inView.set(result.count <= IN_VIEW_LIMIT ? result.items : []);
        this.drawMap(
          result.count <= IN_VIEW_LIMIT ? result.items : [],
          result.count > IN_VIEW_LIMIT ? result.clusters : [],
        );
      });
    this.boundsChanged$.next();
  }

  // ------------------------------------------------------------------------------------------------------------
  // Location
  // ------------------------------------------------------------------------------------------------------------

  useMyLocation() {
    this.addressError.set('');
    this.statusMessage.set(this.translate.instant('Aed.Geolocation.Locating'));
    this.geolocation.locate().subscribe({
      next: (location) =>
        this.setLocation({ ...location, label: this.translate.instant('Aed.Geolocation.MyLocation') }),
      error: (reason: AedGeolocationError) => this.onGeolocationError(reason),
    });
  }

  onGeolocationError(reason: AedGeolocationError) {
    const message = this.translate.instant('Aed.Geolocation.' + reason);
    this.statusMessage.set(message);
    this.addressError.set(message);
    this.addressInput?.nativeElement.focus();
  }

  searchAddress() {
    const query = this.address.trim();
    if (query.length < 3) {
      this.addressError.set(this.translate.instant('Aed.Search.TooShort'));
      return;
    }
    this.addressError.set('');
    this.statusMessage.set(this.translate.instant('Aed.Search.Searching'));
    this.geocoder.searchAddress(`${query}, Polska`).subscribe({
      next: (response) => {
        const feature = response?.features?.[0];
        if (!feature) {
          this.addressError.set(this.translate.instant('Aed.Search.NotFound'));
          this.statusMessage.set(this.addressError());
          return;
        }
        const [lon, lat] = feature.geometry.coordinates as unknown as [number, number];
        this.setLocation({ lat, lon, label: feature.properties.display_name });
      },
      error: () => {
        this.addressError.set(this.translate.instant('Aed.Search.Error'));
        this.statusMessage.set(this.addressError());
      },
    });
  }

  setLocation(location: AedLocation) {
    this.location.set(location);
    this.selected.set(null);
    if (this.map) {
      this.userLayer.clearLayers();
      this.leaflet
        .circleMarker([location.lat, location.lon], {
          radius: 9,
          color: '#0052a5',
          fillColor: '#0052a5',
          fillOpacity: 1,
        })
        .bindTooltip(this.translate.instant('Aed.Map.YouAreHere'))
        .addTo(this.userLayer);
      this.map.setView([location.lat, location.lon], LOCATED_ZOOM);
    }
    this.loadNearest();
  }

  loadNearest() {
    const location = this.location();
    if (!location) {
      return;
    }
    this.loading.set(true);
    this.aedService.getNearest(location, this.filters, NEAREST_LIMIT, NEAREST_MAX_KM).subscribe({
      next: (records) => {
        this.nearest.set(records);
        this.loading.set(false);
        this.statusMessage.set(
          records.length
            ? this.translate.instant('Aed.List.FoundNearest', { count: records.length })
            : this.translate.instant('Aed.List.NoneNearby', { km: NEAREST_MAX_KM }),
        );
      },
      error: () => this.loading.set(false),
    });
  }

  // ------------------------------------------------------------------------------------------------------------
  // Filters & selection
  // ------------------------------------------------------------------------------------------------------------

  onFiltersChange() {
    this.loadNearest();
    this.boundsChanged$.next();
  }

  activeFilters(): number {
    return activeFiltersCount(this.filters);
  }

  select(record: AedRecord) {
    this.aedService
      .getDetails(record.id_aed_krajowe)
      .subscribe((details) => this.selected.set({ ...details, odleglosc_m: record.odleglosc_m }));
    if (this.map) {
      this.map.panTo([record.szerokosc_geograficzna, record.dlugosc_geograficzna]);
    }
  }

  closeDetails() {
    this.selected.set(null);
  }

  // ------------------------------------------------------------------------------------------------------------
  // Map drawing
  // ------------------------------------------------------------------------------------------------------------

  private bounds(): AedBounds {
    const b = this.map.getBounds();
    return { minLon: b.getWest(), minLat: b.getSouth(), maxLon: b.getEast(), maxLat: b.getNorth() };
  }

  private drawMap(records: AedRecord[], clusters: AedCluster[]) {
    this.markersLayer.clearLayers();
    clusters.forEach((cluster) => {
      this.leaflet
        .circleMarker([cluster.lat, cluster.lon], {
          radius: Math.min(30, 12 + Math.log2(cluster.liczba + 1) * 3),
          color: '#0052a5',
          fillColor: '#ffffff',
          fillOpacity: 0.9,
          weight: 3,
        })
        .bindTooltip(String(cluster.liczba), { permanent: true, direction: 'center', className: 'aed-cluster-label' })
        .on('click', () => this.map.setView([cluster.lat, cluster.lon], this.map.getZoom() + 2))
        .addTo(this.markersLayer);
    });
    records.forEach((record) => {
      const color = MARKER_COLORS[record.gotowosc] ?? MARKER_COLORS.NIEZNANY;
      this.leaflet
        .circleMarker([record.szerokosc_geograficzna, record.dlugosc_geograficzna], {
          radius: 9,
          color: '#ffffff',
          weight: 2,
          fillColor: color,
          fillOpacity: 1,
        })
        .bindTooltip(`${record.nazwa_obiektu} – ${this.translate.instant('Aed.Readiness.' + record.gotowosc)}`)
        .on('click', () => this.zone.run(() => this.select(record)))
        .addTo(this.markersLayer);
    });
  }
}
