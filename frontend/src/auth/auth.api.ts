import { createStore } from '@/api/endpoints/create-store';
import type { User } from './auth.types';

export const loginStore = createStore<User | null>(null);

export function clearSession() {
  loginStore.reset();
}