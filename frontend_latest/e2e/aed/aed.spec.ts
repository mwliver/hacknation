import { expect, Page, test } from '@playwright/test';
import * as path from 'path';

import { mockApi, OTWOCK_STATION } from './api-mocks';

/**
 * AED prototype – responsive, keyboard and flow checks + screenshots for the contest presentation
 * (saved in docs/aed/screenshots, see docs/aed/ZRZUTY_EKRANU.md).
 */
const SHOTS = path.join(__dirname, '../../../docs/aed/screenshots');
const DESKTOP = { width: 1440, height: 900 };
const MOBILE = { width: 360, height: 780 };

async function shot(page: Page, name: string, fullPage = true) {
  await page.mouse.move(0, 0); // no hover effects on screenshots
  await page.screenshot({ path: path.join(SHOTS, name), fullPage });
}

async function noHorizontalScroll(page: Page) {
  const { scroll, width } = await page.evaluate(() => ({
    scroll: document.documentElement.scrollWidth,
    width: window.innerWidth,
  }));
  expect(scroll).toBeLessThanOrEqual(width);
}

test.describe('AED – strona akcji', () => {
  test('desktop 1440 px: nazwa, hasło, liczniki i dwa przyciski', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await mockApi(page);
    await page.goto('/pl/aed');
    await expect(page.getByRole('heading', { level: 1, name: 'Misja AED' })).toBeVisible();
    await expect(page.getByText('Dane na ratunek')).toBeVisible();
    await expect(page.locator('[data-test="aed-stat-count"]')).toHaveText('9');
    await expect(page.locator('[data-test="aed-cta-find"]')).toBeVisible();
    await expect(page.locator('[data-test="aed-cta-share"]')).toBeVisible();
    await expect(page.getByRole('note')).toContainText('najpierw dzwoń 112');
    await noHorizontalScroll(page);
    await shot(page, '01_strona_akcji_1440.png');
  });

  test('przy AED_ENABLED=False strony AED są niedostępne (404)', async ({ page }) => {
    await mockApi(page, { aedEnabled: false });
    await page.goto('/pl/aed');
    await expect(page).toHaveURL(/404/);
  });
});

test.describe('AED – mapa i najbliższe AED', () => {
  test('desktop 1440 px: moja lokalizacja → 5 najbliższych z odległością, godzinami i gotowością', async ({
    page,
    context,
  }) => {
    await page.setViewportSize(DESKTOP);
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation(OTWOCK_STATION);
    await mockApi(page);
    await page.goto('/pl/aed/mapa');
    await expect(page.locator('[data-test="aed-map"].leaflet-container')).toBeVisible();

    await page.locator('[data-test="aed-locate"]').click();
    const nearest = page.getByRole('list', { name: 'Najbliższe AED' }).getByRole('listitem');
    await expect(nearest).toHaveCount(3);
    await expect(nearest.first()).toContainText('Dworzec Testowy Otwock');
    await expect(nearest.first().locator('[data-test="aed-distance"]')).toHaveText(/4 m/);
    await expect(nearest.first()).toContainText('24/7');
    await expect(nearest.first()).toContainText('Otwarte teraz');
    await expect(nearest.first()).toContainText('Gotowy');
    await expect(nearest.nth(2)).toContainText('Wymaga uwagi');
    await expect(page.locator('[data-test="aed-status"]')).toContainText('Znaleziono');

    // list next to the map on desktop
    const map = await page.locator('[data-test="aed-map"]').boundingBox();
    const list = await nearest.first().boundingBox();
    expect(list.x).toBeGreaterThan(map.x + map.width - 1);
    await noHorizontalScroll(page);
    await shot(page, '02_mapa_desktop_1440.png');

    await nearest.first().locator('[data-test="aed-list-details"]').click();
    const details = page.locator('[data-test="aed-details"]');
    await expect(details).toContainText('ul. Kolejowa Testowa 1, 05-400 Otwock');
    await expect(details).toContainText('Źródła danych (2)');
    await expect(details.locator('[data-test="aed-navigate"]')).toHaveAttribute(
      'href',
      /openstreetmap\.org\/directions/,
    );
    await expect(details.locator('[data-test="aed-report-problem"]')).toHaveAttribute('href', /dataset\/feedback/);
    await shot(page, '03_mapa_szczegoly_aed_1440.png');
  });

  test('telefon 360 px: lista pod mapą, bez poziomego przewijania, cele dotykowe ≥ 44 px', async ({
    page,
    context,
  }) => {
    await page.setViewportSize(MOBILE);
    await context.grantPermissions(['geolocation']);
    await context.setGeolocation(OTWOCK_STATION);
    await mockApi(page);
    await page.goto('/pl/aed/mapa');
    await page.locator('[data-test="aed-locate"]').click();
    const firstItem = page.getByRole('list', { name: 'Najbliższe AED' }).getByRole('listitem').first();
    await expect(firstItem).toContainText('Dworzec Testowy Otwock');

    const map = await page.locator('[data-test="aed-map"]').boundingBox();
    const list = await firstItem.boundingBox();
    expect(list.y).toBeGreaterThan(map.y + map.height - 1);
    await noHorizontalScroll(page);
    for (const selector of [
      '[data-test="aed-locate"]',
      '[data-test="aed-address-submit"]',
      '[data-test="aed-list-details"]',
    ]) {
      const box = await page.locator(selector).first().boundingBox();
      expect(box.height).toBeGreaterThanOrEqual(44);
      expect(box.width).toBeGreaterThanOrEqual(44);
    }
    await page.locator('[data-test="aed-map"]').scrollIntoViewIfNeeded();
    await shot(page, '04_mapa_telefon_360.png');
  });

  test('odmowa zgody na lokalizację → komunikat i wyszukiwanie adresu', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await mockApi(page);
    await page.goto('/pl/aed/mapa');
    await page.locator('[data-test="aed-locate"]').click();
    await expect(page.locator('[data-test="aed-address-error"]')).toContainText('Nie udostępniono lokalizacji');
    await expect(page.locator('[data-test="aed-address"]')).toBeFocused();

    await page.locator('[data-test="aed-address"]').fill('Otwock, Kolejowa');
    await page.keyboard.press('Enter');
    await expect(page.getByRole('list', { name: 'Najbliższe AED' }).getByRole('listitem')).toHaveCount(3);
  });

  test('obsługa klawiaturą: wyszukanie adresu, filtr i szczegóły bez myszy', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await mockApi(page);
    await page.goto('/pl/aed/mapa');
    await page.locator('[data-test="aed-locate"]').focus();

    await page.keyboard.press('Tab');
    await expect(page.locator('[data-test="aed-address"]')).toBeFocused();
    await page.keyboard.type('Otwock');
    await page.keyboard.press('Tab');
    await expect(page.locator('[data-test="aed-address-submit"]')).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('list', { name: 'Najbliższe AED' }).getByRole('listitem')).toHaveCount(3);

    await page.keyboard.press('Tab');
    await expect(page.locator('#aed-filter-open')).toBeFocused();
    await page.keyboard.press('Space');
    await expect(page.locator('#aed-filter-open')).toBeChecked();

    // continue with Tab until the first "Szczegóły" button – the map itself is a single focusable region
    const details = page.locator('[data-test="aed-list-details"]').first();
    for (let i = 0; i < 15 && !(await details.evaluate((el) => el === document.activeElement)); i++) {
      await page.keyboard.press('Tab');
    }
    await expect(details).toBeFocused();
    const outline = await details.evaluate((el) => getComputedStyle(el).outlineStyle + getComputedStyle(el).boxShadow);
    expect(outline).not.toBe('nonenone');
    await page.keyboard.press('Enter');
    await expect(page.locator('#aed-details-heading')).toBeFocused();
    await expect(page.locator('[data-test="aed-details"]')).toContainText('Dworzec Testowy Otwock');
  });
});

test.describe('AED – kreator dysponenta', () => {
  test('panel administratora w środowisku lokalnym', async ({ page }) => {
    await mockApi(page);
    await page.goto('/pl/aed/udostepnij');
    await page.locator('[data-test="aed-step-4"]').click();
    await expect(page.getByRole('link', { name: /Przejdź do panelu dostawcy/ })).toHaveAttribute(
      'href',
      'https://admin.mcod.local',
    );
  });

  test('plik z błędami → raport, poprawiony plik → zgodny ze standardem → instrukcja publikacji', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await mockApi(page);
    await page.goto('/pl/aed/udostepnij');
    await expect(page.locator('[data-test="aed-fields-table"] tbody tr')).toHaveCount(29);
    await expect(page.locator('[data-test="aed-template-xlsx"]')).toHaveAttribute('href', /\/aed\/template\.xlsx$/);
    await shot(page, '05_kreator_krok1_szablon_1440.png', false);

    await page.locator('[data-test="aed-step-2"]').click();
    await page.locator('[data-test="aed-file"]').setInputFiles({
      name: 'aed_bledy.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id_aed,kod_szafki\nOTW-0001,1234\n'),
    });
    await page.locator('[data-test="aed-validate"]').click();

    const summary = page.locator('[data-test="aed-report-summary"]');
    await expect(summary).toContainText('nie jest zgodny');
    await expect(page.locator('[data-test="aed-issue-FORBIDDEN_COLUMN"]')).toContainText('kod_szafki');
    await expect(page.locator('[data-test="aed-issue-DUPLICATE_ID"]')).toContainText('3');
    await expect(page.locator('#aed-step3-heading')).toBeFocused();
    await expect(page.locator('[data-test="aed-to-publish"]')).toBeDisabled();
    await shot(page, '06_kreator_raport_bledow_1440.png');

    await page.locator('[data-test="aed-report-filter-WARNING"]').click();
    await expect(page.locator('[data-test="aed-issue-DUPLICATE_ID"]')).toHaveCount(0);
    await expect(page.locator('[data-test="aed-issue-OPENING_HOURS_UNSUPPORTED"]')).toHaveCount(1);

    // fixed file
    await page.locator('[data-test="aed-step-2"]').click();
    await page.locator('[data-test="aed-file"]').setInputFiles({
      name: 'aed_poprawiony.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from('id_aed\nOTW-0001\n'),
    });
    await page.locator('[data-test="aed-validate"]').click();
    await expect(summary).toContainText('jest zgodny ze standardem AED v1');
    await shot(page, '07_kreator_zgodny_1440.png', false);
    await page.locator('[data-test="aed-to-publish"]').click();
    await expect(page.getByRole('heading', { name: 'Opublikuj' })).toBeFocused();
  });

  test('nieobsługiwany typ pliku jest odrzucany przed wysłaniem (aria-invalid + komunikat)', async ({ page }) => {
    await mockApi(page);
    await page.goto('/pl/aed/udostepnij');
    await page.locator('[data-test="aed-step-2"]').click();
    await page
      .locator('[data-test="aed-file"]')
      .setInputFiles({ name: 'aed.pdf', mimeType: 'application/pdf', buffer: Buffer.from('%PDF') });
    await expect(page.locator('[data-test="aed-file-error"]')).toContainText('CSV lub XLSX');
    await expect(page.locator('[data-test="aed-file"]')).toHaveAttribute('aria-invalid', 'true');
    await expect(page.locator('[data-test="aed-file"]')).toHaveAttribute('aria-describedby', /aed-file-error/);
  });

  test('telefon 360 px: kreator bez poziomego przewijania', async ({ page }) => {
    await page.setViewportSize(MOBILE);
    await mockApi(page);
    await page.goto('/pl/aed/udostepnij');
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    await noHorizontalScroll(page);
  });

  test('wersja angielska', async ({ page }) => {
    await mockApi(page);
    await page.goto('/en/aed/mapa');
    await expect(page.getByRole('heading', { level: 1, name: 'Find the nearest AED' })).toBeVisible();
    await expect(page.getByRole('note')).toContainText('call 112 first');
  });
});
