# Three.js Demo Page

This document describes the protected Three.js demo page and its navigation entry.

## 1. Page

A new `three-page` Lit component is available at `/three`.

- The route is protected by the existing authentication guard.
- The page displays an animated Three.js torus knot inside a responsive canvas.
- The renderer uses anti-aliasing and is capped at two pixels of device-pixel ratio for performance.
- The scene includes ambient, directional, and point lighting.
- `ResizeObserver` keeps the renderer and perspective camera synchronized with the container.
- Animation and resources are cleaned up when the page is disconnected.

## 2. Navigation

The authenticated drawer includes a **3D Demo** link that:

- Navigates to `/three` through the SPA router.
- Closes the drawer before navigation.

## 3. Dependency

- `three` supplies the 3D scene, geometry, camera, lights, and renderer.
- `@types/three` supplies the TypeScript declarations.
