# Lit Frontend Skeleton

A modular Lit, TypeScript, and Vite application foundation with Web Awesome components, Lit Labs routing, and TanStack Query.

## Requirements

- Node.js 20.19+ or 22.12+
- npm

## Setup

```sh
npm install
cp .env.example .env
npm run dev
```

The prototype login accepts any non-empty email and password. The login query holds the signed-in user in memory; refreshing the page, signing out successfully, or receiving an API `401` clears it.

## Scripts

```sh
npm run dev        # Start the development server
npm run build      # Type-check and create a production build
npm run preview    # Preview the production build
npm run typecheck  # Run strict TypeScript checking
npm run lint       # Run ESLint
npm run format     # Format the project with Prettier
npm test           # Run Vitest and Open WC component tests
```

Set `VITE_API_BASE_URL` to configure the API prefix. Frontend environment variables are public and must not contain secrets.

## Architecture

- `src/app` owns application composition, routing, and the shared QueryClient.
- `src/auth` isolates prototype authentication from future backend integration.
- `src/api` contains the Fetch client, API models, and domain endpoints.
- `src/pages` contains route-level Lit components.
- `src/storage` contains typed, non-sensitive preference persistence.
- `src/styles` centralizes global styles and theme tokens.

`@lit-labs/router` is an experimental Lit Labs package; its version is pinned so router upgrades can be reviewed deliberately. It requires URLPattern, so `urlpattern-polyfill` is loaded before routing. The application shell owns the top-level router and applies navigation guards through route `enter` callbacks.
