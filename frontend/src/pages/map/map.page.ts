import { LitElement, css, html, unsafeCSS, type PropertyValues } from 'lit';
import { customElement } from 'lit/decorators.js';
import * as L from 'leaflet';
import leafletStyles from 'leaflet/dist/leaflet.css?inline';

@customElement('map-page')
export class MapPage extends LitElement {
  static styles = css`
    ${unsafeCSS(leafletStyles)}

    :host {
      display: block;
    }

    h1 {
      margin: 0 0 var(--app-space-4);
      font-size: clamp(1.5rem, 6vw, 2rem);
    }

    .map {
      width: 100%;
      height: clamp(24rem, 65vh, 44rem);
      overflow: hidden;
      border: 1px solid var(--app-color-border);
      border-radius: var(--app-radius-md);
      background: var(--app-color-surface);
      isolation: isolate;
    }

    .leaflet-container img.leaflet-tile {
      mix-blend-mode: normal;
      backface-visibility: hidden;
    }

    @media (max-width: 40rem) {
      .map {
        height: 65vh;
      }
    }
  `;

  private map?: L.Map;

  protected firstUpdated(_changedProperties: PropertyValues): void {
    const container = this.renderRoot.querySelector<HTMLDivElement>('.map');
    if (!container) return;

    this.map = L.map(container, {
      zoomAnimation: true,
      fadeAnimation: true,
      markerZoomAnimation: true,
    }).setView([52.2297, 21.0122], 12);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(this.map);

    requestAnimationFrame(() => this.map?.invalidateSize());
  }

  public disconnectedCallback(): void {
    this.map?.remove();
    this.map = undefined;
    super.disconnectedCallback();
  }

  render() {
    return html`
      <h1>Map</h1>
      <div
        class="map"
        role="region"
        aria-label="OpenStreetMap map of Warsaw"
      ></div>
    `;
  }
}
