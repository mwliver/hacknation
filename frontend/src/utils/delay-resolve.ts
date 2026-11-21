export const delayResolve = <T>(ms: number, value: T): Promise<T> =>
  new Promise((resolve) => {
    setTimeout(() => resolve(value), ms);
  });
