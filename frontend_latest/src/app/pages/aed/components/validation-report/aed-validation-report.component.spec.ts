import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateModule } from '@ngx-translate/core';

import { AedValidationReportComponent } from '@app/pages/aed/components/validation-report/aed-validation-report.component';
import { AedValidationReport } from '@app/pages/aed/services/aed.models';

const REPORT: AedValidationReport = {
  standard: 'AED_V1',
  zgodny: false,
  liczba_wierszy: 3,
  liczba_bledow: 1,
  liczba_ostrzezen: 1,
  data_walidacji: null,
  zasob_id: null,
  problemy: [
    {
      wiersz: 3,
      kolumna: 'id_aed',
      kod: 'DUPLICATE_ID',
      poziom: 'ERROR',
      komunikat_pl: 'Powtórzony identyfikator',
      komunikat_en: 'Duplicate id',
    },
    {
      wiersz: 2,
      kolumna: 'data_aktualizacji',
      kod: 'STALE_UPDATE',
      poziom: 'WARNING',
      komunikat_pl: 'Stare dane',
      komunikat_en: 'Old data',
    },
  ],
};

describe('AedValidationReportComponent', () => {
  let fixture: ComponentFixture<AedValidationReportComponent>;
  const el = () => fixture.nativeElement as HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AedValidationReportComponent, TranslateModule.forRoot()],
    }).compileComponents();
    fixture = TestBed.createComponent(AedValidationReportComponent);
    fixture.componentRef.setInput('report', REPORT);
    fixture.detectChanges();
  });

  it('shows the summary in a live region', () => {
    const summary = el().querySelector('[data-test="aed-report-summary"]');
    expect(summary.getAttribute('role')).toBe('status');
    expect(summary.getAttribute('aria-live')).toBe('polite');
    expect(summary.textContent).toContain('3');
    expect(summary.classList).toContain('aed-report__summary--error');
  });

  it('lists every problem with row, column and message', () => {
    const rows = el().querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('id_aed');
    expect(rows[0].textContent).toContain('Powtórzony identyfikator');
    expect(rows[0].textContent).toContain('3');
  });

  it('filters errors and warnings', () => {
    (el().querySelector('[data-test="aed-report-filter-ERROR"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el().querySelectorAll('[data-test="aed-issue-DUPLICATE_ID"]').length).toBe(1);
    expect(el().querySelectorAll('[data-test="aed-issue-STALE_UPDATE"]').length).toBe(0);
    expect(el().querySelector('[data-test="aed-report-filter-ERROR"]').getAttribute('aria-pressed')).toBe('true');

    (el().querySelector('[data-test="aed-report-filter-WARNING"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el().querySelectorAll('[data-test="aed-issue-STALE_UPDATE"]').length).toBe(1);
  });

  it('exports the filtered report to CSV', () => {
    const createObjectURL = jest.fn(() => 'blob:aed');
    const revokeObjectURL = jest.fn();
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    const click = jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined);

    (el().querySelector('[data-test="aed-report-export"]') as HTMLButtonElement).click();

    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:aed');
    click.mockRestore();
  });

  it('shows a compliant report without the table', () => {
    fixture.componentRef.setInput('report', {
      ...REPORT,
      zgodny: true,
      liczba_bledow: 0,
      liczba_ostrzezen: 0,
      problemy: [],
    });
    fixture.detectChanges();
    expect(el().querySelector('table')).toBeNull();
    expect(el().querySelector('[data-test="aed-report-summary"]').classList).toContain('aed-report__summary--ok');
  });
});
