"""Generate an original, text-based two-question PDF for UI tests."""
from pathlib import Path
import pymupdf
root=Path(__file__).resolve().parents[2]
target=root/'tests/fixtures/private/synthetic-e2e.pdf'
target.parent.mkdir(parents=True,exist_ok=True)
with pymupdf.open() as doc:
    for n in (1,2):
        page=doc.new_page()
        for y,text in [(40,'一. 政治理论'),(80,f'{n}. 浏览器合成验收题'),(120,'正确答案：B'),(150,'你的答案：B')]:
            page.insert_text((40,y),text,fontname='china-s')
    doc.save(target)
