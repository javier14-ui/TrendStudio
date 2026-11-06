import csv
import io
import json
import threading
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone
import pytest
from trendstudio import core, secrets

RSS=b'''<?xml version="1.0"?><rss version="2.0"><channel><title>Test</title><item><title>Nuevo anuncio de un videojuego muy esperado</title><link>https://example.com/a</link><pubDate>Wed, 04 Nov 2026 12:00:00 GMT</pubDate><description>Texto de la fuente</description></item></channel></rss>'''
SOURCE=dict(name='Test',url='https://example.com/feed',category='Videojuegos',country='PE')
def sample():return core.item('Nuevo anuncio de un videojuego muy esperado','https://example.com/a',published=core.now())

def test_feed_dates_and_origin():
    r=core.parse_feed(RSS,SOURCE,'2026-11-04T14:00:00+00:00')[0]
    assert r['origin']=='rss' and r['category']=='Videojuegos' and r['country']=='PE'
    assert r['published']=='2026-11-04T12:00:00+00:00' and r['retrieved']==r['sources'][0]['retrieved']
def test_atom():
    raw=b'<feed xmlns="http://www.w3.org/2005/Atom"><title>A</title><entry><title>Atom</title><link href="https://example.com/atom"/><updated>2026-11-04T00:00:00Z</updated></entry></feed>'
    assert core.parse_feed(raw,SOURCE,core.now())[0]['title']=='Atom'
@pytest.mark.parametrize('raw',[b'not XML', b'<html>no feed</html>',b'<!DOCTYPE x [<!ENTITY a "foo">]><rss>&a;</rss>'])
def test_invalid_feed(raw):
    with pytest.raises(core.UserError):core.parse_feed(raw,SOURCE,core.now())
def test_dedup_sources_and_tracking():
    a=sample();b=core.item(a['title']+'!','https://example.org/other','Other');c=core.item('Otro título','https://example.com/a?utm_source=test')
    result=core.dedupe([a,b,c]);assert len(result)==1 and len(result[0]['sources'])==3
def test_filter_and_missing_date():
    r=sample();r['category']='Tecnología';r['country']='PE'
    assert core.filtered([r],'anuncio','Tecnología','PE',7)==[r]
    assert not core.filtered([r],'inexistente')
    r['published']='';assert not core.filtered([r],days=7)
def test_timezone():assert core.date('2026-11-04T10:00:00-05:00').utcoffset().total_seconds()==-18000
def test_save_open_and_contract(tmp_path):
    p=core.new_project();p['items']=[sample()];ratings={c:3 for c in core.CRITERIA};weights={c:1 for c in core.CRITERIA}
    p['opportunities']=[core.opportunity(p['items'][0],ratings,weights,notes='nota',angle='enfoque')]
    path=tmp_path/'research.json';core.atomic_json(path,p);assert core.validate_project(core.read_json(path))==p
    core.creator_package(tmp_path/'package',p);d=core.read_json(tmp_path/'package/creatorstudio.json');assert d['schema']=='creatorstudio.opportunities.v1'
    assert {'id','topic','category','summary','sources','published','retrieved','observed','notes','angles','warnings'}.issubset(d['opportunities'][0])
    assert 'key' not in json.dumps(d)
def test_invalid_project():
    with pytest.raises(core.UserError):core.validate_project({'schema':'other'})
    p=core.new_project();p['items']=[{}]
    with pytest.raises(core.UserError):core.validate_project(p)
def test_csv_and_html_safety(tmp_path):
    r=sample();r['title']='=HYPERLINK("bad")';r['summary']='<script>alert(1)</script>'
    path=tmp_path/'export.csv';core.export_csv(path,[r]);assert list(csv.DictReader(path.open(encoding='utf-8-sig')))[0]['title'].startswith("'=")
    p=core.new_project();p['items']=[r];out=core.report(p);assert '<script>' not in out and '&lt;script&gt;' in out
def test_manual_csv(tmp_path):
    p=tmp_path/'in.csv';p.write_text('title,url,source,viewCount\nEjemplo,https://example.com,TikTok,250\n',encoding='utf-8')
    r=core.import_csv(p)[0];assert r['origin']=='manual_csv' and r['observed']['viewCount']=='250'
    p.write_text('title,url\nBad,javascript:alert(1)',encoding='utf-8')
    with pytest.raises(core.UserError):core.import_csv(p)
def test_trends(tmp_path):
    p=tmp_path/'trends.csv';p.write_text('Categoría: Todas\n\nSemana,GTA VI: (Perú)\n2026-10-01,50\n2026-10-08,<1\n',encoding='utf-8')
    r=core.import_trends(p,'GTA VI','https://trends.google.com/trends/','PE')[0]
    assert r['observed']['samples'][1]['index']=='<1' and r['origin']=='google_trends_csv'
def test_score_explained():
    ratings={c:5 for c in core.CRITERIA};weights={c:1 for c in core.CRITERIA}
    value,parts=core.score(ratings,weights);assert value==100 and abs(sum(parts.values())-100)<.1
    with pytest.raises(core.UserError):core.score(ratings,{c:0 for c in core.CRITERIA})
    ratings[core.CRITERIA[0]]=float('nan')
    with pytest.raises(core.UserError):core.score(ratings,weights)
def test_settings_validation():
    data=dict(sources=core.DEFAULT_SOURCES,ttl=30,history=False,queries=['GTA VI'])
    assert core.validate_settings(data)==data
    data['ttl']='broken'
    with pytest.raises(core.UserError):core.validate_settings(data)
def test_dpapi(tmp_path):
    p=tmp_path/'secret';secrets.save(p,'not-a-real-key');assert b'not-a-real-key' not in p.read_bytes();assert secrets.load(p)=='not-a-real-key';secrets.save(p,'');assert secrets.load(p)==''
def test_cache_and_cancel(tmp_path,monkeypatch):
    class Response(io.BytesIO):pass
    monkeypatch.setattr(core,'urlopen',lambda *a,**k:Response(RSS))
    h=core.Http(tmp_path);raw,stamp=h.get(SOURCE['url']);raw2,stamp2=h.get(SOURCE['url']);assert raw==raw2 and stamp==stamp2 and h.requests==1 and h.hits==1
    h.cancel.set()
    with pytest.raises(core.Cancelled):h.get(SOURCE['url'])
@pytest.mark.parametrize('code,body,expected',[(429,b'', 'límite'),(403,b'{"reason":"quotaExceeded"}','límite'),(403,b'','denegado'),(404,b'','disponible')])
def test_http_errors(tmp_path,monkeypatch,code,body,expected):
    def fail(*a,**k):raise HTTPError('https://example.com',code,'bad',{},io.BytesIO(body))
    monkeypatch.setattr(core,'urlopen',fail)
    with pytest.raises(core.UserError,match=expected):core.Http(tmp_path).get(SOURCE['url'])
def test_offline_partial(tmp_path,monkeypatch):
    def fail(*a,**k):raise URLError('offline')
    monkeypatch.setattr(core,'urlopen',fail);result=core.radar(core.Http(tmp_path),[SOURCE]);assert not result['items'] and len(result['errors'])==1
def test_no_key(tmp_path):
    with pytest.raises(core.UserError,match='clave'):core.YouTube(core.Http(tmp_path),'').search('test')
def test_youtube_controlled_response(tmp_path):
    class Fake:
        requests=0;hits=0
        def get(self,url,**kw):
            self.requests+=1
            if '/search?' in url:d={'items':[{'id':{'videoId':'abc'}}]}
            elif '/videos?' in url:d={'items':[dict(id='abc',snippet=dict(title='Video',channelId='UC1',channelTitle='Canal',publishedAt=core.now()),statistics=dict(viewCount='123'),contentDetails=dict(duration='PT3M'))]}
            else:d={'items':[dict(id='UC1',statistics=dict(hiddenSubscriberCount=True))]}
            return json.dumps(d).encode(),core.now()
    result=core.YouTube(Fake(),'FAKE').search('demo');assert result['items'][0]['observed']['viewCount']=='123';assert 'subscriberCount' not in result['items'][0]['observed']
