from __future__ import annotations
import csv
import hashlib
import html
import io
import json
import math
import re
import threading
import time
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import feedparser

CATEGORIES = ['General', 'Videojuegos', 'Tecnología', 'Entretenimiento', 'Actualidad del Perú']
CRITERIA = ['Actualidad', 'Público objetivo', 'Evidencia de interés', 'Fuentes', 'Originalidad', 'Facilidad de producción', 'Baja competencia observable']
WARNINGS = ['Estimación editorial, no probabilidad de viralidad.', 'Verificar las fuentes originales antes de publicar.']
DEFAULT_SOURCES = [
    dict(name='BBC Mundo', url='https://feeds.bbci.co.uk/mundo/rss.xml', category='General', country='', favorite=True),
    dict(name='NASA', url='https://www.nasa.gov/feed/', category='Tecnología', country='US', favorite=False),
    dict(name='PlayStation Blog', url='https://blog.playstation.com/feed/', category='Videojuegos', country='', favorite=True),
    dict(name='Andina', url='https://andina.pe/agencia/rss/noticia.aspx', category='Actualidad del Perú', country='PE', favorite=True),
]

class UserError(Exception): pass
class Cancelled(UserError): pass

def now(): return datetime.now(timezone.utc).isoformat()
def clean(text): return html.unescape(re.sub('<[^>]+>', ' ', str(text or ''))).strip()
def normalized(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+', text))
def safe_url(url):
    p = urlsplit(str(url).strip())
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise UserError('Introduce un enlace HTTP o HTTPS válido, sin contraseñas.')
    return urlunsplit(p)
def canonical(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip('/'), urlencode(sorted((k,v) for k,v in parse_qsl(p.query) if not k.startswith('utm_') and k not in ('fbclid','gclid'))), ''))
def date(value):
    try:
        parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError): return None
def atomic_json(path, data):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    tmp.replace(path)
def read_json(path):
    p = Path(path)
    if p.stat().st_size > 25_000_000: raise UserError('Archivo demasiado grande (máximo 25 MB).')
    return json.loads(p.read_text(encoding='utf-8-sig'))
def item(title, url, source='Manual', category='General', country='', published='', summary='', origin='manual', observed=None):
    return dict(id=str(uuid.uuid4()), title=clean(title), url=safe_url(url), source=source, category=category,
                country=country.upper(), published=published, retrieved=now(), summary=clean(summary), origin=origin,
                observed=observed or {}, sources=[dict(name=source, url=safe_url(url), published=published, retrieved=now())])
def dedupe(items):
    result=[];by_url={};by_title={};tokens={}
    for entry in items:
        title=normalized(entry['title']);url=canonical(entry['url']);match=by_url.get(url)
        if match is None and len(title)>20:match=by_title.get(title)
        anchors=[w for w in title.split() if len(w)>3][:3]
        if match is None and len(title)>20:
            candidates=set()
            for word in anchors:candidates.update(tokens.get(word,[]))
            match=next((result[i] for i in sorted(candidates)[-100:] if SequenceMatcher(None,normalized(result[i]['title']),title).ratio()>=.91),None)
        if match:
            known={s['url'] for s in match['sources']}
            match['sources'].extend(s for s in entry['sources'] if s['url'] not in known)
        else:
            match=dict(entry,sources=list(entry['sources']));result.append(match)
            for word in anchors:tokens.setdefault(word,[]).append(len(result)-1)
        by_url[url]=match;by_title[title]=match
    return result
def filtered(items, keyword='', category='', country='', days=0):
    words=normalized(keyword).split(); cutoff=datetime.now(timezone.utc)-timedelta(days=days)
    return [r for r in items if (not category or r['category']==category) and (not country or r['country']==country.upper())
            and all(w in normalized(r['title']+' '+r['summary']) for w in words)
            and (not days or (date(r['published']) is not None and date(r['published']) >= cutoff))]

class Http:
    def __init__(self, cache_dir, ttl=30, cancel=None):
        self.root=Path(cache_dir); self.ttl=ttl*60; self.cancel=cancel or threading.Event(); self.last=0; self.requests=0; self.hits=0
    def check(self):
        if self.cancel.is_set(): raise Cancelled('Consulta cancelada.')
    def get(self, url, headers=None, cache=True):
        self.check(); safe_url(url)
        key=hashlib.sha256(url.encode()).hexdigest(); path=self.root/(key+'.json')
        if cache and self.ttl and path.exists():
            try:
                data=read_json(path)
                if time.time()-data['time'] < self.ttl:
                    self.hits+=1; return data['body'].encode('utf-8'), data['retrieved']
            except (ValueError, OSError, KeyError): pass
        if self.cancel.wait(max(0, .6-(time.monotonic()-self.last))): self.check()
        self.last=time.monotonic(); self.requests+=1
        try:
            with urlopen(Request(url, headers={'User-Agent':'TrendStudio/1.0 (+manual research)', **(headers or {})}), timeout=12) as response:
                raw=response.read(4_000_001)
                if len(raw)>4_000_000: raise UserError('La fuente supera el límite de 4 MB.')
        except HTTPError as e:
            reason=''
            try: reason=e.read(8000).decode('utf-8', errors='replace')
            except OSError: pass
            if e.code==429 or 'quotaExceeded' in reason or 'dailyLimitExceeded' in reason:
                raise UserError('Se alcanzó el límite de consultas. Espera o revisa la cuota del proyecto en Google Cloud.') from None
            if e.code in (401,403): raise UserError('Acceso denegado. Revisa la API habilitada, la clave y sus restricciones.') from None
            raise UserError(f'La fuente no está disponible (HTTP {e.code}).') from None
        except (URLError, TimeoutError, OSError): raise UserError('No se pudo conectar con la fuente. Comprueba internet e inténtalo más tarde.') from None
        self.check(); stamp=now()
        # El caché conserva texto UTF-8 y la fecha real de consulta.
        if cache and self.ttl:
            try:
                if path.exists() or sum(1 for _ in self.root.glob('*.json'))<200:atomic_json(path, dict(time=time.time(), retrieved=stamp, body=raw.decode('utf-8-sig')))
            except (UnicodeDecodeError, OSError): pass
        return raw, stamp

def parse_feed(raw, source, stamp):
    from defusedxml.ElementTree import fromstring
    from defusedxml.common import DefusedXmlException
    from xml.etree.ElementTree import ParseError
    try: fromstring(raw)
    except (DefusedXmlException, ParseError): raise UserError('La fuente no contiene XML seguro y válido.') from None
    feed=feedparser.parse(raw)
    if not feed.entries and (feed.bozo or not feed.get('version')): raise UserError('La dirección no contiene un RSS o Atom válido.')
    result=[]
    for e in feed.entries[:150]:
        if not e.get('link') or not e.get('title'): continue
        parsed=e.get('published_parsed') or e.get('updated_parsed')
        published=datetime(*parsed[:6], tzinfo=timezone.utc).isoformat() if parsed else ''
        try: r=item(e.title, e.link, source['name'], source['category'], source.get('country',''), published, e.get('summary',''), 'rss')
        except UserError: continue
        r['retrieved']=stamp; r['sources'][0]['retrieved']=stamp; result.append(r)
    return result
def radar(http, sources):
    rows=[]; errors=[]
    for s in sources[:30]:
        http.check()
        try:
            raw, stamp=http.get(s['url']); rows.extend(parse_feed(raw,s,stamp))
        except Cancelled: raise
        except UserError as e: errors.append(s['name']+': '+str(e))
    return dict(items=dedupe(rows), errors=errors, requests=http.requests, hits=http.hits)

class YouTube:
    def __init__(self,http,key): self.http=http; self.key=key
    def call(self, endpoint, **params):
        if not self.key: raise UserError('Configura tu clave de YouTube o importa información manualmente.')
        raw, stamp=self.http.get('https://www.googleapis.com/youtube/v3/'+endpoint+'?'+urlencode(params), headers={'X-Goog-Api-Key':self.key})
        try: return json.loads(raw),stamp
        except ValueError: raise UserError('YouTube devolvió una respuesta no válida.') from None
    def search(self, query='', days=30, channel=''):
        params=dict(part='snippet', type='video', maxResults=25, order='date')
        if query: params['q']=query
        if channel:
            channel=channel.strip().rstrip('/').split('/')[-1]
            selector={'forHandle':channel} if channel.startswith('@') else {'id':channel}
            data,_=self.call('channels',part='id',**selector)
            if not data.get('items'): raise UserError('No se encontró el canal. Usa su @usuario o ID UC…')
            params['channelId']=data['items'][0]['id']
        if days: params['publishedAfter']=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()
        data,_=self.call('search',**params)
        ids=','.join(r['id']['videoId'] for r in data.get('items',[]) if 'videoId' in r['id'])
        if not ids: return dict(items=[],errors=[],requests=self.http.requests,hits=self.http.hits)
        data,stamp=self.call('videos',part='snippet,statistics,contentDetails',id=ids)
        channels=','.join(sorted({r['snippet']['channelId'] for r in data['items']}))
        ch,_=self.call('channels',part='snippet,statistics',id=channels)
        cmap={r['id']:r for r in ch.get('items',[])}; rows=[]
        for v in data['items']:
            s=v['snippet']; obs=dict(v.get('statistics',{})); c=cmap.get(s['channelId'],{})
            obs.update(duration=v['contentDetails']['duration'], channel=s['channelTitle'], channelId=s['channelId'])
            cs=c.get('statistics',{})
            if not cs.get('hiddenSubscriberCount',True) and 'subscriberCount' in cs: obs['subscriberCount']=cs['subscriberCount']
            r=item(s['title'],'https://www.youtube.com/watch?v='+v['id'],'YouTube',summary=s.get('description',''),published=s['publishedAt'],origin='youtube_api', observed=obs)
            r['retrieved']=stamp; r['sources'][0]['retrieved']=stamp; rows.append(r)
        return dict(items=rows, errors=[], requests=self.http.requests,hits=self.http.hits)

def import_csv(path):
    text=Path(path).read_text(encoding='utf-8-sig')
    if len(text)>4_000_000: raise UserError('CSV demasiado grande (máximo 4 MB).')
    try: dialect=csv.Sniffer().sniff(text[:4096], delimiters=',;\t')
    except csv.Error: dialect=csv.excel
    reader=csv.DictReader(io.StringIO(text),dialect=dialect)
    if not {'title','url'}.issubset(reader.fieldnames or []): raise UserError('El CSV debe incluir las columnas title y url. Consulta la plantilla en docs.')
    rows=[]
    for n,r in enumerate(reader,2):
        if n>2001: raise UserError('Máximo 2000 filas por importación.')
        try:
            obs={k:r[k] for k in ('viewCount','likeCount','subscriberCount','duration','channel') if r.get(k)}
            for k in ('viewCount','likeCount','subscriberCount'):
                if k in obs and (not obs[k].isdigit()): raise UserError('Las cifras deben ser enteros no negativos.')
            published=r.get('published','')
            if published and date(published) is None: raise UserError('Fecha inválida; utiliza ISO 8601.')
            rows.append(item(r['title'],r['url'],r.get('source') or 'Manual',r.get('category') or 'General',r.get('country',''),published,r.get('summary',''), 'manual_csv', obs))
        except (UserError,TypeError) as e: raise UserError(f'Fila {n}: {e}') from None
    return rows

def import_trends(path, topic, url, country=''):
    text=Path(path).read_text(encoding='utf-8-sig')
    if len(text)>4_000_000: raise UserError('CSV demasiado grande.')
    lines=text.splitlines(); start=None
    for i,line in enumerate(lines):
        first=line.split(',')[0].strip().lower()
        if first in ('day','week','month','día','dia','semana','mes','date','fecha'): start=i; break
    if start is None: raise UserError('Usa el CSV «Interés a lo largo del tiempo» exportado de Google Trends.')
    data=list(csv.reader(lines[start:])); samples=[]
    for row in data[1:]:
        if len(row)<2: continue
        if row[1]=='<1': value='<1'
        else:
            try: value=int(row[1])
            except ValueError: continue
            if not 0<=value<=100: raise UserError('Índice de Trends fuera del rango 0–100.')
        samples.append(dict(date=row[0],index=value))
    if not samples: raise UserError('El CSV no contiene índices reconocibles.')
    r=item(topic,url,'Google Trends',country=country,origin='google_trends_csv',summary='Índice relativo 0–100 de la primera serie del CSV; no representa un volumen de búsquedas.',observed={'series':data[0][1], 'samples':samples})
    return [r]

def score(ratings,weights):
    if not isinstance(ratings,dict) or not isinstance(weights,dict):raise UserError('Valoraciones inválidas.')
    if set(ratings)!=set(CRITERIA) or set(weights)!=set(CRITERIA):raise UserError('Faltan criterios de evaluación.')
    if any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in [*ratings.values(),*weights.values()]):raise UserError('La evaluación debe contener números finitos.')
    total=sum(weights.values())
    if total<=0: raise UserError('Al menos un criterio debe tener peso mayor que cero.')
    if any(not 0<=v<=5 for v in ratings.values()) or any(not 0<=v<=10 for v in weights.values()): raise UserError('Valoraciones o pesos inválidos.')
    contributions={c:round(ratings.get(c,0)/5*weights.get(c,0)/total*100,2) for c in CRITERIA}
    return round(sum(contributions.values()),1),contributions
def opportunity(row,ratings,weights,notes='',angle='',state='Guardada'):
    value,parts=score(ratings,weights)
    return dict(id=str(uuid.uuid4()), topic=row['title'],category=row['category'],summary=row['summary'],sources=row['sources'],
        published=row['published'],retrieved=row['retrieved'],observed=dict(row['observed']),origin=row['origin'],notes=notes,angles=[angle] if angle else [],warnings=list(WARNINGS),
        status=state,ratings=ratings,weights=weights,score=value,contributions=parts)
def validate_project(data):
    if not isinstance(data,dict) or data.get('schema')!='trendstudio.research.v1': raise UserError('Formato de investigación no compatible.')
    if not all(isinstance(data.get(k),list) for k in ('items','opportunities','channels')): raise UserError('Investigación incompleta.')
    try:
        for r in data['items']:
            for k in ('id','title','url','source','category','country','published','retrieved','summary','origin'): assert isinstance(r[k],str)
            safe_url(r['url']); assert isinstance(r['observed'],dict)
            for s in r['sources']: safe_url(s['url'])
        for o in data['opportunities']:
            for k in ('id','topic','category','summary','notes','status'): assert isinstance(o[k],str)
            score(o['ratings'],o['weights'])
            for k in ('published','retrieved','origin'): assert isinstance(o[k],str)
            assert isinstance(o['observed'],dict) and isinstance(o['angles'],list)
            assert isinstance(o['score'],(int,float))
            assert isinstance(o['contributions'],dict)
            for s in o['sources']: safe_url(s['url'])
        assert all(isinstance(c,str) for c in data['channels'])
        if 'analyses' in data:
            from .intelligence import validate
            assert isinstance(data['analyses'],list)
            for a in data['analyses']:
                for k in ('id','created','model'):assert isinstance(a[k],str)
                assert isinstance(a['input_ids'],list) and isinstance(a['sources'],dict)
                validate(a['result'],list(a['sources']))
                for s in a['sources'].values():
                    safe_url(s['url'])
                    for k in ('title','retrieved','published'):assert isinstance(s[k],str)
        if 'groups' in data:
            assert isinstance(data['groups'],list)
            for g in data['groups']:assert isinstance(g['item_ids'],list)
    except (KeyError,TypeError,AssertionError,ValueError,AttributeError): raise UserError('La investigación contiene campos no válidos.') from None
    return data
def new_project(): return dict(schema='trendstudio.research.v1',created=now(),items=[],opportunities=[],channels=[],analyses=[],groups=[])
def validate_settings(data):
    if not isinstance(data,dict):raise UserError('Configuración no válida.')
    if not isinstance(data.get('sources'),list) or len(data['sources'])>30:raise UserError('Lista de fuentes inválida.')
    try:
        for s in data['sources']:
            for k in ('name','url','category','country'):assert isinstance(s[k],str)
            safe_url(s['url'])
        assert isinstance(data.get('ttl'),int) and 0<=data['ttl']<=1440
        assert isinstance(data.get('history'),bool)
        assert isinstance(data.get('queries'),list) and all(isinstance(q,str) for q in data['queries'])
        if 'recent' in data:assert isinstance(data['recent'],list) and all(isinstance(p,str) for p in data['recent'])
        if 'model' in data:assert isinstance(data['model'],str)
        if 'radar_weights' in data:assert isinstance(data['radar_weights'],dict) and all(isinstance(v,int) and 0<=v<=100 for v in data['radar_weights'].values())
    except (KeyError,TypeError,AssertionError):raise UserError('Configuración no válida.') from None
    return data
def export_csv(path,rows):
    fields=['title','url','source','category','country','published','retrieved','summary','origin','observed']
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for row in rows:
            values={k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else str(row.get(k,'')) for k in fields}
            w.writerow({k:"'"+v if v.lstrip().startswith(('=','+','-','@')) else v for k,v in values.items()})
def patterns(rows):
    stop=set('para como este esta sobre desde entre las los una unos del con que por the and de en el la un a y'.split())
    return Counter(w for r in rows for w in set(normalized(r['title']).split()) if len(w)>3 and w not in stop).most_common(12)
def report(project):
    esc=lambda x:html.escape(str(x))
    rows=project['items']; videos=[r for r in rows if 'viewCount' in r['observed']]
    videos.sort(key=lambda r:int(r['observed']['viewCount']) if str(r['observed']['viewCount']).isdigit() else 0,reverse=True)
    cards=''.join(f'<article><h3>{esc(r["title"])}</h3><p>{esc(r["summary"][:900])}</p><a href="{esc(safe_url(r["url"]))}">{esc(r["source"])}</a><p>Publicación: {esc(r["published"] or "Sin fecha")} · Consulta: {esc(r["retrieved"])} · Procedencia: {esc(r["origin"])}</p></article>' for r in rows)
    ideas=''.join(f'<article><h3>{esc(o["topic"])} · {o["score"]}/100</h3><p>{esc(o["notes"])} · {esc("; ".join(o["angles"]))}</p><p>{esc(o["contributions"])}</p>'+''.join(f'<p><a href="{esc(safe_url(s["url"]))}">{esc(s["name"])}</a> · {esc(s.get("retrieved",""))}</p>' for s in o['sources'])+'</article>' for o in project['opportunities'])
    top=''.join(f'<li>{esc(r["title"])}: {esc(r["observed"]["viewCount"])} vistas · {esc(r["observed"].get("channel","Sin canal"))} · {esc(r["origin"])}</li>' for r in videos[:10])
    from .research import channels
    comparison=channels(rows)
    analysis=''.join('<article><h3>IA local · '+esc(a['model'])+'</h3><p>'+esc(a['result']['resumen'])+'</p><pre style="white-space:pre-wrap">'+esc(json.dumps(a['result'],ensure_ascii=False,indent=2))+'</pre>'+''.join('<p>'+esc(key)+': <a href="'+esc(safe_url(s['url']))+'">'+esc(s['title'])+'</a> · '+esc(s['retrieved'])+'</p>' for key,s in a['sources'].items())+'</article>' for a in project.get('analyses',[]))
    return f'<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>TrendStudio · Informe</title><style>body{{background:#181c22;color:#e8edf4;font:16px system-ui;max-width:1000px;margin:40px auto;padding:20px}}article{{background:#252b34;padding:20px;margin:15px 0;border-radius:12px}}a{{color:#8bbcff}}</style><h1>TrendStudio · Investigación</h1><p>Generado: {esc(now())}</p><p>Noticias recientes no equivalen a tendencias demostradas. Las puntuaciones son valoraciones editoriales.</p><h2>Videos con más vistas en esta muestra</h2><ul>{top}</ul><p>Datos manuales requieren verificación. Suscriptores actuales, redondeados y audiencias externas limitan la comparación.</p><h2>Comparación por antigüedad y frecuencia</h2><pre style="white-space:pre-wrap">{esc(json.dumps(comparison,ensure_ascii=False,indent=2))}</pre><h2>Patrones en títulos</h2><p>{esc(patterns(rows))}</p><h2>Canales de referencia</h2><p>{esc(project["channels"])}</p><h2>Oportunidades y respaldo</h2>{ideas}<h2>Análisis local: borradores pendientes de revisión</h2>{analysis}<h2>Temas y fuentes</h2>{cards}</html>'
def creator_package(folder,project):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    atomic_json(folder/'creatorstudio.json',dict(schema='creatorstudio.opportunities.v1',exported=now(),opportunities=project['opportunities']))
    (folder/'LEEME.txt').write_text('Paquete de intercambio CreatorStudio v1. UTF-8. No envía datos ni ejecuta CreatorStudio.\nConsulte docs/INTERCAMBIO.md en el código fuente de TrendStudio.',encoding='utf-8')
