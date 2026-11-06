import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import QTimer
from trendstudio.app import MainWindow, STYLE
from trendstudio import core
from trendstudio.app import OpportunityDialog

def test_ui_without_credentials(tmp_path):
    app=QApplication.instance() or QApplication([]);app.setStyleSheet(STYLE)
    window=MainWindow(tmp_path);window.resize(1024,680);window.show();app.processEvents()
    assert window.tabs.count()==6 and window.worker is None
    window.add_rows([core.item('Prueba de interfaz','https://example.com')]);assert window.results.rowCount()==1
    window.results.selectRow(0);app.processEvents();assert 'Prueba de interfaz' in window.details.toPlainText()
    window.query.setText('no coincide');window.refresh();assert window.results.rowCount()==0
    window.path=str(tmp_path/'project.json');assert window.save_project();assert core.read_json(window.path)['items']
    ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(1));timer.start(10)
    def slow(http):
        http.cancel.wait(.25)
        return dict(items=[],errors=[],requests=0,hits=0)
    window.start(slow)
    for _ in range(30):QTest.qWait(20)
    assert window.worker is None and len(ticks)>5
    window.dirty=False;window.close();timer.stop()

def test_opportunity_edit_and_export_roundtrip(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([]);window=MainWindow(tmp_path/'settings')
    r=core.item('Noticia para investigar','https://example.com',published=core.now());window.add_rows([r])
    def accept(dialog):
        dialog.notes.setPlainText('Contrastar con fuente primaria');dialog.angle.setPlainText('Explicar alcance');dialog.state.setCurrentText('En investigación')
        for widget in dialog.values.values():widget.setValue(2)
        return 1
    monkeypatch.setattr(OpportunityDialog,'exec',accept);window.evaluate(r);assert window.ideas.rowCount()==1
    o=window.project['opportunities'][0];assert o['status']=='En investigación' and o['score']==40
    original=o['id'];window.evaluate(r,o);assert window.project['opportunities'][0]['id']==original
    window.path=str(tmp_path/'project.json');assert window.save_project()
    reopened=core.validate_project(core.read_json(window.path));assert reopened['opportunities'][0]['notes']=='Contrastar con fuente primaria'
    assert window.recent.count()==2
    window.dirty=False;window.close();app.processEvents()
