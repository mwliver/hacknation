import { createApi, createEndpoint } from '@/api/endpoints/create-api';
import type { Credentials, User } from './auth.types';
import { createQuery } from '@/api/endpoints/create-query';
import { delayResolve } from '@/utils/delay-resolve';

// export const AuthApi = {
//   async login(credentials: Credentials): Promise<User> {
//     const email = credentials.email.trim();
//     if (!email || !credentials.password) {
//       throw new Error('Email and password are required.');
//     }

//     return {
//       id: email.toLowerCase(),
//       name: email.split('@')[0] || 'User',
//       email,
//     };
//   },

//   async logout(): Promise<void> {
//     return Promise.resolve();
//   },
// };

const AuthApi = createApi({
  login: createEndpoint<Credentials, User>(),
  logout: createEndpoint<void, void>(),
});

export const loginQuery = createQuery(
  (credentials: Credentials) =>
    delayResolve(2000, {
      id: credentials.email.toLowerCase(),
      name: credentials.email.split('@')[0] || 'User',
      email: credentials.email,
    }),
  // AuthApi.login(credentials).catch(() => {

  //   delayResolve(2000,)
  //   const email = credentials.email.trim();
  //   if (!email || !credentials.password) {
  //     throw new Error('Email and password are required.');
  //   }

  //   return {
  //     id: email.toLowerCase(),
  //     name: email.split('@')[0] || 'User',
  //     email,
  //   };
  // }),
  {
    ignoreCache: true,
    keepPreviousData: false,
  },
);

export function clearSession() {
  loginQuery.reset();

}

export function signOut() {
  loginQuery.reset();
  AuthApi.logout();
}
