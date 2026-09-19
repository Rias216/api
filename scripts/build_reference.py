"""Generate a compact endpoint inventory from fetched official OpenAPI specs."""
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import yaml

ROOT=Path(__file__).resolve().parents[1]
SPECS=[('Polymarket Gamma','polymarket/api-spec/gamma-openapi.yaml','gamma-api.polymarket.com',''),
       ('Polymarket CLOB','polymarket/api-spec/clob-openapi.yaml','clob.polymarket.com',''),
       ('Polymarket Data','polymarket/api-spec/data-openapi.yaml','data-api.polymarket.com',''),
       ('Kalshi Trade API','kalshi/openapi.yaml','external-api.kalshi.com','/trade-api/v2')]

def resolve(spec,obj):
    while isinstance(obj,dict) and '$ref' in obj and obj['$ref'].startswith('#/'):
        parts=obj['$ref'][2:].split('/');obj=spec
        for part in parts:obj=obj[part]
    return obj

def main():
    audit=json.loads((ROOT/'reports/live-audit.json').read_text(encoding='utf-8'))
    inventory=[]
    lines=['# Endpoint inventory','', 'Generated from official OpenAPI documents retrieved for this audit. '
           'This covers the four listed REST specifications, including untested specialist operations; it does not cover FIX, Perps, relayers or every WebSocket channel.',
           '', '“Observed” means the route received at least one HTTP response; it does not establish all parameters or writes work. '
           'Authentication below is what the spec declares. Public live behavior can differ; see the guides and evidence.', '']
    for title,file,host,prefix in SPECS:
        venue,relative=file.split('/',1)
        url=f'https://docs.{venue}.com/{relative}'
        spec=yaml.load((ROOT/'.research'/file).read_text(encoding='utf-8'),Loader=yaml.CSafeLoader)
        lines += [f'## {title}', '', f"Source: [official OpenAPI]({url}), spec version `{spec['info']['version']}`.", '',
                  '| Method and path | Auth in spec | Parameters (* = required) | Observed HTTP |', '|---|---|---|---|']
        paths=spec['paths']
        # Resolve each live URL to its most specific path template.
        matched={}
        for check in audit['checks']:
            u=urlsplit(check.get('url',''))
            if u.hostname!=host:continue
            actual=u.path[len(prefix):] if u.path.startswith(prefix) else u.path
            candidates=[p for p in paths if re.fullmatch(re.sub(r'\{[^}]+\}',r'[^/]+',p),actual)]
            if candidates:
                p=min(candidates,key=lambda x:x.count('{'))
                matched.setdefault((check.get('method','GET').lower(),p),[]).append(check)
        for path,pathitem in paths.items():
            for method,op in pathitem.items():
                if method not in ['get','post','put','delete','patch']:continue
                parameters=[]
                for par in pathitem.get('parameters',[])+op.get('parameters',[]):
                    p=resolve(spec,par);s=resolve(spec,p.get('schema',{}))
                    parameters.append({'name':p['name'],'in':p['in'],'required':p.get('required',False),
                                       'type':s.get('type'),'enum':s.get('enum'),'minimum':s.get('minimum'),'maximum':s.get('maximum'),'default':s.get('default')})
                security=op.get('security',spec.get('security',[]))
                body=resolve(spec,op.get('requestBody',{}))
                body_schema=resolve(spec,body.get('content',{}).get('application/json',{}).get('schema',{}))
                observed=matched.get((method,path),[])
                statuses=sorted(set(c['http_status'] for c in observed if 'http_status' in c))
                row={'api':title,'method':method.upper(),'path':path,'summary':op.get('summary'),
                     'operation_id':op.get('operationId'),'source_url':url,'spec_security':security,'parameters':parameters,
                     'json_body_required':body.get('required',False),'json_body_required_fields':body_schema.get('required',[]),
                     'documented_response_codes':list(op.get('responses',{})),
                     'observed_check_ids':[c['id'] for c in observed],'observed_http_statuses':statuses}
                inventory.append(row)
                params=', '.join(f"`{p['name']}{'*' if p['required'] else ''}`" for p in parameters) or '—'
                if row['json_body_required_fields']:params+='; body: '+', '.join(f'`{f}*`' for f in row['json_body_required_fields'])
                lines.append(f"| `{method.upper()} {path}` | {'Required' if security else 'Public/unspecified'} | {params} | {', '.join(map(str,statuses)) or 'Not tested'} |")
        lines.append('')
    (ROOT/'docs').mkdir(exist_ok=True)
    (ROOT/'docs/endpoint-inventory.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'reports/endpoint-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'documented_operations':len(inventory),'operations_with_live_http_evidence':sum(bool(r['observed_http_statuses']) for r in inventory)}))

if __name__=='__main__':main()
