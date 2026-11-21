import { fixture, html, expect } from '@open-wc/testing';
import { describe, it } from 'vitest';
import './not-found.page';

describe('NotFoundPage', () => {
  it('renders a not-found message and safe navigation', async () => {
    const element = await fixture(html`<not-found-page></not-found-page>`);

    expect(element.shadowRoot?.querySelector('h1')?.textContent).to.equal(
      'Page not found',
    );
    expect(
      element.shadowRoot?.querySelector('a')?.getAttribute('href'),
    ).to.equal('/dashboard');
  });
});
