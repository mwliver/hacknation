import { inject } from '@angular/core';
import { CanMatchFn, Router } from '@angular/router';
import { map } from 'rxjs/operators';

import { AedService } from '@app/pages/aed/services/aed.service';

/**
 * AED pages are available only when the backend runs with AED_ENABLED=True
 * (``GET /aed/config`` exists). Otherwise the user lands on the regular 404 page.
 */
export const aedEnabledGuard: CanMatchFn = () => {
  const router = inject(Router);
  return inject(AedService)
    .getConfig()
    .pipe(map((config) => (config?.enabled ? true : router.parseUrl('/404'))));
};
