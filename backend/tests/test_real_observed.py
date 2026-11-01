import os
import pytest
@pytest.mark.skipif(not os.getenv('SAMPLE_PDF'),reason='Set SAMPLE_PDF for the private real-file regression')
def test_current_uploaded_pdf_regression(client):
    import json,hashlib
    from pathlib import Path
    expected=json.loads((Path(__file__).resolve().parents[2]/'docs/real-sample-result.json').read_text(encoding='utf-8'))
    content=Path(os.environ['SAMPLE_PDF']).read_bytes()
    if hashlib.sha256(content).hexdigest()!=expected['sha256']: pytest.skip('This observed baseline is only for the inspected PDF hash')
    p=client.post('/api/papers/import',files={'file':('private.pdf',content)}).json()['data']
    rows=client.get('/api/papers/'+p['id']+'/questions').json()['data']
    assert p['page_count']==40 and len(rows)==130
    assert {r['number'] for r in rows}==set(range(1,131))
    assert sum(r['answer_status']=='correct' for r in rows)==84
    assert sum(r['answer_status']=='wrong' for r in rows)==46
    for m in expected['modules']:
        group=[q for q in rows if q['module']==m['module']]
        assert len(group)==m['total']
        assert sum(q['answer_status']=='correct' for q in group)==m['correct']
    for check in expected['spot_checks']:
        q=next(q for q in rows if q['number']==check['number'])
        for key,value in check.items(): assert q[key]==value
