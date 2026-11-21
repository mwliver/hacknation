/**
 * DataStore
 *
 * A small, shared container for synchronously stored data.
 *
 * Usage:
 *   const usersStore = createStore<User[]>([]);
 *
 *   // In render():
 *   usersStore.observe(this);
 *   const users = usersStore.get();
 *   return html`${users}`;
 *
 * Rules:
 * - get() returns the currently stored data.
 * - set(data) updates the stored data and notifies observers.
 * - observe(target) registers a one-time notification on the next set().
 *   After notification, the observer list is cleared.
 * - Call observe(this) when rendering a component. No manual registration
 *   or cleanup in the LitElement lifecycle is required.
 * - Observers are stored using WeakRef, so the store does not keep components
 *   alive. Dead references and duplicates are removed on the next observe().
 * - Every set() triggers notifications, even when the new value is identical
 *   to the previous value.
 *
 * Requirements: an environment supporting WeakRef (ES2021+).
 */

export type RequestUpdateTarget = {
  requestUpdate: () => void;
};

class DataStore<T> {
  #data: T;

  #observers = new Set<WeakRef<RequestUpdateTarget>>();

  #initialData: T;

  constructor(initialData: T) {
    this.#initialData = initialData;
    this.#data = initialData;
  }

  reset(): void {
    this.set(this.#initialData);
  }

  get(): T {
    return this.#data;
  }

  set(data: T): void {
    this.#data = data;

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
}

export function createStore<T>(initialData: T): DataStore<T> {
  return new DataStore(initialData);
}
