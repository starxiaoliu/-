import json
import pytest
import httpx
import pymupdf
from app import ai
from app.backup import validate_backup

def test_topic_pdf_keeps_original_gapped_numbers(client):
    with pymupdf.open() as doc:
        for n in (76,81,90):
            page=doc.new_page()
            for y,t in [(40,f'{n}. 专题图形题'),(80,'正确答案：D'),(110,'你的答案：B')]:page.insert_text((40,y),t,fontname='china-s')
        raw=doc.tobytes()
    p=client.post('/api/papers/import',files={'file':('topic.pdf',raw)},data={'collection_kind':'topic','module':'判断推理','subtype':'图形推理'}).json()['data']
    assert p['collection_kind']=='topic'
    rows=client.get('/api/papers/'+p['id']+'/questions').json()['data']
    assert [q['number'] for q in rows]==[76,81,90]
    for q in rows:
        assert q['module']=='判断推理' and q['subtype']=='图形推理'
        data={k:q[k] for k in ('number','module','subtype','page_start','page_end','correct_answer','user_answer')}
        assert client.patch('/api/questions/'+q['id'],json=dict(data,checked=True)).status_code==200
    assert client.post('/api/papers/'+p['id']+'/confirm').status_code==200
    assert client.get('/api/analytics/papers/'+p['id']).json()['data']['total']==3
    client.patch('/api/papers/'+p['id']+'/settings',json={'collection_kind':'topic','expected_count':4})
    assert client.post('/api/papers/'+p['id']+'/confirm').status_code==422

def test_ai_settings_secret_not_returned_or_backed_up(client):
    client.delete('/api/ai/settings')
    assert not client.get('/api/ai/settings').json()['data']['configured']
    assert client.put('/api/ai/settings',json={'base_url':'http://remote.test/v1','model':'test','api_key':'secret-unit-test'}).status_code==422
    settings={'base_url':'https://provider.test/v1','model':'test-model','api_key':'secret-unit-test'}
    r=client.put('/api/ai/settings',json=settings)
    assert r.status_code==200 and 'secret-unit-test' not in r.text
    assert 'secret-unit-test' not in client.get('/api/ai/settings').text
    assert 'secret-unit-test' not in client.get('/api/backups/export').text
    assert client.put('/api/ai/settings',json={'base_url':'https://another.test/v1','model':'test-model'}).status_code==422
    assert client.get('/api/ai/settings').json()['data']['base_url']=='https://provider.test/v1'

def test_ai_pdf_scope_no_automatic_review_mutation(client,pdf,monkeypatch):
    p=client.post('/api/papers/import',files={'file':('unit-ai.pdf',pdf)}).json()['data']
    q=client.get('/api/papers/'+p['id']+'/questions').json()['data'][0]
    prefix='/api/questions/'+q['id']
    preview=client.get(prefix+'/ai-context',params={'start_page':1,'end_page':1,'include_images':True}).json()['data']
    assert preview['pages']==[1] and '合成测试题' in preview['text']
    assert preview['images'][0]['url'].startswith('data:image/png;base64,')
    assert client.get(prefix+'/ai-context?start_page=1&end_page=9').status_code==422
    before=client.get(prefix+'/review').json()
    requests=[]
    def handler(request):
        requests.append(json.loads(request.content))
        assert request.url==httpx.URL('https://provider.test/v1/chat/completions')
        assert request.headers['Authorization']=='Bearer secret-unit-test'
        return httpx.Response(200,json={'choices':[{'message':{'content':'这是建议：下次先找定义主体。'}}]})
    real_client=httpx.AsyncClient
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(handler),**kw))
    body={'mode':'organize','note':'我漏看了主体','pdf_text':'我核对过的本题文字','image_pages':[1],'consent':True}
    assert client.post(prefix+'/ai-assist',json=dict(body,consent=False)).status_code==422
    assert not requests
    result=client.post(prefix+'/ai-assist',json=body)
    assert result.status_code==200,result.text
    sent=requests[0]['messages'][-1]['content']
    assert '我核对过的本题文字' in sent[0]['text']
    assert sent[1]['type']=='image_url'
    assert client.get(prefix+'/review').json()==before
    # An upstream error must not expose its body or credentials.
    def failure(request): return httpx.Response(401,text='secret-unit-test')
    monkeypatch.setattr(ai.httpx,'AsyncClient',lambda **kw:real_client(transport=httpx.MockTransport(failure),**kw))
    error=client.post(prefix+'/ai-assist',json=dict(body,mode='discuss',history=[{'role':'user','content':'为什么？'}]))
    assert error.status_code==502 and 'secret-unit-test' not in error.text
    assert client.get(prefix+'/review').json()==before
    client.delete('/api/ai/settings')
    assert client.post(prefix+'/ai-assist',json=body).status_code==409

def test_v1_backup_upgrades_collection_fields(client):
    data=client.get('/api/backups/export').json()
    assert data['version']==2
    data['version']=1
    for p in data['tables']['papers']:p.pop('collection_kind');p.pop('expected_count')
    tables,_=validate_backup(data)
    assert all(p['collection_kind']=='full' and p['expected_count'] is None for p in tables['papers'])

def test_topic_without_answers_stays_unknown(client):
    with pymupdf.open() as doc:
        p=doc.new_page();p.insert_text((40,60),'81. 只有图形的专题题，没有答案',fontname='china-s');raw=doc.tobytes()
    p=client.post('/api/papers/import',files={'file':('no-key.pdf',raw)},data={'collection_kind':'topic','module':'判断推理','subtype':'图形推理'}).json()['data']
    stats=client.get('/api/analytics/papers/'+p['id']).json()['data']
    assert stats['total']==1 and stats['unknown']==1 and stats['wrong']==0 and stats['accuracy'] is None
