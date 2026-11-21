import type { CreateUserRequest, UserModel } from '../models/user.model';
import { createApi, createEndpoint } from './create-api';
import { createQuery } from './create-query';

export const UsersApi = createApi({
  getAllUsers: createEndpoint<void, UserModel[]>(),
  createNewuser: createEndpoint<CreateUserRequest, void>(),
  getById: createEndpoint<{ id: string }, UserModel>(),
  getByName: createEndpoint<{ name: string }, CreateUserRequest>(),
});

export const UsersQuery = createQuery(UsersApi.getById);

export const somethingQUery = createQuery(
  (data: { name: string; id: string }) => {
    const { name, id } = data;
    return Promise.all([
      UsersApi.getById({ id }),
      UsersApi.getByName({ name }),
    ])
  },
);

