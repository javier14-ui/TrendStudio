"""Señales descriptivas y recopilación pública limitada, sin scraping evasivo."""
import json
from collections import defaultdict
from datetime import datetime,timezone
from urllib.parse import urlsplit,urlencode
from . import core

STATES=['Nueva','Interesante','Guardada','En investigación','Lista para guion','Descartada','Producida']
DEFAULT_WEIGHTS={'actualidad':50,'fuentes':25,'interes_observable':25}

def priority(row,weights=None):
    weights=weights or DEFAULT_WEIGHTS
    stamp=core.date(row['published']);age=(datetime.now(timezone.utc)-stamp).total_seconds()/86400 if stamp else None
    freshness=max(0,1-max(0,age)/7) if age is not None else 0
    domains={urlsplit(s['url']).hostname for s in row['sources']};count=len(domains)
    evidence=0;signals=[];missing=[]
    if row['origin']=='youtube_api' and str(row['observed'].get('viewCount','')).isdigit():
        signals.append(f"{row['observed']['viewCount']} vistas públicas observadas; no garantiza crecimiento.");evidence=.5
    elif row['origin']=='google_trends_csv' and row['observed'].get('samples'):
        signals.append('Serie relativa de Google Trends importada; no es volumen absoluto.');evidence=.5
    else:missing.append('Interés cuantitativo verificado no disponible.')
    if age is None:missing.append('Fecha de publicación desconocida.')
    signals.append(f'{count} dominio(s) citado(s); no acredita independencia editorial.')
    values=dict(actualidad=freshness,fuentes=min(count/3,1),interes_observable=evidence)
    total=sum(weights.values()) or 1;parts={k:round(values[k]*weights.get(k,0)/total*100,1) for k in values}
    return dict(score=round(sum(parts.values()),1),contributions=parts,signals=signals,missing=missing,weights=weights,warning='Prioridad de revisión heurística. No es probabilidad de viralidad ni medición de tendencia.')

def group_events(rows):
    groups=[];stop=set('para como este esta desde sobre entre las los del una que por con video nuevo nueva'.split())
    for row in rows[:500]:
        words={w for w in core.normalized(row['title']).split() if len(w)>2 and w not in stop}
        group=next((g for g in groups if len(words & g['_words'])>=3 and len(words & g['_words'])/max(1,len(words|g['_words']))>=.35),None)
        if group:group['item_ids'].append(row['id']);group['_words']|=words
        else:groups.append(dict(topic=row['title'],item_ids=[row['id']],_words=words))
    return [dict(topic=g['topic'],item_ids=g['item_ids'],method='Coincidencia de palabras en titulares; agrupación aproximada que requiere revisión.') for g in groups]

def today(http,sources,weights=None):
    data=core.radar(http,sources)
    for r in data['items']:r['priority']=priority(r,weights)
    data['items'].sort(key=lambda r:r['priority']['score'],reverse=True);data['groups']=group_events(data['items']);return data

def duration_seconds(value):
    import re
    m=re.fullmatch(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?',str(value))
    return sum(int(x or 0)*factor for x,factor in zip(m.groups(),[3600,60,1])) if m else None

def channels(rows):
    grouped=defaultdict(list);ranked=[]
    for row in rows:
        obs=row['observed'];channel=obs.get('channel') or obs.get('channelId')
        if channel:grouped[channel].append(row)
        stamp=core.date(row['published']);age=(datetime.now(timezone.utc)-stamp).total_seconds()/86400 if stamp else None
        views=int(obs['viewCount']) if str(obs.get('viewCount','')).isdigit() else None
        if views is not None:
            ranked.append(dict(id=row['id'],title=row['title'],url=row['url'],channel=channel or 'Sin canal',views=views,age_days=round(age,2) if age is not None else None,views_per_day=round(views/max(age,1),1) if age is not None and age>=0 else None,origin=row['origin'],retrieved=row['retrieved']))
    summary=[]
    for name,items in grouped.items():
        dates=sorted({d for r in items if (d:=core.date(r['published']))})
        gaps=[(b-a).total_seconds()/86400 for a,b in zip(dates,dates[1:])]
        durations=[d for r in items if (d:=duration_seconds(r['observed'].get('duration'))) is not None]
        summary.append(dict(channel=name,sample_size=len(items),first=dates[0].isoformat() if dates else '',last=dates[-1].isoformat() if dates else '',mean_gap_days=round(sum(gaps)/len(gaps),2) if gaps else None,mean_duration_seconds=round(sum(durations)/len(durations)) if durations else None,terms=core.patterns(items)))
    ranked.sort(key=lambda r:r['views_per_day'] if r['views_per_day'] is not None else -1,reverse=True)
    return dict(channels=summary,videos=ranked,warnings=['Muestra limitada: la frecuencia no representa necesariamente toda la actividad del canal.','Vistas/día = vistas acumuladas / máximo(edad en días, 1). No es velocidad reciente ni predicción.','Las cifras manuales no se verifican automáticamente. Los videos menores de un día usan divisor 1.'])

def youtube_feed(http,channel,days=30):
    import re
    channel=channel.strip().rstrip('/').split('/')[-1]
    if not re.fullmatch(r'UC[A-Za-z0-9_-]{22}',channel):raise core.UserError('Sin API usa el ID público UC… del canal (24 caracteres). Los @usuarios requieren la API opcional.')
    url='https://www.youtube.com/xml/feeds/videos.xml?'+urlencode({'channel_id':channel});raw,stamp=http.get(url)
    source=dict(name='YouTube',category='General',country='')
    rows=core.parse_feed(raw,source,stamp)
    parsed=core.feedparser.parse(raw)
    for row,entry in zip(rows,parsed.entries):
        row['origin']='youtube_rss';row['observed'].update(channelId=channel,channel=entry.get('author',channel))
    rows=core.filtered(rows,days=days)
    return dict(items=rows,errors=[] if rows else ['El RSS del canal no entregó videos para este periodo. Prueba Todo el periodo, la API opcional o la importación.'],requests=http.requests,hits=http.hits)

def public_metadata(http,url):
    url=core.safe_url(url);host=urlsplit(url).hostname.lower()
    if host in ('www.youtube.com','youtube.com','youtu.be','m.youtube.com'):
        endpoint='https://www.youtube.com/oembed?';name='YouTube'
    elif host in ('www.tiktok.com','tiktok.com'):
        endpoint='https://www.tiktok.com/oembed?';name='TikTok'
    else:raise core.UserError('Metadatos públicos disponibles para YouTube y TikTok. Para Instagram y otras fuentes, usa Añadir enlace o CSV.')
    raw,stamp=http.get(endpoint+urlencode(dict(url=url,format='json')))
    try:
        data=json.loads(raw)
        if not isinstance(data,dict) or not data.get('provider_name'):raise ValueError()
        title=data.get('title') or f'Publicación de {name} · título no disponible'
        row=core.item(title,url,name,origin='public_oembed',summary='Metadatos oficiales de oEmbed; no incluye métricas de rendimiento ni verificación del contenido.',observed={'channel':data.get('author_name',''),'metadata_only':True,'provider':data['provider_name']})
        row['retrieved']=stamp;row['sources'][0]['retrieved']=stamp
    except (ValueError,TypeError):raise core.UserError('La plataforma no entregó metadatos compatibles. Puedes importar el enlace manualmente.') from None
    return dict(items=[row],errors=[],requests=http.requests,hits=http.hits)

def script_package(folder,project):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    data=dict(schema='trendstudio.script-package.v1',created=core.now(),opportunities=project['opportunities'],analyses=project.get('analyses',[]),warnings=['Ideas de IA y valoraciones editoriales requieren revisión humana. No confundir propuestas con hechos.'])
    core.atomic_json(folder/'guion.json',data)
    (folder/'LEEME.txt').write_text('Paquete local para preparar guiones. No envía información a otra aplicación.\nEsquema: trendstudio.script-package.v1. Consulte docs/INTERCAMBIO.md.',encoding='utf-8')

from pathlib import Path
