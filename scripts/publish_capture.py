"""Publish an integrity-checked pointer alongside an immutable market snapshot."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from commercial_history import now

PUBLIC_FILES = ('report.json','retail_source_context.json','mri_cases.json','collection_coverage.json','forecast_evaluations.json')
SCHEMAS = {'report.json':'edge.commercial.snapshot.v1',
    'retail_source_context.json':'edge.mri.retail_source_context.v1',
    'mri_cases.json':'edge.mri.multi_source_cases.v1',
    'collection_coverage.json':'edge.mri.collection_coverage.v1',
    'forecast_evaluations.json':'edge.mri.prospective_followup.v1'}


def build_pointer(out, snapshot_id):
    if not re.fullmatch(r'[0-9]+-[0-9]+', snapshot_id):
        raise ValueError('Invalid immutable snapshot identifier')
    manifest=json.loads((out/'manifest.json').read_text())
    documents={};files={}
    for name in PUBLIC_FILES:
        raw=(out/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if manifest.get(name)!=sha:raise ValueError('Snapshot integrity mismatch: '+name)
        doc=json.loads(raw)
        if doc.get('schema')!=SCHEMAS[name]:raise ValueError('Unexpected public schema: '+name)
        documents[name]=doc
        files[name]={'path':'snapshots/'+snapshot_id+'/'+name,'sha256':sha}
    market=documents['report.json']
    if market['status'] not in ('OK','PARTIAL','FAILED','EMPTY'):raise ValueError('Unexpected collection status')
    return {'schema':'edge.public.live_capture.v1','snapshot_id':snapshot_id,
        'observed_at':market['observed_at'],'published_at':now(),'status':market['status'],'files':files,
        'data_kind':'OBSERVED_MARKET_DATA_WITH_SEPARATE_LABELLED_ESTIMATES',
        'financial_decision':'NOT_ESTABLISHED'}


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--out',required=True);cli.add_argument('--snapshot',required=True);cli.add_argument('--destination',required=True)
    args=cli.parse_args();pointer=build_pointer(Path(args.out),args.snapshot)
    Path(args.destination).write_text(json.dumps(pointer,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'live_snapshot':pointer['snapshot_id'],'status':pointer['status']}))


if __name__=='__main__':main()
