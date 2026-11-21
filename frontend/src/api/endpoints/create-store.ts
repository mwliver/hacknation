
export type RequestUpdateTarget = {
  requestUpdate: () => void;
};

export type StoreListener<T> = (data: T) => void;

class DataStore<T> {
  #data: T;
  #initialData: T;

  #observers = new Set<WeakRef<RequestUpdateTarget>>();
  #listeners = new Set<StoreListener<T>>();

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

    for (const listener of this.#listeners) {
      listener(this.#data);
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

  register(listener: StoreListener<T>): void {
    this.#listeners.add(listener);
  }

  unregister(listener: StoreListener<T>): void {
    this.#listeners.delete(listener);
  }
}

export function createStore<T>(initialData: T): DataStore<T> {
  return new DataStore(initialData);
}
