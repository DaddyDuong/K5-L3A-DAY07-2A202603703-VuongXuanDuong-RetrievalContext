"""Compare retrievers on original Day 6 dev queries, never held-out test labels."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import statistics
import time

from baseline import pack_context
from day7_agent import Day6Retriever, DEFAULT_DAY6, ROOT
from retrieval import METHODS, RetrievalSuite


def evidence_hit(chunk, question):
    canonical = lambda text: re.sub(r'\s+', ' ', text).strip()
    return any(chunk['source_id'] == gold['gold_source_id']
               and chunk['page'] == gold['gold_page']
               and canonical(gold['evidence_quote']) in canonical(chunk['text'])
               for gold in [question, *question.get('alternative_gold', [])])


def evaluate_case(retriever, case, budget):
    start = time.perf_counter()
    # Only question and the query-supplied metadata filter reach the retriever.
    hits = retriever.search(case['question'], filters=case.get('filter', {}), top_k=3)
    context, ids = pack_context(hits, budget=budget)
    marked = [{**h, 'evidence_hit': evidence_hit(h, case)} for h in hits]
    return {'query_id': case['id'], 'split': 'dev', 'question': case['question'],
            'query': case['question'], 'query_mode': 'original', 'method': retriever.method,
            'filters': case.get('filter', {}), 'results': marked, 'context': context,
            'context_ids': ids, 'context_chars': len(context),
            'hit1': bool(marked and marked[0]['evidence_hit']),
            'hit3': any(h['evidence_hit'] for h in marked),
            'context_hit': any(h['evidence_hit'] and h['id'] in ids for h in marked),
            'elapsed_ms': (time.perf_counter() - start) * 1000, 'status': 'ok'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day6-root', type=Path, default=DEFAULT_DAY6)
    parser.add_argument('--budget', type=int, default=4000)
    parser.add_argument('--candidates', type=int, default=10)
    parser.add_argument('--rrf-constant', type=int, default=60)
    args = parser.parse_args()
    if min(args.budget, args.candidates, args.rrf_constant) < 1:
        parser.error('budget, candidates and RRF constant must be positive')
    output = ROOT / 'artifacts/retrieval' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-dev')
    output.mkdir(parents=True, exist_ok=False)
    write = lambda name, value: (output / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    cases = [q for line in (args.day6_root / 'benchmark/questions.jsonl').read_text().splitlines()
             if (q := json.loads(line))['split'] == 'dev']
    if len(cases) < 15 or len({c['id'] for c in cases}) != len(cases):
        raise ValueError('Expected at least 15 unique dev questions')
    # Declare the selection rule before observing scores. This is retrieval-only,
    # not a final agent selection or an independent Day 7 test evaluation.
    config = {'split': 'dev', 'methods': METHODS, 'queries': 'original Vietnamese, no rewriting',
              'top_k': 3, 'budget_chars': args.budget, 'candidates': args.candidates,
              'rrf_constant': args.rrf_constant, 'query_ids': [c['id'] for c in cases],
              'selection_rule': 'Max Evidence Hit@3, then Hit@1, then Context Evidence Rate, '
                                'then lower median query latency; fixed method order breaks final ties.',
              'matching': 'source/page + full primary OR alternative evidence; whitespace normalized',
              'context': 'single retrieval top-3; deduplicate whole chunks fitting character budget',
              'scope': 'retrieval-only dev benchmark; no model-generated answers',
              'code_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
                  [Path(__file__), ROOT/'starter/retrieval.py', ROOT/'starter/day7_agent.py',
                   ROOT/'starter/baseline.py']}}
    write('config.json', config)
    traces, summaries = [], []
    dense = None
    try:
        start = time.perf_counter()
        dense = Day6Retriever(args.day6_root.resolve())
        suite = RetrievalSuite(dense, candidates=args.candidates, rrf_constant=args.rrf_constant)
        config.update(retrieval=suite.info, shared_setup_seconds=time.perf_counter()-start)
        # Warm query inference separately; no labels/gold are used.
        start = time.perf_counter()
        dense.embedder.embed_query('Python file reading')
        config['warmup_seconds'] = time.perf_counter() - start
        write('config.json', config)
        # Rotate method order per query to reduce systematic warm-cache order effects.
        for index, case in enumerate(cases):
            order = METHODS[index % len(METHODS):] + METHODS[:index % len(METHODS)]
            for method in order:
                suite.method = method
                try:
                    trace = evaluate_case(suite, case, args.budget)
                    trace['retrieval_call'] = suite.calls[-1]
                except Exception as exc:
                    trace = {'query_id': case['id'], 'method': method, 'status': 'error',
                             'error_type': type(exc).__name__, 'hit1': False, 'hit3': False,
                             'context_hit': False}
                traces.append(trace)
                write('traces.json', traces)
        for method in METHODS:
            rows = [t for t in traces if t['method'] == method]
            successful = [t for t in rows if t['status'] == 'ok']
            summary = {'method': method, 'n': len(rows), 'errors': len(rows)-len(successful),
                       'median_ms': statistics.median(t['elapsed_ms'] for t in successful) if successful else None,
                       'service_cost_usd': 0, 'cost_note': 'Local retrieval; hardware/electricity excluded'}
            for metric in ('hit1', 'hit3', 'context_hit'):
                summary[metric + '_n'] = sum(t[metric] for t in rows)
                summary[metric + '_rate'] = summary[metric + '_n'] / len(rows)
            summaries.append(summary)
        selected = (max(summaries, key=lambda s: (s['hit3_n'], s['hit1_n'], s['context_hit_n'],
                    -s['median_ms'], -METHODS.index(s['method'])))['method']
                    if not any(s['errors'] for s in summaries) else None)
        write('summary.json', {'metrics': summaries, 'selected_on_dev': selected,
                               'scope': config['scope']})
        lines = ['# So sánh retrieval trên dev', '',
                 '| Method | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Median ms | Errors |',
                 '|---|---:|---:|---:|---:|---:|']
        for s in summaries:
            cells = [f"{s[m+'_n']}/{s['n']} ({s[m+'_rate']:.1%})" for m in ('hit1','hit3','context_hit')]
            lines.append('| ' + ' | '.join([s['method'], *cells, str(round(s['median_ms'], 2))
                if s['median_ms'] is not None else 'N/A', str(s['errors'])]) + ' |')
        lines += ['', f'Chọn tạm trên dev theo tiêu chí công bố trước: **{selected}**.', '',
                  f"Cùng {suite.info['chunks']} chunk {dense.strategy}, cùng query gốc và filter do câu hỏi cung cấp. "
                  'Không viết lại query, không gọi model trả lời, không đánh giá test. '
                  'Context Evidence Rate ở đây đo context của một lượt top-3, không phải context nhiều lượt của agent.', '',
                  'Chi phí API retrieval = 0 USD (chạy local); chưa tính phần cứng/điện. '
                  'Thời gian setup và warmup ghi riêng trong config.json. Timing là một lần đo, có nhiễu.', '',
                  'Gold dùng chỉ ở bước chấm sau retrieval. Strict metric chưa thay đánh giá nguồn thủ công.', '',
                  'Access for free at openstax.org. Nội dung chunk theo CC BY-NC-SA 4.0; nguồn tại hồ sơ Day 6.', '']
        (output/'summary.md').write_text('\n'.join(lines), encoding='utf-8')
        print('\n'.join(lines))
        print('Results:', output)
        return int(any(s['errors'] for s in summaries))
    finally:
        if dense:
            dense.close()


if __name__ == '__main__':
    raise SystemExit(main())
