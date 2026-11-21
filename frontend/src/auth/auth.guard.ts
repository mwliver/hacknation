export type Navigate = (url: string) => Promise<void>;

export function getCurrentReturnPath(
  url: URL = new URL(window.location.href),
): string {
  return `${url.pathname}${url.search}${url.hash}`;
}

export function isSafeReturnTo(value: string | null): value is string {
  return value !== null && value.startsWith('/') && !value.startsWith('//');
}

export function loginUrlFor(returnTo: string): string {
  return `/login?returnTo=${encodeURIComponent(returnTo)}`;
}

export async function requireAuthentication(
  isAuthenticated: boolean,
  navigate: Navigate,
  requestedUrl: string,
): Promise<boolean> {
  if (isAuthenticated) return true;
  await navigate(loginUrlFor(requestedUrl));
  return false;
}
