#!/usr/bin/env python3
"""Read-only Cloudflare D1 schema audit for EDGE Outlook, with no secret output.

Only an operator-triggered GitHub workflow invokes this. The API uses POST
for a parameterized, hard-coded SELECT, not for any schema/data mutation.
"""
import json
import os
import sys
import urllib.error
import urllib.request

API="https://api.cloudflare.com/client/v4"
REQUIRED=("lbc_alert_messages","lbc_listing_observations","lbc_graph_delta_cursor",
          "lbc_oauth_pending","lbc_oauth_credentials","lbc_sync_lease")

IMMUTABILITY_TRIGGERS=("lbc_alert_messages_no_update","lbc_alert_messages_no_delete",
    "lbc_listing_observations_no_update","lbc_listing_observations_no_delete")
SCHEMA_QUERY="SELECT type,name FROM sqlite_master WHERE type IN ('table','trigger') AND name LIKE 'lbc_%' ORDER BY type,name"

class AuditError(Exception):
    pass

def request_json(path, token, *, payload=None):
    if not path.startswith("/accounts") or "?" in path and not path.startswith("/accounts?"):
        raise AuditError("invalid_audit_api_path")
    url=API+path
    body=None if payload is None else json.dumps(payload).encode()
    headers={"Authorization":"Bearer "+token,"Accept":"application/json"}
    if body is not None:
        headers["Content-Type"]="application/json"
    req=urllib.request.Request(url,data=body,headers=headers,
                               method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req,timeout=20) as res:
            raw=res.read(2_000_001)
    except (urllib.error.HTTPError, urllib.error.URLError,TimeoutError):
        # Cloudflare errors can include identifiers, token metadata or SQL.
        raise AuditError("cloudflare_audit_request_failed") from None
    if len(raw)>2_000_000:
        raise AuditError("cloudflare_audit_response_too_large")
    try:
        parsed=json.loads(raw)
    except (ValueError,UnicodeError):
        raise AuditError("cloudflare_audit_invalid_response") from None
    if not isinstance(parsed,dict) or parsed.get("success") is not True:
        raise AuditError("cloudflare_audit_request_rejected")
    return parsed

def audit(token, requester=request_json):
    if not isinstance(token,str) or not token:
        return {"status":"NOT_CHECKED","reason":"missing_cloudflare_token",
                "remote_migrations_verified":False}
    # Fail closed if the credential has access to multiple accounts. Never
    # infer an arbitrary account or database from user-controlled input.
    account_result=requester("/accounts?per_page=100",token)
    if (account_result.get("result_info") or {}).get("total_pages",1)!=1:
        raise AuditError("ambiguous_cloudflare_account")
    accounts=account_result.get("result") or []
    if len(accounts)!=1 or not isinstance(accounts[0],dict):
        raise AuditError("ambiguous_cloudflare_account")
    account_id=accounts[0].get("id","")
    if not isinstance(account_id,str) or len(account_id)!=32 or any(
        c not in "0123456789abcdef" for c in account_id.lower()
    ):
        raise AuditError("invalid_cloudflare_account_id")
    listing=requester(f"/accounts/{account_id}/d1/database?per_page=100",token)
    if (listing.get("result_info") or {}).get("total_pages",1)!=1:
        raise AuditError("d1_listing_pagination_unchecked")
    databases=listing.get("result") or []
    if not isinstance(databases,list):
        raise AuditError("invalid_d1_database_list")
    matches=[db for db in databases if isinstance(db,dict) and db.get("name")=="edge-tcg-history"]
    if len(matches)!=1:
        return {"status":"UNAVAILABLE" if not matches else "AMBIGUOUS",
                "database_found":False,"remote_migrations_verified":False,
                "required_table_count":len(REQUIRED),"found_table_count":0}
    database_id=matches[0].get("uuid","")
    import uuid
    try:
        database_id=str(uuid.UUID(database_id))
    except (TypeError,ValueError,AttributeError):
        raise AuditError("invalid_d1_database_identifier") from None
    # Query API uses POST for read-only SQL. Do not interpolate account
    # input in SQL or enumerate private listing/credential table contents.
    result=requester(f"/accounts/{account_id}/d1/database/{database_id}/query",
      token,payload={"sql":SCHEMA_QUERY})
    blocks=result.get("result")
    if not isinstance(blocks,list) or not blocks or not isinstance(blocks[0],dict):
        raise AuditError("unexpected_d1_query_result")
    rows=blocks[0].get("results")
    if not isinstance(rows,list):
        raise AuditError("unexpected_d1_query_rows")
    names={row.get("name") for row in rows if isinstance(row,dict) and row.get("type")=="table" and isinstance(row.get("name"),str)}
    trigger_names={row.get("name") for row in rows if isinstance(row,dict) and row.get("type")=="trigger" and isinstance(row.get("name"),str)}
    missing=sorted(set(REQUIRED)-names)
    missing_triggers=sorted(set(IMMUTABILITY_TRIGGERS)-trigger_names)
    objects_present=not missing and not missing_triggers
    return {"status":"SCHEMA_OBJECTS_PRESENT_UNVERIFIED" if objects_present else "SCHEMA_INCOMPLETE",
            "database_found":True,"required_table_count":len(REQUIRED),
            "found_table_count":len(REQUIRED)-len(missing),
            "missing_tables":missing,"missing_immutability_triggers":missing_triggers,
            "schema_objects_present":objects_present,"remote_migrations_verified":False,
            "real_user_consent_verified":False,"production_collection_active":False}

def main():
    token=os.environ.get("CLOUDFLARE_API_TOKEN","")
    try:
        result=audit(token)
    except AuditError as exc:
        result={"status":"AUDIT_FAILED","reason":str(exc),
                "remote_migrations_verified":False}
    print(json.dumps(result,sort_keys=True))
    summary=os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary,"a",encoding="utf-8") as out:
            out.write("## EDGE Outlook remote D1 — read-only audit\n\n")
            out.write(f"- Status: **{result['status']}**\n")
            out.write(f"- Migrations verified: **{result['remote_migrations_verified']}**\n")
            if "missing_tables" in result:
                out.write("- Missing table names: "+(", ".join(result["missing_tables"]) or "none")+"\n")
            if "missing_immutability_triggers" in result:
                out.write("- Missing immutability triggers: "+(", ".join(result["missing_immutability_triggers"]) or "none")+"\n")
            out.write("- No schema mutations, mailbox reads, tokens or listing content accessed.\n")
    return 1 if result["status"]=="AUDIT_FAILED" else 0

if __name__=="__main__":
    sys.exit(main())
