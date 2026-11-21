/**
 * PromiseQuery
 *
 * A small, shared container for the result of a Promise-returning function.
 *
 * Usage:
 *   const usersQuery = createQuery(fetchUsers);
 *
 *   // In render():
 *   usersQuery.observe(this);
 *   if (usersQuery.isLoading) return html`Loading...`;
 *   if (usersQuery.isError) return html`Error`;
 *   return html`${usersQuery.data}`;
 *
 * Rules:
 * - observe(target) registers a one-time notification on the next status
 *   change. After notification, the observer list is cleared.
 * - Call observe(this) when rendering a component. No manual registration
 *   or cleanup in the LitElement lifecycle is required.
 * - Observers are stored using WeakRef, so the query does not keep components
 *   alive. Dead references and duplicates are removed on the next observe().
 * - Notifications are triggered only when the status changes.
 * - Only the latest call() invocation updates the query's status, data, and
 *   error. Results from older calls may still be stored in the cache, but
 *   they will not overwrite a newer entry for the same key.
 * - The cache is a local in-memory Map belonging to the query instance.
 *   Keys are generated using JSON.stringify(arguments), so arguments should
 *   be serializable.
 * - clearCache() clears the cache. reset() invalidates pending calls and
 *   resets the state, but does not cancel the underlying asynchronous operation.
 *
 * Requirements: an environment supporting WeakRef (ES2021+).
 */

export type PromiseFunction = (...args: any[]) => Promise<any>;

export type PromiseStatus = 'idle' | 'loading' | 'success' | 'error';

export type RequestUpdateTarget = {
  requestUpdate: () => void;
};

export type PromiseQueryOptions = {
  keepPreviousData?: boolean;
  ignoreCache?: boolean;
};

export type PromiseCallOptions = PromiseQueryOptions;

const QUERY_OPTIONS = Symbol('query-options');

type MarkedQueryOptions = PromiseCallOptions & {
  [QUERY_OPTIONS]: true;
};

type CacheEntry<T> = {
  requestId: number;
  data: T;
};

export function queryOptions(options: PromiseCallOptions): MarkedQueryOptions {
  return {
    ...options,
    [QUERY_OPTIONS]: true,
  };
}

function isQueryOptions(value: unknown): value is MarkedQueryOptions {
  return (
    typeof value === 'object' &&
    value !== null &&
    QUERY_OPTIONS in value &&
    (value as MarkedQueryOptions)[QUERY_OPTIONS] === true
  );
}

class PromiseWrapper<F extends PromiseFunction> {
  #status: PromiseStatus = 'idle';
  #data: Awaited<ReturnType<F>> | undefined;
  #error: unknown;

  #observers = new Set<WeakRef<RequestUpdateTarget>>();
  #requestId = 0;

  #cache = new Map<string, CacheEntry<Awaited<ReturnType<F>>>>();

  constructor(
    private readonly fn: F,
    private readonly options: PromiseQueryOptions = {},
  ) {}

  get status(): PromiseStatus {
    return this.#status;
  }

  get data(): Awaited<ReturnType<F>> | undefined {
    return this.#data;
  }

  get error(): any {
    return this.#error;
  }

  get isIdle(): boolean {
    return this.#status === 'idle';
  }

  get isLoading(): boolean {
    return this.#status === 'loading';
  }

  get isSuccess(): boolean {
    return this.#status === 'success';
  }

  get isError(): boolean {
    return this.#status === 'error';
  }

  #setStatus(status: PromiseStatus): void {
    if (this.#status === status) return;

    this.#status = status;

    const observers = [...this.#observers];
    this.#observers.clear();

    for (const observer of observers) {
      observer.deref()?.requestUpdate();
    }
  }

  observe(target: RequestUpdateTarget): void {
    for (const observer of this.#observers) {
      const observedTarget = observer.deref();

      if (!observedTarget || observedTarget === target) {
        this.#observers.delete(observer);
      }
    }

    this.#observers.add(new WeakRef(target));
  }

  #getCacheKey(args: Parameters<F>): string | undefined {
    try {
      return JSON.stringify(args);
    } catch {
      return undefined;
    }
  }

  async call(
    ...args: [...Parameters<F>, MarkedQueryOptions?]
  ): Promise<Awaited<ReturnType<F>>> {
    const lastArg = args.at(-1);
    const callOptions = isQueryOptions(lastArg) ? lastArg : undefined;

    const requestArgs = (
      callOptions ? args.slice(0, -1) : args
    ) as Parameters<F>;

    const keepPreviousData =
      callOptions?.keepPreviousData ?? this.options.keepPreviousData ?? false;

    const ignoreCache =
      callOptions?.ignoreCache ?? this.options.ignoreCache ?? false;

    const requestId = ++this.#requestId;

    if (!keepPreviousData) {
      this.#data = undefined;
    }

    this.#error = undefined;
    this.#setStatus('loading');

    const cacheKey = this.#getCacheKey(requestArgs);

    if (!ignoreCache && cacheKey !== undefined) {
      const cachedEntry = this.#cache.get(cacheKey);

      if (cachedEntry) {
        if (requestId === this.#requestId) {
          this.#data = cachedEntry.data;
          this.#setStatus('success');
        }

        return cachedEntry.data;
      }
    }

    try {
      const response = await this.fn(...requestArgs);

      if (!ignoreCache && cacheKey !== undefined) {
        const cachedEntry = this.#cache.get(cacheKey);

        if (!cachedEntry || requestId > cachedEntry.requestId) {
          this.#cache.set(cacheKey, {
            requestId,
            data: response,
          });
        }
      }

      if (requestId === this.#requestId) {
        this.#data = response;
        this.#setStatus('success');
      }

      return response;
    } catch (error) {
      if (requestId === this.#requestId) {
        this.#error = error;
        this.#setStatus('error');
      }

      throw error;
    }
  }

  reset(): void {
    this.#requestId++;

    this.#data = undefined;
    this.#error = undefined;

    this.#setStatus('idle');
  }

  clearCache(): void {
    this.#cache.clear();
  }
}

export function createQuery<F extends PromiseFunction>(
  fn: F,
  options: PromiseQueryOptions = {},
): PromiseWrapper<F> {
  return new PromiseWrapper(fn, options);
}
