/** Types for the public capability contract (`capabilities.mjs`). */
export type PublicCapability = {
  id: string;
  environment: string;
  route: string;
  traceabilityId: string;
  evidence: readonly string[];
  status: string;
  routeNote?: string;
};

export declare const CAPABILITIES: readonly PublicCapability[];
export declare const PUBLIC_OFFER: {
  plan: string;
  currency: string;
  unitPriceMinor: number;
  priceSource: string;
  checkoutRoute: string;
};
export declare const CONTRACT_VERSION: string;
