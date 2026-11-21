import { post } from '../http';

type Method = 'POST';

interface Endpoint<TRequest = void, TResponse = void> {
  method: Method;
  request: TRequest;
  response: TResponse;
}

type AnyEndpoint = Endpoint<any, any>;

type Endpoints = Record<string, AnyEndpoint>;

type BuildEndpoint<E extends AnyEndpoint> = (
  request: E['request'],
) => Promise<E['response']>;

type BuildEndpoints<T extends Endpoints> = {
  [K in keyof T]: BuildEndpoint<T[K]>;
};

export function createEndpoint<TRequest = void, TResponse = void>(): Endpoint<
  TRequest,
  TResponse
> {
  return {
    method: 'POST' as Method,
    request: null as TRequest,
    response: null as TResponse,
  };
}

export function createApi<T extends Endpoints>(
  endpoints: T,
): BuildEndpoints<T> {
  return Object.fromEntries(
    Object.entries(endpoints).map(([name]) => [
      name,
      (request: unknown) => post(name, request),
    ]),
  ) as BuildEndpoints<T>;
}
