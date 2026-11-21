import { isPlatformBrowser } from '@angular/common';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { Observable } from 'rxjs';

import { AedLocation } from '@app/pages/aed/services/aed.models';

/** Translation keys (Aed.Geolocation.*) describing why the location could not be read. */
export type AedGeolocationError = 'Denied' | 'Unavailable' | 'Timeout' | 'Unsupported';

/**
 * Thin wrapper over the browser Geolocation API. Errors are mapped to user friendly reasons, so that the UI can
 * explain them and offer the address search instead.
 */
@Injectable({
  providedIn: 'root',
})
export class AedGeolocationService {
  constructor(@Inject(PLATFORM_ID) private platformId: object) {}

  isSupported(): boolean {
    return isPlatformBrowser(this.platformId) && typeof navigator !== 'undefined' && !!navigator.geolocation;
  }

  locate(): Observable<AedLocation> {
    return new Observable<AedLocation>((subscriber) => {
      if (!this.isSupported()) {
        subscriber.error('Unsupported' as AedGeolocationError);
        return;
      }
      navigator.geolocation.getCurrentPosition(
        (position) => {
          subscriber.next({ lat: position.coords.latitude, lon: position.coords.longitude });
          subscriber.complete();
        },
        (error) => subscriber.error(AedGeolocationService.reason(error)),
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 },
      );
    });
  }

  static reason(error: GeolocationPositionError | { code: number }): AedGeolocationError {
    switch (error?.code) {
      case 1:
        return 'Denied';
      case 3:
        return 'Timeout';
      default:
        return 'Unavailable';
    }
  }
}
