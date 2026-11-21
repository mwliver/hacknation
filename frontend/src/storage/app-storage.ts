import { createLocalStorage } from '@dmytromykhailiuk/typed-local-storage';

export type ThemePreference = 'light' | 'dark';

export const appStorage = {
  theme: createLocalStorage<ThemePreference>('app:theme', {
    initialValue: 'light',
  }),
  credentials: createLocalStorage<{
    email:string,
    password: string
  }>('credentials'),
};
