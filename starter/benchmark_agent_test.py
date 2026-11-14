"""Evaluate frozen baseline/selected configurations once on new held-out questions."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from agentic import run_agent
from benchmark_agent_dev import CaseRetriever, write_json
from benchmark_retrieval import evidence_hit
from day7_agent import DEFAULT_DAY6, ROOT, Day6Retriever, ModelController
from retrieval import QuestionContextSelector, RetrievalSuite


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze(root, manifest):
    for name, expected in manifest['files_sha256'].items():
        if sha(root/name) != expected:
            raise ValueError(f'Frozen file changed: {name}; do not tune on test')


def execute(case, name, spec, suite, lock, settings, frozen, output):
    controller=ModelController(settings,max_searches=frozen['max_searches'],query_language=spec['query_language'])
    retriever=CaseRetriever(suite,lock)
    selector=(QuestionContextSelector(suite.dense,case['question'],lock)
              if spec['context_policy']=='relevance' else None)
    trace={'query_id':case['id'],'split':'test','config_name':name,'config':spec,
           'question':case['question'],'filter':case.get('filter',{})}
    start=time.perf_counter()
    try:
        trace.update(run_agent(case['question'],controller,retriever,filters=case.get('filter',{}),
            top_k=frozen['top_k'],max_searches=frozen['max_searches'],budget=frozen['budget_chars'],
            context_selector=selector))
    except Exception as exc:
        trace.update(status='error',error_type=type(exc).__name__)
    trace.update(elapsed_seconds=time.perf_counter()-start,model_calls=controller.calls,
                 retrieval_calls=retriever.calls,context_selections=selector.calls if selector else [])
    usages=[c.get('response',{}).get('usage',{}) for c in controller.calls]
    trace['usage']={k:sum(u.get(k,0) or 0 for u in usages) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    trace['reported_cost_usd']=(sum(u['cost'] for u in usages)
        if usages and all(isinstance(u.get('cost'),(int,float)) for u in usages) else None)
    searches=[e for e in trace.get('events',[]) if e['event']=='search']
    if case['answerable'] and searches:
        trace['evaluation']={
            'first_hit1':bool(searches[0]['results'] and evidence_hit(searches[0]['results'][0],case)),
            'first_hit3':any(evidence_hit(h,case) for h in searches[0]['results']),
            'context_hit':any(evidence_hit(h,case) and h['id'] in searches[-1]['context_ids']
                for e in searches for h in e['results'])}
    write_json(output/name/(case['id']+'.json'),trace)
    return trace


def main():
    from dotenv import dotenv_values
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-env',type=Path,default=ROOT/'.env')
    parser.add_argument('--day6-root',type=Path,default=DEFAULT_DAY6)
    parser.add_argument('--reproduction',action='store_true',help='Rerun published test; not a new holdout')
    args=parser.parse_args()
    freeze_path=ROOT/'artifacts/test-freeze.json'
    manifest=json.loads(freeze_path.read_text())
    verify_freeze(ROOT,manifest)
    frozen=manifest['selected']
    settings={**dotenv_values(args.model_env),**os.environ}
    model=ModelController(settings)
    if model.model!=frozen['model'] or model.provider!=frozen['provider']:
        raise ValueError('Model/provider differs from the frozen dev selection')
    cases=json.loads((ROOT/'data/test_cases.json').read_text())
    if (len(cases)!=7 or len({c['id'] for c in cases})!=7 or any(c['split']!='test' for c in cases)
            or sum(c['answerable'] for c in cases)!=5):
        raise ValueError('Expected five answerable and two unanswerable unique test cases')
    baseline={'query_language':'auto','context_policy':'arrival'}
    specs={'baseline':baseline}
    aliases={'baseline':'baseline','selected':'baseline'}
    if frozen['settings']!=baseline:
        specs['selected']=frozen['settings']
        aliases['selected']='selected'
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output=ROOT/'artifacts/agent-test'/(stamp+('-reproduction' if args.reproduction else ''))
    marker=ROOT/'artifacts/test_started.json'
    if marker.exists() and not args.reproduction:
        raise ValueError('Official test already started; only --reproduction is allowed')
    output.mkdir(parents=True,exist_ok=False)
    for name in specs:
        (output/name).mkdir()
    config={'split':'test','started_at':stamp,'freeze_sha256':sha(freeze_path),
            'reproduction':args.reproduction,'config_aliases':aliases,'unique_configurations':specs,
            'scope':'Baseline equals selected: shared traces, not independent replicated runs'
                if aliases['selected']=='baseline' else 'Two frozen configurations on the same test',
            'workers':3,'cases_sha256':sha(ROOT/'data/test_cases.json')}
    write_json(output/'config.json',config)
    write_json(output/'cases.json',cases)
    dense=None
    try:
        dense=Day6Retriever(args.day6_root.resolve())
        suite=RetrievalSuite(dense,method=frozen['method'])
        if suite.info['chunk_snapshot_sha256']!=manifest['chunk_snapshot_sha256']:
            raise ValueError('Database chunk snapshot differs from dev')
        config['retrieval']=suite.info
        write_json(output/'config.json',config)
        if not args.reproduction:
            with marker.open('x',encoding='utf-8') as f:
                json.dump({'started_at':stamp,'freeze_sha256':sha(freeze_path),
                           'output':str(output.relative_to(ROOT)), 'selection_sha256':manifest['selection_sha256']},f,indent=2)
                f.write('\n')
        print('Output:',output,flush=True)
        lock=threading.RLock()
        traces=[]
        with ThreadPoolExecutor(max_workers=3) as pool:
            jobs=[pool.submit(execute,c,name,spec,suite,lock,settings,frozen,output)
                  for c in cases for name,spec in specs.items()]
            for future in as_completed(jobs):
                t=future.result();traces.append(t)
                print(t['config_name'],t['query_id'],t['status'],len(t['retrieval_calls']),'searches',flush=True)
        write_json(output/'traces.json',sorted(traces,key=lambda t:(t['config_name'],t['query_id'])))
        verify_freeze(ROOT,manifest)
        print('Frozen files unchanged. Review sources before summarizing.',flush=True)
        return int(any(t['status']=='error' for t in traces))
    finally:
        if dense:dense.close()


if __name__=='__main__':
    raise SystemExit(main())
