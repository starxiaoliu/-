"""Versioned, self-contained local backup; validate everything before atomic restore."""
import base64, hashlib, json
from pydantic import BaseModel, Field, TypeAdapter
from typing import get_type_hints, get_args
from .db import Paper, Question, Tag, Review, ReviewTag, DATA
import pymupdf
TABLES = {'papers':Paper,'questions':Question,'tags':Tag,'reviews':Review,'review_tags':ReviewTag}
def export_backup(s):
    from sqlalchemy import select
    data={'version':2,'includes_pdf':True,'tables':{},'pdfs':{}}
    for name,model in TABLES.items():
        data['tables'][name]=[{c.name:getattr(r,c.name) for c in model.__table__.columns} for r in s.scalars(select(model))]
    for p in data['tables']['papers']:
        path=DATA/'uploads'/f"{p['sha256']}.pdf"
        if not path.exists(): raise ValueError('原卷缺失，无法导出完整备份')
        data['pdfs'][p['sha256']]=base64.b64encode(path.read_bytes()).decode('ascii')
    return data

def validate_backup(data):
    if not isinstance(data,dict) or data.get('version') not in (1,2) or data.get('includes_pdf') is not True: raise ValueError('仅支持 v1/v2 含原卷的完整备份')
    tables=data.get('tables',{})
    if data['version']==1:
        for p in tables.get('papers',[]):
            p.setdefault('collection_kind','full');p.setdefault('expected_count',None)
    if set(tables)!=set(TABLES): raise ValueError('备份数据表不完整')
    for name,model in TABLES.items():
        if not isinstance(tables[name],list): raise ValueError('数据表格式错误')
        columns={c.name for c in model.__table__.columns}
        seen=set()
        for row in tables[name]:
            if not isinstance(row,dict) or set(row)!=columns: raise ValueError(f'{name} 字段不完整')
            hints=get_type_hints(model)
            for column,value in row.items(): TypeAdapter(get_args(hints[column])[0]).validate_python(value,strict=True)
            key=tuple(row[c.name] for c in model.__table__.primary_key.columns)
            if key in seen: raise ValueError('重复记录')
            seen.add(key)
    papers={p['id']:p for p in tables['papers']}
    questions={q['id']:q for q in tables['questions']}
    tags={t['code'] for t in tables['tags']}
    reviews={r['question_id'] for r in tables['reviews']}
    files={}
    hashes=set()
    for p in papers.values():
        digest=p['sha256']
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): raise ValueError('无效原卷 hash')
        if digest in hashes: raise ValueError('重复原卷')
        hashes.add(digest)
        content=base64.b64decode(data.get('pdfs',{}).get(digest,''),validate=True)
        if hashlib.sha256(content).hexdigest()!=digest: raise ValueError('原卷 hash 不匹配')
        with pymupdf.open(stream=content,filetype='pdf') as doc:
            if len(doc)!=p['page_count']: raise ValueError('页数不匹配')
        files[digest]=content
    numbers=set()
    from .main import Correction,ReviewBody
    for q in questions.values():
        p=papers.get(q['paper_id'])
        body=Correction.model_validate(q)
        if not p or not body.page_start<=body.page_end<=p['page_count']: raise ValueError('题目关联或页码错误')
        key=(q['paper_id'],q['number'])
        if key in numbers: raise ValueError('重复题号')
        numbers.add(key)
    for r in tables['reviews']:
        if r['question_id'] not in questions: raise ValueError('笔记关联错误')
        ReviewBody.model_validate(r)
    for t in tables['review_tags']:
        if t['question_id'] not in reviews or t['tag_code'] not in tags: raise ValueError('标签关联错误')
    return tables,files
