// Dedicated Outlook entrypoint. Never reuse the TCG worker entrypoint:
// it exposes a separate collection trigger and scheduled TCG jobs.
// This worker has no scheduled handler and no public collector endpoint.
import {handleOutlookWorkerRoute} from "./leboncoin-worker-http.mjs";

type OutlookEnv = {
  DB?: D1Database;
  OUTLOOK_ROUTES_ENABLED?: string;
  OUTLOOK_CONSENT_ENABLED?: string;
  OUTLOOK_DIAGNOSTICS_ENABLED?: string;
  OUTLOOK_OFFERS_ENABLED?: string;
  OUTLOOK_INGEST_ENABLED?: string;
  OUTLOOK_MANUAL_SYNC_ENABLED?: string;
  OUTLOOK_SCHEDULE_ENABLED?: string;
  OUTLOOK_CLIENT_ID?: string;
  OUTLOOK_CLIENT_SECRET?: string;
  OUTLOOK_REDIRECT_URI?: string;
  OUTLOOK_TENANT?: string;
  OUTLOOK_ENCRYPTION_KEY?: string;
  OUTLOOK_DELTA_ENCRYPTION_KEY?: string;
  OUTLOOK_ALLOWED_SENDER_DOMAINS?: string;
  CF_ACCESS_TEAM_DOMAIN?: string;
  CF_ACCESS_APP_AUD?: string;
  CF_ACCESS_ALLOWED_SUBJECTS?: string;
};

const HIDDEN_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  "Cache-Control": "no-store, private",
  "Referrer-Policy": "no-referrer",
  "X-Content-Type-Options": "nosniff"
};

export default {
  async fetch(request: Request, env: OutlookEnv): Promise<Response> {
    // With default-off flags this never requests Microsoft Graph, queries D1,
    // or exposes OAuth/identity configuration to unauthenticated visitors.
    const response = await handleOutlookWorkerRoute({request,env});
    return response ?? new Response(JSON.stringify({error:"not_found"}),{
      status:404,headers:HIDDEN_HEADERS
    });
  }
};
