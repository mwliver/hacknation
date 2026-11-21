
import { clearSession } from '../auth/auth.api';
import { navigateTo } from '../app/router';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

const API_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function post<T>(
  path: string,
  body?: unknown,
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError('Unable to reach the API.', 0);
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      clearSession();
      await navigateTo('/login');
    }

    if (response.status === 403) {
      await navigateTo('/forbidden');
    }

    throw new ApiError(
      data?.message ?? `Request failed: ${response.status}`,
      response.status,
    );
  }

  return data as T;
}
