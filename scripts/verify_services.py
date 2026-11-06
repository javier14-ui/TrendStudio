"""Pruebas reales opcionales. Nunca descarga modelos ni usa credenciales."""
import argparse
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trendstudio import core,research,intelligence

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--ollama',action='store_true');parser.add_argument('--out',required=True);args=parser.parse_args()
    records=[]
    with tempfile.TemporaryDirectory() as folder:
        http=core.Http(Path(folder)/'http',ttl=30)
        tests=[('RSS y radar',lambda:research.today(http,core.DEFAULT_SOURCES)),
          ('YouTube RSS público',lambda:research.youtube_feed(http,'UC_x5XG1OV2P6uZZ5FSM9Ttw',0)),
          ('YouTube oEmbed',lambda:research.public_metadata(http,'https://www.youtube.com/watch?v=jNQXAC9IVRw')),
          ('TikTok oEmbed',lambda:research.public_metadata(http,'https://www.tiktok.com/@scout2015/video/6718335390845095173'))]
        rows=[]
        for name,fn in tests:
            start=time.monotonic()
            try:
                d=fn();records.append(dict(test=name,ok=True,count=len(d['items']),errors=d['errors'],seconds=round(time.monotonic()-start,2)))
                if name=='RSS y radar':rows=d['items']
            except core.UserError as e:records.append(dict(test=name,ok=False,message=str(e)))
        if args.ollama:
            client=intelligence.Ollama(Path(folder)/'ai');start=time.monotonic()
            try:
                models=client.models();records.append(dict(test='Modelos Ollama',ok=True,models=[dict(name=m['name'],size=m['size']) for m in models]))
                selected=next((r for r in rows if r['country']=='PE'),rows[0] if rows else None)
                a=client.analyze([selected]);records.append(dict(test='Generación Ollama real',ok=True,seconds=round(time.monotonic()-start,2),model=a['model'],titles=a['result']['titulos'],quality_notes=a['quality_notes'],field_provenance=a['field_provenance']))
                start=time.monotonic();cached=client.analyze([selected]);records.append(dict(test='Caché IA real',ok=cached['cached'],seconds=round(time.monotonic()-start,3)))
                cancel=threading.Event();timer=threading.Timer(.3,cancel.set);timer.start();start=time.monotonic()
                try:
                    intelligence.Ollama(Path(folder)/'ai',cancel).analyze([selected],use_cache=False);records.append(dict(test='Cancelación Ollama real',ok=False))
                except core.Cancelled:records.append(dict(test='Cancelación Ollama real',ok=True,seconds=round(time.monotonic()-start,3)))
                finally:timer.cancel()
            except core.UserError as e:records.append(dict(test='Ollama',ok=False,message=str(e)))
    core.atomic_json(args.out,dict(created=core.now(),results=records));print(json.dumps(records,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
