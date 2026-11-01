import os
import tempfile
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ['DATA_DIR'] = tempfile.mkdtemp(prefix='xingce-tests-')
import pytest
import pymupdf
from fastapi.testclient import TestClient
from app.db import Base,engine
from app.main import app
Base.metadata.create_all(engine)
@pytest.fixture
def client():
    with TestClient(app) as c: yield c
@pytest.fixture
def pdf():
    d=pymupdf.open()
    p=d.new_page()
    p.insert_text((40,40),'一. 政治理论',fontname='china-s')
    p.insert_text((40,80),'1. 合成测试题',fontname='china-s')
    p.insert_text((40,110),'正确答案：B',fontname='china-s')
    p.insert_text((40,140),'你的答案：D',fontname='china-s')
    p=d.new_page()
    p.insert_text((40,40),'2. 合成测试题',fontname='china-s')
    p.insert_text((40,70),'正确答案：A',fontname='china-s')
    p.insert_text((40,100),'你的答案：未作答',fontname='china-s')
    content=d.tobytes();d.close();return content
