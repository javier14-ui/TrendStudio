import copy
import json
import socket
import threading
import time
from datetime import datetime,timezone,timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from trendstudio import core,research,intelligence

def result():
    return dict(resumen='Una nueva misión espacial',categoria='Tecnología',afirmaciones=[dict(texto='La agencia anunció una misión',cita='La agencia anunció una misión',tipo='hecho reportado',fuentes=['fuente_1'])],grupos=[dict(tema='Misión espacial',fuentes=['fuente_1'])],contradicciones=[],titulos=['Nueva misión espacial: claves','La misión explicada','¿Qué cambia con la misión?'],ganchos=['Revisemos el anuncio de hoy.','Esto es lo que cuenta la fuente.','El siguiente paso merece atención.'],enfoques=['Comparar el anuncio con publicaciones anteriores.'],verificar=['Confirmar la fecha con la agencia.'],patrones=[])
def row():return core.item('La agencia anunció una misión','https://example.com/noticia',category='Tecnología',summary='La agencia anunció una misión espacial.',published=core.now())

def test_ai_reference_validation():
    d=result();assert intelligence.validate(d,['fuente_1'])==d
    d['afirmaciones'][0]['fuentes']=['fuente_inventada']
    with pytest.raises(core.UserError):intelligence.validate(d,['fuente_1'])
def test_ai_review_discards_unsupported_numbers_quotes_and_repetition():
    d=result();d['afirmaciones'][0]['cita']='Cita inventada que no existe';d['titulos'][0]='La misión costará 900000';d['ganchos']=['igual']*3;d['categoria']='Actualidad del Perú'
    doc=dict(id='fuente_1',title=row()['title'],summary=row()['summary'],observed={},category='Tecnología')
    cleaned,issues,origins=intelligence.review(d,[doc]);assert cleaned['categoria']=='Tecnología'
    assert origins['titulos']=='plantilla_editorial_no_IA' and origins['ganchos']=='plantilla_editorial_no_IA'
    assert cleaned['afirmaciones'][0]['texto']==doc['title'] and len(issues)>=3
    assert '900000' not in json.dumps(cleaned)
def test_ai_keeps_literal_evidence():
    doc=dict(id='fuente_1',title=row()['title'],summary=row()['summary'],observed={},category='Tecnología')
    cleaned,_,_=intelligence.review(result(),[doc]);assert cleaned['afirmaciones'][0]['cita'] in doc['title']
def test_ai_missing_model_no_download(tmp_path,monkeypatch):
    ai=intelligence.Ollama(tmp_path);monkeypatch.setattr(ai,'models',lambda:[])
    with pytest.raises(core.UserError,match='no está instalado'):ai.analyze([row()])
def test_ai_single_task_lock(tmp_path):
    intelligence.LOCK.acquire()
    try:
        with pytest.raises(core.UserError,match='curso'):intelligence.Ollama(tmp_path).analyze([row()])
    finally:intelligence.LOCK.release()
def test_ai_two_stage_cache_and_project_roundtrip(tmp_path,monkeypatch):
    ai=intelligence.Ollama(tmp_path/'cache');monkeypatch.setattr(ai,'models',lambda:[{'name':'test','digest':'x'}]);calls=[]
    def stream(payload):calls.append(payload);return json.dumps({k:result()[k] for k in payload['format']['required']})
    monkeypatch.setattr(ai,'stream',stream);r=row();a=ai.analyze([r],'test');assert len(calls)==2
    r2=copy.deepcopy(r);r2['id']='new-id';cached=ai.analyze([r2],'test');assert cached['cached'] and len(calls)==2 and cached['input_ids']==['new-id']
    p=core.new_project();p['items']=[r];p['analyses']=[a];core.atomic_json(tmp_path/'p.json',p);assert core.validate_project(core.read_json(tmp_path/'p.json'))==p
    research.script_package(tmp_path/'guion',p);assert core.read_json(tmp_path/'guion/guion.json')['analyses'][0]['sources']['fuente_1']['url']==r['url']
    assert 'IA local' in core.report(p)
def test_ollama_offline(tmp_path):
    with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    with pytest.raises(core.UserError,match='no está disponible'):intelligence.Ollama(tmp_path,port=port).models()
def test_cancel_interrupts_local_http(tmp_path):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']));time.sleep(1.5)
            try:self.send_response(200);self.end_headers();self.wfile.write(b'{"done":true}\n')
            except OSError:pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    cancel=threading.Event();ai=intelligence.Ollama(tmp_path,cancel,port=server.server_port);timer=threading.Timer(.15,cancel.set);timer.start();start=time.monotonic()
    try:
        with pytest.raises(core.Cancelled):ai.stream({'model':'test'})
        assert time.monotonic()-start<1.2
    finally:timer.cancel();server.shutdown();server.server_close();thread.join()
def test_priority_is_explainable_no_fabricated_interest():
    p=research.priority(row());assert p['missing'] and 0<=p['score']<=100
    assert sum(p['contributions'].values())==pytest.approx(p['score'],abs=.11)
def test_channel_age_duration_frequency():
    a=row();b=row();a['published']=(datetime.now(timezone.utc)-timedelta(days=10)).isoformat();b['published']=(datetime.now(timezone.utc)-timedelta(days=5)).isoformat()
    a['observed']=dict(channel='Canal',viewCount='1000',duration='PT2M');b['observed']=dict(channel='Canal',viewCount='1000',duration='PT4M')
    d=research.channels([a,b]);assert d['videos'][0]['id']==b['id'];assert d['channels'][0]['mean_gap_days']==5 and d['channels'][0]['mean_duration_seconds']==180
def test_grouping_does_not_discard_originals():
    rows=[row(),core.item('La agencia anunció una misión espacial nueva','https://other.com')]
    groups=research.group_events(rows);assert len(groups)==1 and len(groups[0]['item_ids'])==2 and len(rows)==2
def test_oembed_no_html_execution(tmp_path):
    class Fake:
        requests=1;hits=0
        def get(self,url):return json.dumps(dict(provider_name='TikTok',html='<script>bad()</script>')).encode(),core.now()
    d=research.public_metadata(Fake(),'https://www.tiktok.com/@example/video/123');assert d['items'][0]['origin']=='public_oembed'
    assert '<script>' not in json.dumps(d)
    with pytest.raises(core.UserError):research.public_metadata(Fake(),'https://instagram.com/example')
def test_youtube_rss_invalid_channel_no_request(tmp_path):
    h=core.Http(tmp_path)
    with pytest.raises(core.UserError):research.youtube_feed(h,'@usuario')
    assert h.requests==0
