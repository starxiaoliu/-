from contextlib import asynccontextmanager
from hashlib import sha256
from pathlib import Path
from fastapi import FastAPI, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from .db import DATA, Session, Paper, Question, Tag
from .parser import parse_pdf, MODULES
import os
from typing import Literal

def public(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}
def result(q):
    if not q.correct_answer: return 'unknown'
    if q.user_answer == '未作答': return 'unanswered'
    if not q.user_answer: return 'unknown'
    return 'correct' if q.correct_answer == q.user_answer else 'wrong'
def question_data(q): return dict(public(q), answer_status=result(q))
def need(s, model, key):
    row = s.get(model, key)
    if row is None: raise HTTPException(404, '记录不存在')
    return row
@asynccontextmanager
async def lifespan(app):
    # Schema changes are applied only by Alembic, never by dropping user data.
    with Session.begin() as s:
        import json
        for tag in json.loads(Path(__file__).with_name('tags.json').read_text(encoding='utf-8')):
            if not s.get(Tag, tag['code']): s.add(Tag(**tag))
    yield
app = FastAPI(title='行测复盘工作台', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=['http://localhost:5173','http://127.0.0.1:5173'], allow_methods=['GET','POST','PATCH','PUT','DELETE'], allow_headers=['Content-Type'])
@app.exception_handler(HTTPException)
async def error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'data':None,'error':exc.detail,'meta':{}})
def ok(data): return {'data':data,'error':None,'meta':{}}
@app.get('/api/health')
def health(): return ok({'status':'ok'})
@app.get('/api/papers')
def papers():
    with Session() as s:
        return ok([dict(public(p), **stats(s, list(s.scalars(select(Question).where(Question.paper_id==p.id))))) for p in s.scalars(select(Paper))])
@app.post('/api/papers/import')
async def import_pdf(file: UploadFile, collection_kind: Literal['full','topic'] = Form('full'), module: str = Form('',max_length=100), subtype: str = Form('',max_length=100)):
    limit = int(os.getenv('MAX_UPLOAD_MB','30')) * 1024 * 1024
    content = await file.read(limit + 1)
    if len(content) > limit: raise HTTPException(413, '文件超过体积限制')
    if not (file.filename or '').lower().endswith('.pdf') or not content.startswith(b'%PDF-'):
        raise HTTPException(422,'请选择真实 PDF 文件')
    digest = sha256(content).hexdigest()
    with Session.begin() as s:
        existing = s.scalar(select(Paper).where(Paper.sha256 == digest))
        if existing: return ok(dict(public(existing),duplicate=True))
        try: pages, rows, warnings = parse_pdf(content)
        except Exception as exc: raise HTTPException(422, f'PDF 无法解析：{exc}')
        target = DATA / 'uploads' / f'{digest}.pdf'
        temp = target.with_suffix('.tmp')
        temp.write_bytes(content)
        temp.replace(target)
        p = Paper(title=Path(file.filename.replace('\\','/')).name,sha256=digest,page_count=pages,warnings=warnings,collection_kind=collection_kind)
        s.add(p); s.flush()
        for row in rows:
            if module: row['module']=module
            if subtype: row['subtype']=subtype
            s.add(Question(paper_id=p.id, **row))
        return ok(public(p))
@app.get('/api/papers/{pid}')
def paper(pid: str):
    with Session() as s:
        p = need(s,Paper,pid)
        rows = list(s.scalars(select(Question).where(Question.paper_id == pid).order_by(Question.number)))
        return ok(dict(public(p),questions=[question_data(q) for q in rows]))
@app.get('/api/papers/{pid}/pdf')
def pdf(pid: str):
    with Session() as s: digest = need(s,Paper,pid).sha256
    return FileResponse(DATA / 'uploads' / f'{digest}.pdf', media_type='application/pdf')
class Correction(BaseModel):
    number: int = Field(ge=1,le=1000)
    module: str = Field(min_length=1,max_length=100)
    subtype: str = Field(default='',max_length=100)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    correct_answer: str | None = Field(default=None,pattern='^[ABCD]$')
    user_answer: str | None = Field(default=None,pattern='^(?:[ABCD]|未作答)$')
    checked: bool = False

def apply(s, q, body):
    p = need(s,Paper,q.paper_id)
    if not body.page_start <= body.page_end <= p.page_count: raise HTTPException(422,'起止页超出原卷范围')
    duplicate = s.scalar(select(Question).where(Question.paper_id==p.id,Question.number==body.number,Question.id!=q.id))
    if duplicate: raise HTTPException(409,'题号已存在')
    for key,value in body.model_dump(exclude={'checked'}).items(): setattr(q,key,value)
    q.warnings = [] if body.checked else ['字段已修改，仍需勾选人工核对']
    q.confidence = 'manual' if body.checked else 'low'
    p.parse_status = 'needs_review'
@app.patch('/api/questions/{qid}')
def correct(qid: str, body: Correction):
    with Session.begin() as s:
        q = need(s,Question,qid); apply(s,q,body); s.flush()
        return ok(question_data(q))
@app.post('/api/papers/{pid}/questions')
def add_question(pid: str, body: Correction):
    with Session.begin() as s:
        need(s,Paper,pid)
        q = Question(paper_id=pid)
        # Assign a temporary UUID before duplicate validation.
        from uuid import uuid4
        q.id = str(uuid4())
        apply(s,q,body); s.add(q); s.flush()
        return ok(question_data(q))
@app.post('/api/papers/{pid}/confirm')
def confirm(pid: str):
    with Session.begin() as s:
        p = need(s,Paper,pid)
        rows = list(s.scalars(select(Question).where(Question.paper_id==pid)))
        nums = {q.number for q in rows}
        if not rows: raise HTTPException(422,'请先添加或核对题目')
        if p.collection_kind=='full' and nums != set(range(1,len(rows)+1)): raise HTTPException(422,'整卷题号不连续；若为专题摘录，请切换为专题题集并核对实际题数')
        if p.expected_count is not None and len(rows)!=p.expected_count: raise HTTPException(422,'识别题数与预期题数不一致，请核对')
        if any(q.warnings for q in rows): raise HTTPException(422,'请逐题核对并保存后再确认')
        p.parse_status = 'confirmed'
        return ok(public(p))
@app.get('/api/tags')
def tags():
    with Session() as s: return ok([public(t) for t in s.scalars(select(Tag))])
from .db import Review, ReviewTag
from sqlalchemy import delete
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

def review_data(s, qid):
    r = s.get(Review,qid)
    data = public(r) if r else dict(question_id=qid,status='not_started',attempt_flags=[],note='',correct_method='',next_time_rule='',review_later=False,updated_at='')
    data['tag_ids'] = list(s.scalars(select(ReviewTag.tag_code).where(ReviewTag.question_id==qid)))
    return data
class ReviewBody(BaseModel):
    status: Literal['not_started','in_progress','completed'] = 'not_started'
    attempt_flags: list[Literal['guessed','hesitant','overtime','unread_stem']] = []
    tag_ids: list[str] = []
    note: str = Field(default='',max_length=100000)
    correct_method: str = Field(default='',max_length=100000)
    next_time_rule: str = Field(default='',max_length=100000)
    review_later: bool = False
@app.get('/api/questions/{qid}/review')
def get_review(qid:str):
    with Session() as s:
        need(s,Question,qid)
        return ok(review_data(s,qid))
@app.put('/api/questions/{qid}/review')
def save_review(qid:str,body:ReviewBody):
    with Session.begin() as s:
        need(s,Question,qid)
        for tag in set(body.tag_ids): need(s,Tag,tag)
        has_content=bool(body.note.strip() or body.correct_method.strip() or body.next_time_rule.strip() or body.tag_ids)
        if body.status=='completed' and not has_content: raise HTTPException(422,'请至少填写一项笔记或标签再标记完成')
        r=s.get(Review,qid)
        if not r: r=Review(question_id=qid);s.add(r)
        for key,value in body.model_dump(exclude={'tag_ids'}).items(): setattr(r,key,value)
        if r.status=='not_started' and (has_content or body.attempt_flags): r.status='in_progress'
        r.attempt_flags=list(dict.fromkeys(r.attempt_flags))
        r.updated_at=datetime.now(timezone.utc).isoformat()
        s.flush()
        s.execute(delete(ReviewTag).where(ReviewTag.question_id==qid))
        for tag in set(body.tag_ids): s.add(ReviewTag(question_id=qid,tag_code=tag))
        s.flush()
        return ok(review_data(s,qid))
class TagBody(BaseModel):
    label:str=Field(min_length=1,max_length=100)
    module:str=Field(default='',max_length=100)
    subtype:str=Field(default='',max_length=100)
@app.post('/api/tags')
def add_tag(body:TagBody):
    with Session.begin() as s:
        label=body.label.strip()
        if not label: raise HTTPException(422,'标签不能为空')
        tag=s.scalar(select(Tag).where(Tag.label==label,Tag.module==body.module,Tag.subtype==body.subtype))
        if not tag: tag=Tag(code=str(uuid4()),label=label,module=body.module,subtype=body.subtype,origin='custom');s.add(tag);s.flush()
        return ok(public(tag))
@app.delete('/api/tags/{code}')
def hide_tag(code:str):
    # Preserve history; hidden tags remain associated with reviews.
    with Session.begin() as s:
        t=need(s,Tag,code)
        if t.origin=='system': raise HTTPException(422,'系统标签不能删除')
        t.origin='hidden'
        return ok(public(t))
@app.get('/api/papers/{pid}/questions')
def questions(pid:str):
    with Session() as s:
        need(s,Paper,pid)
        return ok([dict(question_data(q),review=review_data(s,q.id)) for q in s.scalars(select(Question).where(Question.paper_id==pid).order_by(Question.number))])

def stats(s,rows):
    from collections import Counter
    counts=Counter(result(q) for q in rows)
    tags=Counter()
    completed=0
    for q in rows:
        r=review_data(s,q.id)
        completed+=r['status']=='completed'
        tags.update(r['tag_ids'])
    denominator=counts['correct']+counts['wrong']
    return dict(total=len(rows),correct=counts['correct'],wrong=counts['wrong'],unanswered=counts['unanswered'],unknown=counts['unknown'],accuracy=round(100*counts['correct']/denominator,2) if denominator else None,completed=completed,completion=round(100*completed/len(rows),2) if rows else 0,tags=[dict(code=k,label=need(s,Tag,k).label,count=v) for k,v in tags.most_common()])
@app.get('/api/analytics/papers/{pid}')
def analytics(pid:str):
    with Session() as s:
        p=need(s,Paper,pid)
        rows=list(s.scalars(select(Question).where(Question.paper_id==pid)))
        return ok(dict(stats(s,rows),trusted=p.parse_status=='confirmed',modules=[dict(module=m,**stats(s,[q for q in rows if q.module==m])) for m in dict.fromkeys(q.module for q in rows)]))
@app.get('/api/analytics/overview')
def overview():
    with Session() as s: return ok(stats(s,list(s.scalars(select(Question)))))
@app.get('/api/reviews')
def notes(keyword:str='',module:str='',tag:str='',answer_status:str=''):
    with Session() as s:
        out=[]
        for q in s.scalars(select(Question).join(Review,Review.question_id==Question.id).order_by(Review.updated_at.desc())):
            r=review_data(s,q.id)
            labels=[need(s,Tag,t).label for t in r['tag_ids']]
            if keyword and keyword.lower() not in (' '.join([r['note'],r['correct_method'],r['next_time_rule'],*labels])).lower(): continue
            if module and q.module!=module: continue
            if tag and tag not in r['tag_ids']: continue
            if answer_status and result(q)!=answer_status: continue
            out.append(dict(question_data(q),review=r,tag_labels=labels,paper_title=need(s,Paper,q.paper_id).title))
        return ok(out)
@app.delete('/api/papers/{pid}')
def delete_paper(pid:str):
    with Session.begin() as s:
        p=need(s,Paper,pid)
        s.delete(p)
        # Original file retained for recovery until user explicitly cleans local uploads.
        return ok({'deleted':pid})
from .backup import export_backup,validate_backup,TABLES
import json
@app.get('/api/backups/export')
def backup_export():
    with Session() as s:
        try: data=export_backup(s)
        except ValueError as exc: raise HTTPException(422,str(exc))
        return JSONResponse(data,headers={'Content-Disposition':'attachment; filename="xingce-backup.json"'})
@app.post('/api/backups/import')
async def backup_import(file:UploadFile,confirm:bool=False):
    content=await file.read(120*1024*1024+1)
    if len(content)>120*1024*1024: raise HTTPException(413,'备份超过 120 MB')
    try:
        tables,files=validate_backup(json.loads(content))
    except Exception as exc: raise HTTPException(422,f'备份校验失败：{exc}')
    summary={name:len(rows) for name,rows in tables.items()}
    if not confirm: return ok(dict(preview=True,counts=summary,warning='确认恢复将替换本地全部试卷、标签和笔记，请先导出当前数据'))
    with Session.begin() as s:
        # Immutable hash files can be staged before committing the database.
        for digest,raw in files.items():
            target=DATA/'uploads'/f'{digest}.pdf'
            tmp=target.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(target)
        for model in reversed(list(TABLES.values())): s.execute(delete(model))
        for name,model in TABLES.items():
            for row in tables[name]: s.add(model(**row))
            s.flush()
    return ok(dict(restored=True,counts=summary))
@app.delete('/api/questions/{qid}')
def delete_question(qid:str):
    with Session.begin() as s:
        q=need(s,Question,qid)
        need(s,Paper,q.paper_id).parse_status='needs_review'
        s.delete(q)
        return ok({'deleted':qid})
from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    return JSONResponse(status_code=422,content={'data':None,'error':'字段校验失败，请检查题号、答案、页码与状态','meta':{'fields':[str(e['loc']) for e in exc.errors()]}})
class CollectionSettings(BaseModel):
    collection_kind: Literal['full','topic']
    expected_count: int | None = Field(default=None,ge=1,le=1000)
    module: str = Field(default='',max_length=100)
    subtype: str = Field(default='',max_length=100)
@app.patch('/api/papers/{pid}/settings')
def collection_settings(pid:str,body:CollectionSettings):
    with Session.begin() as s:
        p=need(s,Paper,pid)
        p.collection_kind=body.collection_kind;p.expected_count=body.expected_count;p.parse_status='needs_review'
        if body.module or body.subtype:
            for q in s.scalars(select(Question).where(Question.paper_id==pid)):
                if body.module:q.module=body.module
                if body.subtype:q.subtype=body.subtype
                q.warnings=['分类已批量修改，请对照原卷核对'];q.confidence='low'
        return ok(public(p))
from .ai import router as ai_router
app.include_router(ai_router)
