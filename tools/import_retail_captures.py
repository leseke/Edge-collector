"""Offline CLI for importing previously reviewed retail captures into EDGE."""
import argparse
import json
from intelligence.retail_capture_batch import import_capture_batch
from intelligence.retail_freshness_audit import audit_retail_freshness

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--journal",required=True)
    p.add_argument("--as-of",required=True)
    args=p.parse_args(argv)
    imported=import_capture_batch(manifest_path=args.manifest,journal_path=args.journal,as_of=args.as_of)
    fresh=audit_retail_freshness(args.journal,as_of=args.as_of)
    result={"schema":"edge.retail.offline_cli.v1","import":imported,
            "tracked_offers":fresh["tracked_offers"],"stale_offers":fresh["stale_offers"],
            "network_calls":0,"verified_sales":0,"purchase_authorized":False}
    print(json.dumps(result,sort_keys=True))
    return result

if __name__=="__main__":
    main()
