"""Summarize source-reviewed dev runs; draft labels never imply student approval."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

from agent_metrics import aggregate
from benchmark_agent_dev import CONFIGS, write_json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    config=json.loads((args.run/'config.json').read_text())
    cases=json.loads((args.run/'cases.json').read_text())
    summaries=[]
    for name in CONFIGS:
        traces=[json.loads((args.run/name/(c['id']+'.json')).read_text()) for c in cases]
        reviews=json.loads((args.run/name/'reviews.json').read_text())
        for t in traces:
            if t['status']=='error':
                continue
            searches=[e for e in t['events'] if e['event']=='search']
            assert searches and len(searches)<=3
            assert all(len(e['context'])<=4000 for e in searches)
            assert set(t['citations'])<=set(searches[-1]['context_ids'])
        report=aggregate(cases,traces,reviews)
        report.update(config_name=name, label_source='Codex source-based draft',student_confirmed=False)
        valid=[t for t in traces if t['status']!='error']
        answerable_ids={c['id'] for c in cases if c['answerable']}
        report['retrieval']={'N':len(answerable_ids)}
        for metric in ['first_hit1','first_hit3','context_hit']:
            report['retrieval'][metric]=sum(t.get('evaluation',{}).get(metric,False)
                for t in traces if t['query_id'] in answerable_ids)
        report['median_seconds']=statistics.median(t['elapsed_seconds'] for t in valid) if valid else None
        costs=[t['reported_cost_usd'] for t in traces]
        report['reported_cost_usd']=sum(costs) if all(isinstance(c,(int,float)) for c in costs) else None
        report['model_calls']=sum(len(t['model_calls']) for t in traces)
        report['retrieval_calls']=sum(len(t['retrieval_calls']) for t in traces)
        report['search_distribution']={str(n):sum(len(t['retrieval_calls'])==n for t in valid) for n in [1,2,3]}
        summaries.append(report)
    eligible=[s for s in summaries if not s['provider_errors'] and s['abstention']=={'n':2,'N':2}]
    def key(s):
        g=s['grounded_answer']
        cite=s['citation_validity']
        return (g['1']+2*g['2'],cite['n']/cite['N'] if cite['N'] else 0,
                s['retrieval']['context_hit'], -s['reported_cost_usd'] if s['reported_cost_usd'] is not None else float('-inf'),
                -s['median_seconds'], -list(CONFIGS).index(s['config_name']))
    selected=max(eligible,key=key)['config_name'] if eligible else None
    output={'split':'dev','reviews':'Codex source-based draft; pending student review',
            'metrics':summaries,'selected_config':selected,'selection_rule':config['selection_rule']}
    write_json(args.run/'summary.json',output)
    frozen={'selected_config':selected,'split':'dev','student_confirmed':False,
            'status':'frozen_on_dev_using_draft_source_reviews' if selected else 'no_eligible_configuration',
            'settings':CONFIGS[selected] if selected else None,'method':'dense','top_k':3,
            'max_searches':3,'budget_chars':4000,'model':config['model'],'provider':config['provider'],
            'selection_rule':config['selection_rule'],'benchmark_sha256':config['cases_sha256'],
            'run_config_sha256':hashlib.sha256((args.run/'config.json').read_bytes()).hexdigest(),
            'review_sha256':{name:hashlib.sha256((args.run/name/'reviews.json').read_bytes()).hexdigest() for name in CONFIGS},
            'test_started':False}
    write_json(args.run/'selection.json',frozen)
    lines=['# Agent dev — so sánh ba cấu hình','',
        '**Nhãn do Codex đối chiếu nguồn, đang ở dạng sơ bộ; chưa được học viên xác nhận.**','',
        '| Config | Grounded answer tổng /30 | Citation support | Context evidence | Abstention | Median s | API USD | Errors |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for s in summaries:
        g=s['grounded_answer']; c=s['citation_validity']; a=s['abstention']
        lines.append(f"| {s['config_name']} | {g['1']+2*g['2']}/30 | {c['n']}/{c['N']} | "
            f"{s['retrieval']['context_hit']}/15 | {a['n']}/{a['N']} | {s['median_seconds']:.2f} | "
            f"{s['reported_cost_usd']:.8f} | {s['provider_errors']} |")
    lines+=['',f'Chọn trên dev theo nhãn sơ bộ và tiêu chí công bố trước: **{selected}**.',
            'Không chạy test. Grounded answer và citation support cần học viên đọc lại; không phải nhãn do người học đã xác nhận.',
            'Latency là wall time của từng case với 3 worker, gồm chờ khóa retrieval; không dùng để suy rộng benchmark phần cứng.',
            'Context Evidence Rate dùng đầy đủ primary hoặc alternative evidence sau chuẩn hóa whitespace, không suy từ câu trả lời.',
            'Access for free at openstax.org. Đoạn sách trong trace theo CC BY-NC-SA 4.0.','']
    (args.run/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines))


if __name__=='__main__':
    main()
