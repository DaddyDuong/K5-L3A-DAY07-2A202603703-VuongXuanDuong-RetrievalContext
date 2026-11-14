"""Summarize frozen test traces and explicit source-based review labels."""
import argparse
import json
from pathlib import Path
import statistics

from agent_metrics import aggregate
from benchmark_agent_dev import write_json
from benchmark_agent_test import verify_freeze
from day7_agent import ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path)
    args=parser.parse_args()
    manifest=json.loads((ROOT/'artifacts/test-freeze.json').read_text())
    verify_freeze(ROOT,manifest)
    config=json.loads((args.run/'config.json').read_text())
    cases=json.loads((args.run/'cases.json').read_text())
    output={'split':'test','review_status':'Codex source-based draft; not student confirmed',
            'config_aliases':config['config_aliases'],'metrics':{},'frozen_files_unchanged':True}
    answerable_ids={c['id'] for c in cases if c['answerable']}
    for name in config['unique_configurations']:
        traces=[json.loads((args.run/name/(c['id']+'.json')).read_text()) for c in cases]
        reviews=json.loads((args.run/name/'reviews.json').read_text())
        for trace in traces:
            if trace['status']=='error':continue
            searches=[e for e in trace['events'] if e['event']=='search']
            if not searches or len(searches)>manifest['selected']['max_searches']:
                raise ValueError('Invalid test tool trace')
            if any(len(e['context'])>manifest['selected']['budget_chars'] for e in searches):
                raise ValueError('Context exceeds frozen budget')
            if not set(trace['citations'])<=set(searches[-1]['context_ids']):
                raise ValueError('Citation outside final context')
        report=aggregate(cases,traces,reviews)
        report['retrieval']={'N':len(answerable_ids)}
        for key in ['first_hit1','first_hit3','context_hit']:
            report['retrieval'][key]=sum(t.get('evaluation',{}).get(key,False) for t in traces
                if t['query_id'] in answerable_ids)
        times=[t['elapsed_seconds'] for t in traces]
        report['median_seconds']=statistics.median(times)
        report['total_case_seconds']=sum(times)
        costs=[t['reported_cost_usd'] for t in traces]
        report['reported_cost_usd']=sum(costs) if all(isinstance(c,(int,float)) for c in costs) else None
        report['model_calls']=sum(len(t['model_calls']) for t in traces)
        report['retrieval_calls']=sum(len(t['retrieval_calls']) for t in traces)
        report['search_distribution']={str(n):sum(len(t['retrieval_calls'])==n for t in traces) for n in [1,2,3]}
        report['context_grades']={str(n):sum(r.get('context_grade')==n for r in reviews
            if r['query_id'] in answerable_ids) for n in [0,1,2]}
        report['label_source']='Codex source-based draft'
        report['student_confirmed']=False
        output['metrics'][name]=report
    write_json(args.run/'summary.json',output)
    lines=['# Kết quả test mới sau khi khóa cấu hình','',
           '**Nhãn do Codex đọc đối chiếu nguồn, chưa được học viên xác nhận.**','',
           '| Cấu hình thực thi | Hit@1 | Evidence Hit@3 | Context evidence | Grounded answer | Citation support | Abstention | API USD |',
           '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,s in output['metrics'].items():
        r=s['retrieval'];g=s['grounded_answer'];c=s['citation_validity'];a=s['abstention']
        lines.append(f"| {name} | {r['first_hit1']}/{r['N']} | {r['first_hit3']}/{r['N']} | "
                     f"{r['context_hit']}/{r['N']} | {g['1']+2*g['2']}/{2*g['N']} | "
                     f"{c['n']}/{c['N']} | {a['n']}/{a['N']} | {s['reported_cost_usd']:.8f} |")
    lines+=['','Baseline và selected trỏ cùng trace vì cấu hình chọn trên dev chính là baseline. '
            'Đây là 7 câu và một cấu hình thực thi, không phải hai lần đánh giá độc lập.',
            'Gold/answer labels chỉ dùng sau khi agent kết thúc. Không chỉnh code, prompt hoặc cấu hình theo kết quả test.',
            'Test có câu hỏi mới nhưng dùng chung corpus; không phải holdout tách theo tài liệu.',
            'Chi phí do provider báo, chưa tính phần cứng/điện. Không suy rộng từ 7 câu hoặc coi đây là benchmark nâng cao.',
            'Access for free at openstax.org. Nội dung chunk/evidence theo CC BY-NC-SA 4.0.','']
    (args.run/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    print('\n'.join(lines))


if __name__=='__main__':main()
