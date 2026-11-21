import { LitElement, css, html, type PropertyValues } from 'lit';
import { customElement } from 'lit/decorators.js';
import * as THREE from 'three';

@customElement('three-page')
export class ThreePage extends LitElement {
  static styles = css`
    :host {
      display: block;
    }

    h1 {
      margin: 0 0 var(--app-space-4);
      font-size: clamp(1.5rem, 6vw, 2rem);
    }

    p {
      color: var(--app-color-text-muted);
    }

    .canvas {
      width: 100%;
      height: clamp(24rem, 65vh, 44rem);
      overflow: hidden;
      border: 1px solid var(--app-color-border);
      border-radius: var(--app-radius-md);
      background: #111827;
    }

    canvas {
      display: block;
      width: 100%;
      height: 100%;
    }

    @media (max-width: 40rem) {
      .canvas {
        height: 65vh;
      }
    }
  `;

  private renderer?: THREE.WebGLRenderer;
  private scene?: THREE.Scene;
  private camera?: THREE.PerspectiveCamera;
  private knot?: THREE.Mesh;
  private animationFrame?: number;
  private resizeObserver?: ResizeObserver;

  protected firstUpdated(_changedProperties: PropertyValues): void {
    const container = this.renderRoot.querySelector<HTMLDivElement>('.canvas');
    if (!container) return;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#111827');

    this.camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
    this.camera.position.set(0, 0, 5);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.append(this.renderer.domElement);

    const geometry = new THREE.TorusKnotGeometry(1.1, 0.38, 180, 24);
    const material = new THREE.MeshStandardMaterial({
      color: '#8b5cf6',
      metalness: 0.35,
      roughness: 0.22,
    });
    this.knot = new THREE.Mesh(geometry, material);
    this.scene.add(this.knot);

    const ambientLight = new THREE.AmbientLight('#ffffff', 1.2);
    this.scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight('#67e8f9', 4);
    keyLight.position.set(3, 4, 5);
    this.scene.add(keyLight);

    const rimLight = new THREE.PointLight('#f472b6', 30, 20);
    rimLight.position.set(-4, -2, 3);
    this.scene.add(rimLight);

    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(container);
    this.resize();
    this.startAnimation();
  }

  public disconnectedCallback(): void {
    if (this.animationFrame !== undefined) {
      cancelAnimationFrame(this.animationFrame);
    }
    this.resizeObserver?.disconnect();
    this.resizeObserver = undefined;
    this.scene?.traverse((object) => {
      if (object instanceof THREE.Mesh) {
        object.geometry.dispose();
        const materials = Array.isArray(object.material)
          ? object.material
          : [object.material];
        materials.forEach((material) => material.dispose());
      }
    });
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
    this.renderer = undefined;
    this.scene = undefined;
    this.camera = undefined;
    this.knot = undefined;
    super.disconnectedCallback();
  }

  private resize(): void {
    if (!this.renderer || !this.camera) return;
    const container = this.renderRoot.querySelector<HTMLDivElement>('.canvas');
    if (!container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;
    if (width === 0 || height === 0) return;

    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  private startAnimation = (): void => {
    if (!this.renderer || !this.scene || !this.camera) return;

    if (this.knot) {
      this.knot.rotation.x += 0.006;
      this.knot.rotation.y += 0.009;
    }
    this.renderer.render(this.scene, this.camera);
    this.animationFrame = requestAnimationFrame(this.startAnimation);
  };

  render() {
    return html`
      <h1>Three.js Demo</h1>
      <p>An animated 3D torus knot rendered with Three.js.</p>
      <div
        class="canvas"
        role="img"
        aria-label="Animated three-dimensional torus knot"
      ></div>
    `;
  }
}
