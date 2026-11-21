import { createStore } from '@/api/endpoints/create-store';

export const loginStore = createStore<{
  email: string,
  password: string
} | null>(null);

export function clearSession() {
  loginStore.reset();
}