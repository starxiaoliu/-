"""Conservative, geometry-ordered parser. Never pairs answers by global ordinal."""
import re
import pymupdf
MODULES = ['政治理论','常识判断','言语理解与表达','数量关系','判断推理','资料分析']
START = re.compile(r'^\s*(\d{1,3})[.．、](?!\d)\s*(.*)')
ANSWER = re.compile(r'(正确答案|你的答案)\s*[:：]\s*([A-D]|未作答|未答)', re.I)

def parse_pdf(content: bytes):
    with pymupdf.open(stream=content, filetype='pdf') as doc:
        if doc.is_encrypted:
            raise ValueError('不支持加密 PDF，请先解除密码')
        count = len(doc)
        if not count: raise ValueError('PDF 没有页面')
        questions, warnings, current, module = [], [], None, '待核对'
        seen = set()
        for page_no, page in enumerate(doc, 1):
            # Text sorted by geometry, with line positions available for future template adapters.
            for line in page.get_text('text', sort=True).splitlines():
                for name in MODULES:
                    if re.match(r'^[一二三四五六七八九十\d\s.．、]*' + re.escape(name) + r'(?:\s*[:：]|$)', line.strip()):
                        module = name
                match = START.match(line)
                if match:
                    number = int(match[1])
                    if number < 1: continue
                    if number in seen:
                        warnings.append(f'第{page_no}页题号{number}重复，需核对原卷')
                        current = None
                        continue
                    seen.add(number)
                    current = dict(number=number, module=module, subtype='', page_start=page_no,
                                   page_end=page_no, correct_answer=None, user_answer=None,
                                   warnings=[], confidence='low')
                    questions.append(current)
                if current:
                    current['page_end'] = page_no
                    for answer in ANSWER.finditer(line):
                        key = 'correct_answer' if answer[1] == '正确答案' else 'user_answer'
                        value = answer[2].upper()
                        if value.startswith('未'): value = '未作答'
                        if current[key] is not None:
                            current['warnings'].append(f'{answer[1]}重复，需人工核对')
                            current[key] = None
                        else: current[key] = value
                elif ANSWER.search(line):
                    warnings.append(f'第{page_no}页答案出现在可确认题号之前，未自动关联')
        if not questions: warnings.append('没有可靠识别题号；可浏览原卷并手工建题，不代表成功解析')
        if seen and seen != set(range(min(seen), max(seen)+1)): warnings.append('题号有间隔；若为专题摘录可保留原题号，请核对实际题数')
        for q in questions:
            if not q['correct_answer'] or q['correct_answer'] == '未作答':
                q['correct_answer'] = None
                q['warnings'].append('标准答案缺失或异常')
            if q['user_answer'] is None: q['warnings'].append('个人答案缺失，不等于未作答')
            if q['module'] == '待核对': q['warnings'].append('模块未识别')
            q['warnings'].append('题干或图片、跨页范围请对照原卷核对')
        return count, questions, warnings
