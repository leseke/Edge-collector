// Scheduled Outlook collection for one server-pinned, Cloudflare Access
// operator. Uses exactly the same opaque identity key as verified Access JWTs.
// NO cron is created here; this function is inert unless explicitly opted in.
import {deriveCloudflareAccessOwnerKey} from "./leboncoin-access-session.mjs";
import {runOutlookLeboncoinCollection} from "./leboncoin-runner.mjs";

const STATUSES=new Set(["OK","EMPTY","PARTIAL","BUSY","DISABLED"]);
export async function runScheduledOutlookCollection({
  env, scheduledTime, runCollection=runOutlookLeboncoinCollection
}) {
  if(env?.OUTLOOK_SCHEDULE_ENABLED!=="true" ||
     env?.OUTLOOK_INGEST_ENABLED!=="true")return {status:"DISABLED",active:false};
  // Require a single configured, signed-Access-eligible operator. The
  // owner key is derived from trusted deployment configuration; scheduled
  // events have no browser JWT and must never accept an owner from input.
  const subjects=typeof env?.CF_ACCESS_ALLOWED_SUBJECTS==="string"
    ? env.CF_ACCESS_ALLOWED_SUBJECTS.split(",").map(v=>v.trim()).filter(Boolean)
    : [];
  if(subjects.length!==1 || !env?.CF_ACCESS_TEAM_DOMAIN ||
     !env?.CF_ACCESS_APP_AUD ||
     !Number.isSafeInteger(scheduledTime) || scheduledTime<0)
    throw new Error("outlook_schedule_not_configured");
  const ownerKey=await deriveCloudflareAccessOwnerKey({
    teamUrl:env.CF_ACCESS_TEAM_DOMAIN,
    audience:env.CF_ACCESS_APP_AUD,
    subject:subjects[0]
  });
  const result=await runCollection({env,ownerKey,maxPages:3});
  // Never emit credentials, owner keys, mailbox information or listings
  // from a scheduled run; the caller can log only the categorical status.
  if(!STATUSES.has(result?.status))
    throw new Error("outlook_schedule_unexpected_status");
  return {status:result.status,active:result.active===true,
    complete:result.complete===true};
}
