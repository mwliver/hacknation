import { queryClient } from '../../app/query-client';
import { httpClient } from '../http';
import type { CreateUserRequest, UserModel } from '../models/user.model';

const usersKey = ['users'] as const;

export function usersQueryOptions() {
  return {
    queryKey: usersKey,
    queryFn: () => httpClient.get<UserModel[]>('users'),
  };
}

export function createUserMutationOptions() {
  return {
    mutationFn: (user: CreateUserRequest) =>
      httpClient.post<UserModel, CreateUserRequest>('users', user),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: usersKey }),
  };
}
