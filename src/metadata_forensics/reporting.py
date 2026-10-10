import json
import re
import os
from pathlib import Path
from urllib.request import Request, urlopen
from datetime import datetime, timezone

SYSTEM_PROMPT = """你是一名临床数据治理与实体对齐的取证报告撰写助手。
你只能使用用户提供的 JSON 作为事实来源。不得臆造患者属性、临床诊断、实验室事件、日期、外部来源或已确认的错误。
候选排名是上游 B02/B04 的结果；不要重新排序或改写上游 decision。
时间一致性只表示支持关联的线索，不证明身份相同；时间矛盾也不证明数据被污染。
重要：一个 sample ID 只能来自输入；不要把相同日期的多个样本视为独立的身份确认。
用简体中文写清晰、克制、可供人工审计的报告。
只输出一个合法 JSON 对象，不要 Markdown 代码围栏，不要额外文字。
JSON 必须包含字段：clinical_id (string), decision (string), summary (string),
candidate_assessments (array of objects with lab_id, supporting_sample_ids, contradicting_sample_ids, interpretation),
uncertainties (array of strings), recommended_checks (array of strings), limitations (array of strings)。
不要输出概率、置信度百分比或伪造引用。"""

def evidence_payload(raw):
    allowed = {'clinical_id', 'decision', 'critical_dates', 'recommended_action', 'top_candidates'}
    clean = {k: raw[k] for k in allowed if k in raw}
    clean['top_candidates'] = [
        {'lab_id': c['lab_id'], 'rank': c.get('rank'), 'hit_rate': c.get('hit_rate'),
         'hits': c.get('hits'), 'evidence': [
             {k:e[k] for k in ('sample_id','collection_date','nearest_visit_distance_days','role') if k in e}
             for e in c.get('evidence', [])]}
        for c in raw.get('top_candidates', [])
    ]
    return clean


def parse_json_reply(reply):
    cleaned = reply.strip()
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', cleaned).strip()
    obj = json.loads(cleaned)
    if not isinstance(obj, dict):
        raise ValueError('LLM must return a JSON object')
    return obj

def _validate_identifiers(report, evidence):
    issues=[]
    required = {'clinical_id','decision','summary','candidate_assessments',
                'uncertainties','recommended_checks','limitations'}
    missing = required - set(report)
    if missing: issues.append(f'Missing fields: {sorted(missing)}')
    if report.get('clinical_id') != evidence['clinical_id']:
        issues.append('clinical_id changed')
    if report.get('decision') != evidence['decision']:
        issues.append('upstream decision changed')
    known = {str(c['lab_id']): {str(e['sample_id']) for e in c.get('evidence', [])}
             for c in evidence.get('top_candidates', [])}
    assessments = report.get('candidate_assessments', [])
    if not isinstance(assessments, list):
        issues.append('candidate_assessments is not a list'); assessments=[]
    for a in assessments:
        if not isinstance(a, dict): issues.append('invalid candidate assessment'); continue
        lid = str(a.get('lab_id', ''))
        if lid not in known:
            issues.append(f'Invented candidate: {lid}'); continue
        for field in ('supporting_sample_ids','contradicting_sample_ids'):
            ids = a.get(field, [])
            if not isinstance(ids, list): issues.append(f'{lid}: {field} is not a list'); continue
            unknown = set(map(str, ids)) - known[lid]
            if unknown: issues.append(f'{lid}: unknown {field}: {sorted(unknown)}')
        if not isinstance(a.get('interpretation'), str):
            issues.append(f'{lid}: missing interpretation')
    if set(str(a.get('lab_id')) for a in assessments if isinstance(a, dict)) != set(known):
        issues.append('Candidate coverage mismatch')
    for field in ('uncertainties','recommended_checks','limitations'):
        if not isinstance(report.get(field), list): issues.append(f'{field} must be a list')
    # Semantic claims in free text still require human review; schema checks cannot prove factuality.
    return issues

CONFIG = {
    'deepseek': ('https://api.deepseek.com/v1', 'deepseek-chat', 'DEEPSEEK_API_KEY'),
    'openai': ('https://api.openai.com/v1', 'gpt-4.1-mini', 'OPENAI_API_KEY'),
    'ollama': ('http://localhost:11434/v1', 'qwen3:8b', None),
}


def run_report(case_path, output, *, live=False, provider=None, model=None):
    """Offline by default; never silently substitute demonstration evidence."""
    case_path, output = Path(case_path), Path(output)
    payload = evidence_payload(json.loads(case_path.read_text(encoding='utf-8')))
    output.mkdir(parents=True, exist_ok=True)
    provider = provider or os.getenv('B05_PROVIDER', 'deepseek')
    base, default_model, key_env = CONFIG[provider]
    model = model or os.getenv('B05_MODEL', default_model)
    base = os.getenv('B05_BASE_URL', base).rstrip('/')
    prompt = '请根据以下上游证据 JSON 撰写可审计的取证报告。不要添加输入中不存在的事实：\n' + json.dumps(payload, ensure_ascii=False, indent=2)
    bundle = {'metadata': {'provider':provider, 'model':model, 'source':str(case_path),
              'generated_at_utc':datetime.now(timezone.utc).isoformat(), 'live':live},
              'input_evidence':payload, 'system_prompt':SYSTEM_PROMPT, 'user_prompt':prompt}
    if not live:
        (output/'prepared_evidence.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
        return bundle
    key = os.getenv(key_env, '') if key_env else 'ollama'
    if not key:
        raise ValueError(f'Missing API key: {key_env}')
    body = {'model':model, 'messages':[{'role':'system','content':SYSTEM_PROMPT},
            {'role':'user','content':prompt}], 'temperature':0, 'stream':False}
    request = Request(base+'/chat/completions', data=json.dumps(body).encode(),
                      headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
    with urlopen(request, timeout=120) as response:
        data = json.load(response)
    reply = data['choices'][0]['message']['content']
    bundle['raw_reply'] = reply
    bundle['metadata']['usage'] = data.get('usage', {})
    try:
        report = parse_json_reply(reply)
        issues = validate_report(report, payload)
        bundle['llm_report'] = report
    except (ValueError, TypeError, KeyError) as error:
        issues = [str(error)]
    bundle['validation_issues'] = issues
    bundle['metadata']['validated'] = not issues
    slug = re.sub(r'[^a-zA-Z0-9_-]', '_', str(payload['clinical_id']))
    (output/f'{slug}_llm_audit.json').write_text(json.dumps(bundle, ensure_ascii=False, indent=2), encoding='utf-8')
    if issues:
        raise ValueError(f'Report validation failed; audit saved: {issues}')
    lines = [f'# Investigation: {report["clinical_id"]}', f'Upstream decision: {report["decision"]}', report['summary']]
    for candidate in report['candidate_assessments']:
        lines += [f'## {candidate["lab_id"]}', candidate['interpretation'],
                  'Supporting samples: '+', '.join(candidate['supporting_sample_ids']),
                  'Contradicting samples: '+', '.join(candidate['contradicting_sample_ids'])]
    for field in ['uncertainties','recommended_checks','limitations']:
        lines += ['## '+field] + ['- '+str(item) for item in report[field]]
    (output/f'{slug}_report.md').write_text('\n\n'.join(lines), encoding='utf-8')
    return bundle


def validate_report(report, evidence):
    """Structural/identifier checks do not certify free-text factual accuracy."""
    issues = _validate_identifiers(report, evidence)
    if not isinstance(report.get('summary'), str):
        issues.append('summary must be a string')
    for field in ['uncertainties','recommended_checks','limitations']:
        value = report.get(field)
        if isinstance(value, list) and not all(isinstance(x,str) for x in value):
            issues.append(f'{field} must contain strings')
    assessments = report.get('candidate_assessments')
    if isinstance(assessments,list):
        expected = [c['lab_id'] for c in evidence.get('top_candidates',[])]
        actual = [a.get('lab_id') for a in assessments if isinstance(a,dict)]
        if actual != expected:
            issues.append('Candidate order or multiplicity changed')
        candidates = {c['lab_id']:c for c in evidence.get('top_candidates',[])}
        for a in assessments:
            if not isinstance(a,dict) or not isinstance(a.get('lab_id'),str):
                continue
            candidate = candidates.get(a['lab_id'],{})
            for field,role in [('supporting_sample_ids','support'),('contradicting_sample_ids','contradiction')]:
                ids = a.get(field)
                allowed = {e['sample_id'] for e in candidate.get('evidence',[]) if e.get('role')==role}
                if not isinstance(ids,list) or not all(isinstance(x,str) for x in ids):
                    issues.append(f'{field} must be an array of strings')
                elif set(ids)-allowed:
                    issues.append(f'{field} contradicts upstream evidence roles')
    return issues
