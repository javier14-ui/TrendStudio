"""Autoprueba explícita de la distribución; no se ejecuta en el uso normal."""
import sys
import tempfile
import time
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer,qVersion
from . import core,research,secrets,intelligence
from .app import MainWindow,STYLE

def main():
    index=sys.argv.index('--verify-install');out=Path(sys.argv[index+1]);report={'frozen':bool(getattr(sys,'frozen',False)),'qt':qVersion(),'tests':{},'date':core.now()}
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE)
    with tempfile.TemporaryDirectory() as temp:
        home=Path(temp);start=time.monotonic();window=MainWindow(home);window.show();report['window_seconds']=round(time.monotonic()-start,3)
        rows=[core.item('Verificación local de TrendStudio','https://example.com',summary='Dato de prueba controlado, no noticia real.')]
        try:
            if '--live' in sys.argv:
                data=research.today(core.Http(home/'http',ttl=0),core.DEFAULT_SOURCES);rows=data['items'];report['tests']['live_rss']={'count':len(rows),'errors':data['errors']}
            project=core.new_project();project['items']=rows;core.atomic_json(home/'p.json',project);assert core.validate_project(core.read_json(home/'p.json'))==project
            core.export_csv(home/'p.csv',rows);(home/'report.html').write_text(core.report(project),encoding='utf-8');research.script_package(home/'script',project)
            secrets.save(home/'test.dpapi','verification-only');assert secrets.load(home/'test.dpapi')=='verification-only'
            window.project=project;window.refresh();window.results.selectRow(0)
            window.status.setText(f'Autoprueba: {len(rows)} registros consultados; guardado y exportaciones comprobados.')
            if '--ollama' in sys.argv:
                ai_start=time.monotonic();client=intelligence.Ollama(home/'ai');analysis=client.analyze(rows[:1]);project['analyses']=[analysis]
                report['tests']['ollama']={'model':analysis['model'],'seconds':round(time.monotonic()-ai_start,2),'titles':len(analysis['result']['titulos']),'hooks':len(analysis['result']['ganchos']),'warnings':len(analysis.get('quality_notes',[]))}
                window.refresh();window.results.selectRow(0)
            report['tests'].update(json_roundtrip=True,csv=True,html=True,script_package=True,dpapi=True,qt_window=True)
        except Exception as e:report['error']=type(e).__name__+': '+str(e)
        def finish():
            if '--screenshots' in sys.argv:
                folder=Path(sys.argv[sys.argv.index('--screenshots')+1]);folder.mkdir(parents=True,exist_ok=True)
                window.grab().save(str(folder/'radar.png'));window.tabs.setCurrentIndex(4);app.processEvents();window.grab().save(str(folder/'configuracion.png'))
                if window.project.get('analyses'):
                    window.tabs.setCurrentIndex(5);window.analysis_list.setCurrentRow(0);app.processEvents();window.grab().save(str(folder/'ia-local.png'))
            report['elapsed_seconds']=round(time.monotonic()-start,3);core.atomic_json(out,report);window.dirty=False;window.close();app.quit()
        QTimer.singleShot(700,finish);app.exec()
    return 1 if 'error' in report else 0
