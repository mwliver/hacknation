import { PLATFORM_ID } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { AedGeolocationService } from '@app/pages/aed/services/aed-geolocation.service';

describe('AedGeolocationService', () => {
  let service: AedGeolocationService;
  const originalGeolocation = navigator.geolocation;

  const mockGeolocation = (impl: Partial<Geolocation> | undefined) =>
    Object.defineProperty(navigator, 'geolocation', { value: impl, configurable: true });

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [AedGeolocationService, { provide: PLATFORM_ID, useValue: 'browser' }],
    });
    service = TestBed.inject(AedGeolocationService);
  });

  afterEach(() => mockGeolocation(originalGeolocation));

  it('returns the position', (done) => {
    mockGeolocation({
      getCurrentPosition: (success) => success({ coords: { latitude: 52.1, longitude: 21.2 } } as GeolocationPosition),
    });
    service.locate().subscribe((location) => {
      expect(location).toEqual({ lat: 52.1, lon: 21.2 });
      done();
    });
  });

  it('maps a refused permission to "Denied"', (done) => {
    mockGeolocation({
      getCurrentPosition: (_success, error) =>
        error({ code: 1, message: 'User denied Geolocation' } as GeolocationPositionError),
    });
    service.locate().subscribe({
      error: (reason) => {
        expect(reason).toBe('Denied');
        done();
      },
    });
  });

  it('maps timeout and other errors', () => {
    expect(AedGeolocationService.reason({ code: 3 })).toBe('Timeout');
    expect(AedGeolocationService.reason({ code: 2 })).toBe('Unavailable');
  });

  it('reports a browser without geolocation as "Unsupported"', (done) => {
    mockGeolocation(undefined);
    expect(service.isSupported()).toBe(false);
    service.locate().subscribe({
      error: (reason) => {
        expect(reason).toBe('Unsupported');
        done();
      },
    });
  });
});
