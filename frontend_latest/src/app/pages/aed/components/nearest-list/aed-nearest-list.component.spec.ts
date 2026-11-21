import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AedNearestListComponent } from '@app/pages/aed/components/nearest-list/aed-nearest-list.component';
import { AedRecord } from '@app/pages/aed/services/aed.models';

const aed = (overrides: Partial<AedRecord>): AedRecord =>
  ({
    id_aed_krajowe: '1',
    nazwa_obiektu: 'Dworzec Testowy',
    opis_lokalizacji: 'hol główny',
    miejscowosc: 'Otwock',
    ulica: 'ul. Testowa',
    nr_budynku: '1',
    godziny_dostepnosci: '24/7',
    otwarte_teraz: true,
    gotowosc: 'GOTOWY',
    dostep_publiczny: true,
    wymaga_kodu_lub_klucza: false,
    odleglosc_m: 120,
    ...overrides,
  }) as AedRecord;

describe('AedNearestListComponent', () => {
  let fixture: ComponentFixture<AedNearestListComponent>;
  const el = () => fixture.nativeElement as HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AedNearestListComponent, TranslateModule.forRoot()],
    }).compileComponents();
    TestBed.inject(TranslateService).use('pl');
    fixture = TestBed.createComponent(AedNearestListComponent);
  });

  it('renders an ordered list with distance, facility, hours and readiness as text', () => {
    fixture.componentRef.setInput('records', [
      aed({}),
      aed({
        id_aed_krajowe: '2',
        nazwa_obiektu: 'Przychodnia',
        odleglosc_m: 1530,
        otwarte_teraz: null,
        gotowosc: 'NIEZNANY',
      }),
    ]);
    fixture.detectChanges();

    const items = el().querySelectorAll('[data-test="aed-list-item"]');
    expect(el().querySelector('ol')).not.toBeNull();
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('Dworzec Testowy');
    expect(items[0].querySelector('[data-test="aed-distance"]').textContent).toContain('120 m');
    expect(items[1].querySelector('[data-test="aed-distance"]').textContent).toContain('1,5 km');
    expect(items[0].textContent).toContain('24/7');
    expect(items[0].textContent).toContain('Aed.OpenNow.Open');
    expect(items[1].textContent).toContain('Aed.OpenNow.Unknown');
    // readiness is a text label, not only a colour
    expect(items[0].querySelector('.aed-readiness').textContent).toContain('Aed.Readiness.GOTOWY');
    expect(items[1].querySelector('.aed-readiness').classList).toContain('aed-readiness--unknown');
  });

  it('informs about restricted access and the cabinet code from the dispatcher', () => {
    fixture.componentRef.setInput('records', [aed({ dostep_publiczny: false, wymaga_kodu_lub_klucza: true })]);
    fixture.detectChanges();
    expect(el().textContent).toContain('Aed.Access.StaffOnly');
    expect(el().textContent).toContain('Aed.Access.CodeFromDispatcher');
  });

  it('emits the selected AED and marks it', () => {
    const record = aed({});
    fixture.componentRef.setInput('records', [record]);
    const emitted: AedRecord[] = [];
    fixture.componentInstance.selected.subscribe((r) => emitted.push(r));
    fixture.detectChanges();

    (el().querySelector('[data-test="aed-list-details"]') as HTMLButtonElement).click();
    fixture.componentRef.setInput('selectedId', '1');
    fixture.detectChanges();

    expect(emitted).toEqual([record]);
    expect(el().querySelector('[data-test="aed-list-details"]').getAttribute('aria-expanded')).toBe('true');
  });

  it('shows the empty message', () => {
    fixture.componentRef.setInput('records', []);
    fixture.detectChanges();
    expect(el().querySelector('[data-test="aed-list-empty"]').textContent).toContain('Aed.List.Empty');
  });
});
