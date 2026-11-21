export const delayReject = <T = never>(
  ms: number,
  error: unknown,
): Promise<T> =>
  new Promise((_, reject) => {
    setTimeout(() => reject(error), ms);
  });
