import { describe, expect, it, vi } from 'vitest';
import { createQuery, queryOptions } from './create-query';

describe('createQuery', () => {
  it('does not cache requests that ignore the cache', async () => {
    const fetchValue = vi.fn(async (value: string) => value);
    const query = createQuery(fetchValue, { ignoreCache: true });

    await query.call('value');
    await query.call('value', queryOptions({ ignoreCache: false }));

    expect(fetchValue).toHaveBeenCalledTimes(2);
  });
});
