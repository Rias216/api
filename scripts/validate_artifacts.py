"""Check documentation links/syntax, source metadata and credential redaction."""
import ast
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit,unquote
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]

def main():
    errors=[];links=0;snippets=0
    files=[p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.relative_to(ROOT).parts for x in
           ['.git','.venv','.research','__pycache__','.pytest_cache'])]
    for p in files:
        if p.suffix!='.md':continue
        text=p.read_text(encoding='utf-8')
        for label,target in re.findall(r'\[([^\]]+)\]\(([^)]+)\)',text):
            if target.startswith(('https://','http://','#','mailto:')):continue
            target=unquote(target.split('#')[0])
            if not target:continue
            links+=1
            if not (p.parent/target).exists():errors.append(f'Broken local link in {p.relative_to(ROOT)}: {target}')
        for code in re.findall(r'```python\n(.*?)\n```',text,re.S):
            snippets+=1
            try:ast.parse(code)
            except SyntaxError as e:errors.append(f'Python snippet syntax in {p.relative_to(ROOT)}: {e}')
    scanned=0
    for p in files:
        if p.suffix not in {'.md','.json','.py','.txt','.xml'}:continue
        scanned+=1;content=p.read_text(encoding='utf-8-sig')
        for k,v in os.environ.items():
            if k.startswith(('POLYMARKET_','KALSHI_')) and len(v)>=8 and v in content:
                errors.append(f'Configured value found in {p.relative_to(ROOT)} ({k}; value not printed)')
        if '-----BEGIN PRIVATE KEY-----' in content or '-----BEGIN RSA PRIVATE KEY-----' in content:
            # These markers must not appear as literal private material in artifacts.
            if p.name!='validate_artifacts.py':errors.append(f'PEM marker in {p.relative_to(ROOT)}')
    audit=json.loads((ROOT/'reports/live-audit.json').read_text(encoding='utf-8'))
    from collections import Counter
    if dict(Counter(r['status'] for r in audit['checks']))!=audit['counts']:errors.append('Audit counts do not match rows')
    manifest=json.loads((ROOT/'reports/sources.json').read_text(encoding='utf-8'))
    if any(r['http_status']!=200 for r in manifest):errors.append('A source retrieval did not return 200')
    xml=ET.parse(ROOT/'reports/unit-tests.xml')
    tests=sum(int(x.get('tests','0')) for x in xml.findall('.//testsuite'))
    failures=sum(int(x.get('failures','0'))+int(x.get('errors','0')) for x in xml.findall('.//testsuite'))
    result={'at':datetime.now(timezone.utc).isoformat(),'local_links_checked':links,'python_snippets_parsed':snippets,
            'artifact_files_scanned':scanned,'source_manifest_entries':len(manifest),'offline_tests':tests,
            'offline_test_failures':failures,'audit_counts':audit['counts'],'errors':errors}
    (ROOT/'reports/artifact-validation.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return bool(errors) or bool(failures)

if __name__=='__main__':raise SystemExit(main())
