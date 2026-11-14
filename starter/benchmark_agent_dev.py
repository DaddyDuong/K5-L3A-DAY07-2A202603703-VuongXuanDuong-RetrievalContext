"""Three controlled agent configurations on 17 dev cases; never runs test."""
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
from benchmark_retrieval import evidence_hit
from day7_agent import DEFAULT_DAY6, ROOT, Day6Retriever, ModelController
from retrieval import QuestionContextSelector, RetrievalSuite

CONFIGS = {
    'baseline': {'query_language': 'auto', 'context_policy': 'arrival'},
    'english': {'query_language': 'english', 'context_policy': 'arrival'},
    'relevance': {'query_language': 'auto', 'context_policy': 'relevance'},
}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


class CaseRetriever:
    def __init__(self, suite, lock):
        self.suite, self.lock, self.calls = suite, lock, []

    def search(self, query, *, filters, top_k):
        with self.lock:
            try:
                return self.suite.search(query, filters=filters, top_k=top_k)
            finally:
                self.calls.append(self.suite.calls[-1])


def execute_case(case, config_name, suite, lock, settings, output):
    spec = CONFIGS[config_name]
    controller = ModelController(settings, max_searches=3, query_language=spec['query_language'])
    retriever = CaseRetriever(suite, lock)
    selector = (QuestionContextSelector(suite.dense, case['question'], lock)
                if spec['context_policy']=='relevance' else None)
    trace = {'query_id': case['id'], 'split': 'dev', 'question': case['question'],
             'config_name': config_name, 'config': {**spec, 'method': 'dense', 'top_k': 3,
                 'max_searches': 3, 'budget_chars': 4000},
             'filter': case.get('filter', {})}
    start = time.perf_counter()
    try:
        trace.update(run_agent(case['question'], controller, retriever,
            filters=case.get('filter', {}), top_k=3, max_searches=3, budget=4000,
            context_selector=selector))
    except Exception as exc:
        trace.update(status='error', error_type=type(exc).__name__)
    trace['elapsed_seconds'] = time.perf_counter()-start
    trace['model_calls'], trace['retrieval_calls'] = controller.calls, retriever.calls
    trace['context_selections'] = selector.calls if selector else []
    usages = [c.get('response', {}).get('usage', {}) for c in controller.calls]
    trace['usage'] = {k: sum(u.get(k,0) or 0 for u in usages)
                      for k in ('prompt_tokens','completion_tokens','total_tokens')}
    trace['reported_cost_usd'] = (sum(u['cost'] for u in usages)
        if usages and all(isinstance(u.get('cost'), (int,float)) for u in usages) else None)
    events = trace.get('events', [])
    searches = [e for e in events if e['event']=='search']
    # Evaluation happens only AFTER the agent finishes. No gold enters its loop.
    if case['answerable'] and searches:
        trace['evaluation'] = {
            'first_hit1': bool(searches[0]['results'] and evidence_hit(searches[0]['results'][0],case)),
            'first_hit3': any(evidence_hit(h,case) for h in searches[0]['results']),
            'context_hit': any(evidence_hit(h,case) and h['id'] in searches[-1]['context_ids']
                               for e in searches for h in e['results']),
        }
    write_json(output/config_name/(case['id']+'.json'),trace)
    return trace


def main():
    from dotenv import dotenv_values
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day6-root', type=Path, default=DEFAULT_DAY6)
    parser.add_argument('--model-env', type=Path, default=ROOT/'.env')
    parser.add_argument('--workers', type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 3:
        parser.error('workers must be 1..3')
    cases_path = ROOT/'data/dev_cases.json'
    cases = json.loads(cases_path.read_text())
    if (len(cases)!=17 or len({c['id'] for c in cases})!=17
            or any(c['split']!='dev' for c in cases)
            or sum(c['answerable'] for c in cases)!=15):
        raise ValueError('Expected 15 answerable + 2 unanswerable unique dev cases')
    settings = {**dotenv_values(args.model_env), **os.environ}
    controller_check = ModelController(settings)
    output = ROOT/'artifacts/agent-dev'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True,exist_ok=False)
    for name in CONFIGS:
        (output/name).mkdir()
    config = {'split':'dev','cases_sha256':hashlib.sha256(cases_path.read_bytes()).hexdigest(),
              'case_ids':[c['id'] for c in cases], 'configs':CONFIGS,
              'model':controller_check.model, 'provider':controller_check.provider,
              'workers':args.workers,'hypotheses':{
                  'english':'Explicit English query instructions may improve bilingual retrieval over automatic query language.',
                  'relevance':'Reranking cumulative chunks by original-question cosine may retain better evidence within the same budget.'},
              'selection_rule':'Require zero provider errors and correct abstention on both unanswerable cases; '
                  'maximize draft grounded-answer total, then supported citation fraction, then context hit count, '
                  'then lower reported API cost, then lower median wall time; baseline wins final tie.',
              'review_status':'Codex draft source-based review required; pending student confirmation',
              'code_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in [Path(__file__),ROOT/'starter/agentic.py',ROOT/'starter/day7_agent.py',ROOT/'starter/retrieval.py']}}
    write_json(output/'config.json',config)
    write_json(output/'cases.json',cases)
    print('Output:',output,flush=True)
    dense = None
    try:
        start = time.perf_counter()
        dense = Day6Retriever(args.day6_root.resolve())
        suite = RetrievalSuite(dense, method='dense')
        config.update(retrieval=suite.info,setup_seconds=time.perf_counter()-start)
        write_json(output/'config.json',config)
        lock = threading.RLock()
        traces = []
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            jobs = []
            names = list(CONFIGS)
            for i,case in enumerate(cases):
                for name in names[i%3:]+names[:i%3]:
                    jobs.append(pool.submit(execute_case,case,name,suite,lock,settings,output))
            for future in as_completed(jobs):
                trace = future.result()
                traces.append(trace)
                print(trace['config_name'],trace['query_id'],trace['status'],
                      len(trace['retrieval_calls']),'searches',round(trace['elapsed_seconds'],2),'s',flush=True)
        write_json(output/'traces.json',sorted(traces,key=lambda t:(t['config_name'],t['query_id'])))
        print('Completed:',len(traces),'runs. Source-based reviews still required.',flush=True)
        return int(any(t['status']=='error' for t in traces))
    finally:
        if dense:
            dense.close()


if __name__=='__main__':
    raise SystemExit(main())
