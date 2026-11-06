"""Prueba real, opt-in: consulta una vez cada fuente; no requiere API key."""
import json
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from trendstudio import core

results=[]
with tempfile.TemporaryDirectory() as folder:
    http=core.Http(folder,ttl=0)
    for source in core.DEFAULT_SOURCES:
        start=time.monotonic()
        try:
            raw,stamp=http.get(source['url']);items=core.parse_feed(raw,source,stamp)
            results.append(dict(source=source['name'],url=source['url'],ok=True,count=len(items),retrieved=stamp,seconds=round(time.monotonic()-start,2)))
        except core.UserError as e:results.append(dict(source=source['name'],url=source['url'],ok=False,error=str(e),seconds=round(time.monotonic()-start,2)))
print(json.dumps(results,ensure_ascii=False,indent=2))
