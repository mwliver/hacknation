import { Route } from '@angular/router';

import { AedCampaignComponent } from '@app/pages/aed/campaign/aed-campaign.component';
import { AedMapComponent } from '@app/pages/aed/map/aed-map.component';
import { AedShareComponent } from '@app/pages/aed/share/aed-share.component';

export const AED_ROUTES: Route[] = [
  { path: '', component: AedCampaignComponent },
  {
    path: '!aedmap',
    component: AedMapComponent,
    data: { breadcrumbs: { translationKey: 'Aed.Map.Title' } },
  },
  {
    path: '!aedshare',
    component: AedShareComponent,
    data: { breadcrumbs: { translationKey: 'Aed.Share.Title' } },
  },
];
