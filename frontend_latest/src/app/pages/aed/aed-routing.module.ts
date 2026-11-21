import { NgModule } from '@angular/core';
import { RouterModule } from '@angular/router';
import { LocalizeRouterModule } from '@gilsdav/ngx-translate-router';

import { AED_ROUTES } from '@app/pages/aed/aed.routes';

/** Lazy AED routes; '!' segments are fixed (not translated) like in the rest of the portal. */
@NgModule({
  imports: [RouterModule.forChild(AED_ROUTES), LocalizeRouterModule.forChild(AED_ROUTES)],
  exports: [RouterModule, LocalizeRouterModule],
})
export class AedRoutingModule {}
