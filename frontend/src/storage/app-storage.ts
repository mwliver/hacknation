import type { User } from '@/auth/auth.types';
import { createLocalStorage } from '@dmytromykhailiuk/typed-local-storage';

export type ThemePreference = 'light' | 'dark';

export const appStorage = {
  theme: createLocalStorage<ThemePreference>('app:theme', {
    initialValue: 'light',
  }),
  credentials: createLocalStorage<{
    email: string;
    password: string;
  }>('credentials'),
  user: createLocalStorage<User | null>('auth:user'),
};
