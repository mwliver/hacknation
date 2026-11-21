import { createStore } from '@/api/endpoints/create-store';
import type { User } from './auth.types';
import { appStorage } from '@/storage/app-storage';

export const loginStore = createStore<User | null>(null);

if(appStorage.user.hasValue()) loginStore.set(appStorage.user.get()!)

loginStore.register((data) => appStorage.user.set(data))

export function clearSession() {
  loginStore.reset();
}