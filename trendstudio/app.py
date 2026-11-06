from __future__ import annotations
import json
import os
import sys
import threading
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtGui import QDesktopServices, QCloseEvent
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QComboBox,QTabWidget,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QTextBrowser,QSplitter,QFileDialog,QMessageBox,QDialog,QFormLayout,QDialogButtonBox,QSpinBox,QCheckBox,QPlainTextEdit,QListWidget)
from . import core, secrets, research, intelligence

STYLE='''
QWidget { background:#191d24; color:#e7edf5; font-family:"Segoe UI"; font-size:13px; }
QMainWindow,QDialog { background:#191d24; } QLabel#brand {font-size:28px;font-weight:700;color:#a8c9ff;}
QPushButton {background:#304b6f;border:1px solid #46638b;border-radius:6px;padding:8px 12px;}
QPushButton:hover {background:#3d608c;} QPushButton:disabled {color:#788390;background:#252b34;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTextBrowser,QListWidget {background:#242b35;border:1px solid #414c5b;border-radius:5px;padding:6px;}
QTableWidget {background:#202630;alternate-background-color:#262e39;border:0;gridline-color:#303845;}
QHeaderView::section {background:#2d3745;color:#b8cce6;padding:8px;border:0;}
QTabWidget::pane {border:1px solid #343f4d;} QTabBar::tab {padding:12px;background:#222a34;}
QTabBar::tab:selected {background:#354c69;color:#b9d6ff;} QTableWidget::item:selected {background:#355578;}
QToolTip {background:#344357;color:white;} QScrollBar {background:#242b35;}
'''

def button(text,fn,layout):
    b=QPushButton(text); b.clicked.connect(fn); layout.addWidget(b); return b
def combo(values):
    c=QComboBox(); c.addItems(values); return c
def table(headers):
    t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.setSelectionMode(QAbstractItemView.SingleSelection); t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setAlternatingRowColors(True); t.verticalHeader().hide(); t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    t.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch); return t
def fill(t,rows):
    t.setSortingEnabled(False); t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,value in enumerate(row): t.setItem(i,j,QTableWidgetItem(str(value)))

class Worker(QThread):
    done=Signal(object); failed=Signal(str); progress=Signal(str)
    def __init__(self,fn,cancel): super().__init__(); self.fn=fn; self.cancel=cancel
    def run(self):
        try: self.done.emit(self.fn())
        except core.UserError as e: self.failed.emit(str(e))
        except Exception: self.failed.emit('La fuente devolvió datos inesperados. Prueba otra fuente o revisa su formato.')

class EntryDialog(QDialog):
    def __init__(self,parent,title,fields):
        super().__init__(parent); self.setWindowTitle(title); self.resize(540,340); self.fields={}; form=QFormLayout(self)
        for name,initial in fields.items():
            widget=QPlainTextEdit(initial) if name in ('Resumen','Notas','Enfoque') else QLineEdit(initial)
            if isinstance(widget,QPlainTextEdit): widget.setMaximumHeight(90)
            self.fields[name]=widget; form.addRow(name,widget)
        box=QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel); box.accepted.connect(self.accept); box.rejected.connect(self.reject); form.addRow(box)
    def values(self): return {k:(w.toPlainText() if isinstance(w,QPlainTextEdit) else w.text()).strip() for k,w in self.fields.items()}

class OpportunityDialog(QDialog):
    def __init__(self,parent,row,existing=None):
        super().__init__(parent); self.setWindowTitle('Evaluar oportunidad'); self.resize(650,650); layout=QVBoxLayout(self)
        title=QLabel(row['title']); title.setWordWrap(True); layout.addWidget(title)
        note=QLabel('Valoración editorial de 0 a 5. 0 = sin evidencia o desfavorable.\nLos pesos definen la importancia; facilidad y baja competencia puntúan a favor.'); note.setWordWrap(True); layout.addWidget(note)
        missing=QLabel('Datos faltantes: '+ ' '.join(research.priority(row)['missing'])+' Competencia y dificultad requieren tu evaluación.');missing.setWordWrap(True);layout.addWidget(missing)
        self.values={}; self.weights={}; form=QFormLayout(); layout.addLayout(form)
        for c in core.CRITERIA:
            line=QHBoxLayout(); v=QSpinBox();v.setRange(0,5);w=QSpinBox();w.setRange(0,10)
            v.setValue(existing['ratings'].get(c,0) if existing else 0);w.setValue(existing['weights'].get(c,1) if existing else 1)
            line.addWidget(v);line.addWidget(QLabel('Peso'));line.addWidget(w);form.addRow(c,line);self.values[c]=v;self.weights[c]=w
        self.state=combo(research.STATES);self.notes=QPlainTextEdit();self.angle=QPlainTextEdit()
        self.notes.setMaximumHeight(70);self.angle.setMaximumHeight(70)
        if existing: self.state.setCurrentText(existing['status']);self.notes.setPlainText(existing['notes']);self.angle.setPlainText('\n'.join(existing['angles']))
        form.addRow('Estado',self.state);form.addRow('Notas y justificación',self.notes);form.addRow('Enfoque original',self.angle)
        self.preview=QLabel();layout.addWidget(self.preview)
        for w in [*self.values.values(),*self.weights.values()]: w.valueChanged.connect(self.update_score)
        self.update_score();box=QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel);box.accepted.connect(self.commit);box.rejected.connect(self.reject);layout.addWidget(box)
    def update_score(self):
        try:
            s,_=core.score({k:v.value() for k,v in self.values.items()},{k:v.value() for k,v in self.weights.items()});self.preview.setText(f'Estimación editorial: {s}/100 · No predice viralidad')
        except core.UserError as e:self.preview.setText(str(e))
    def commit(self):
        if not sum(w.value() for w in self.weights.values()): return
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self,data_dir=None):
        super().__init__(); self.setWindowTitle('TrendStudio · Radar de contenido'); self.resize(1120,740); self.setMinimumSize(850,580)
        self.home=Path(data_dir or Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'TrendStudio');self.home.mkdir(parents=True,exist_ok=True)
        self.settings=dict(sources=core.DEFAULT_SOURCES,ttl=30,history=False,queries=[]);self.project=core.new_project();self.path=None;self.dirty=False;self.worker=None;self.closing=False
        try:
            if (self.home/'settings.json').exists():
                settings=core.validate_settings(core.read_json(self.home/'settings.json'))
                self.settings.update(settings)
        except (ValueError,OSError,core.UserError): pass
        base=QWidget();self.setCentralWidget(base);main=QVBoxLayout(base);main.setContentsMargins(20,16,20,12)
        head=QHBoxLayout();brand=QLabel('TrendStudio');brand.setObjectName('brand');head.addWidget(brand);head.addStretch()
        button('Abrir',self.open_project,head);button('Guardar investigación',self.save_project,head);button('Nueva',self.new_project,head);main.addLayout(head)
        main.addWidget(QLabel('Investiga con fuentes. Decide con criterio.'))
        self.tabs=QTabWidget();main.addWidget(self.tabs)
        self.make_radar();self.make_youtube();self.make_opportunities();self.make_exports();self.make_settings();self.make_ai()
        bottom=QHBoxLayout();self.status=QLabel('Listo. No se realizan conexiones hasta que inicies una consulta.');self.status.setWordWrap(True);bottom.addWidget(self.status,1)
        self.cancel=button('Cancelar búsqueda',self.cancel_search,bottom);self.cancel.setEnabled(False);main.addLayout(bottom)
        self.refresh()
    def error(self,message): QMessageBox.warning(self,'TrendStudio',str(message))
    def guarded(self,fn):
        try:return fn()
        except (core.UserError,OSError,ValueError,TypeError,KeyError) as e:self.error(str(e) if isinstance(e,core.UserError) else 'No se pudo leer o escribir el archivo. Revisa su formato y los permisos de la carpeta.')
    def make_radar(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Radar')
        row=QHBoxLayout();self.query=QLineEdit();self.query.setPlaceholderText('Tema o palabras clave: GTA VI, tecnología, Perú…');self.query.setMinimumHeight(38);row.addWidget(self.query,1)
        self.search_button=button('Buscar tendencias',self.search_radar,row);layout.addLayout(row)
        todayrow=QHBoxLayout();self.today_button=button('Buscar oportunidades de hoy',self.search_today,todayrow);todayrow.addWidget(QLabel('Últimas 24 horas · prioridad explicable · sin IA obligatoria'),1);layout.addLayout(todayrow)
        filters=QHBoxLayout();self.category=combo(['Todas las categorías']+core.CATEGORIES);self.country=QLineEdit();self.country.setPlaceholderText('País: PE, US…');self.country.setMaximumWidth(130)
        self.period=combo(['Todo el periodo','Últimas 24 horas','Últimos 7 días','Últimos 30 días','Últimos 90 días']);self.favorite=QCheckBox('Solo favoritas')
        filters.addWidget(self.category);filters.addWidget(self.country);filters.addWidget(self.period);filters.addWidget(self.favorite);button('Aplicar filtros',self.refresh,filters);layout.addLayout(filters)
        saved=QHBoxLayout();self.saved=combo(['Consultas guardadas']+self.settings.get('queries',[]));saved.addWidget(self.saved,1);button('Usar consulta',lambda:self.query.setText(self.saved.currentText() if self.saved.currentIndex()>0 else ''),saved);button('Guardar consulta',self.save_query,saved);layout.addLayout(saved)
        split=QSplitter(Qt.Vertical);self.results=table(['Tema','Fuente','Publicado','Prioridad']);split.addWidget(self.results);self.details=QTextBrowser();self.details.setOpenExternalLinks(False);self.details.anchorClicked.connect(lambda u:QDesktopServices.openUrl(u) if u.scheme() in ('http','https') else None);split.addWidget(self.details);split.setSizes([300,160]);layout.addWidget(split)
        self.results.itemSelectionChanged.connect(self.show_details)
        actions=QHBoxLayout();button('Abrir fuente',self.open_source,actions);button('Crear oportunidad',self.create_opportunity,actions);button('Añadir enlace',self.manual,actions);button('Importar CSV',self.import_csv,actions);button('Importar Trends',self.import_trends,actions);layout.addLayout(actions)
    def make_youtube(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'YouTube y canales')
        label=QLabel('YouTube: API opcional o RSS público por ID de canal UC… sin clave.\nMetadatos públicos de YouTube/TikTok cuando estén disponibles. Instagram: importación manual.');label.setWordWrap(True);layout.addWidget(label)
        row=QHBoxLayout();self.yquery=QLineEdit();self.yquery.setPlaceholderText('Buscar videos por tema');self.channel=QLineEdit();self.channel.setPlaceholderText('Canal opcional: @usuario o UC…');row.addWidget(self.yquery);row.addWidget(self.channel);layout.addLayout(row)
        row=QHBoxLayout();self.yperiod=combo(['Últimos 7 días','Últimos 30 días','Últimos 90 días','Todo el periodo']);row.addWidget(self.yperiod);self.ysearch=button('Consultar YouTube',self.search_youtube,row);button('Guardar canal',self.save_channel,row);layout.addLayout(row)
        row=QHBoxLayout();button('RSS del canal (sin clave)',self.search_channel_rss,row);button('Obtener metadatos de enlace',self.fetch_metadata,row);button('Comparar canales y antigüedad',self.compare_channels,row);layout.addLayout(row)
        self.videos=table(['Título','Canal','Vistas','Duración','Publicado']);layout.addWidget(self.videos)
        self.video_detail=QTextBrowser();self.video_detail.setMaximumHeight(150);layout.addWidget(self.video_detail);self.videos.itemSelectionChanged.connect(self.show_video)
        self.channel_list=QListWidget();self.channel_list.setMaximumHeight(90);self.channel_list.itemClicked.connect(lambda i:self.channel.setText(i.text()));layout.addWidget(self.channel_list)
        button('Quitar canal seleccionado',self.remove_channel,layout)
        label=QLabel('Máximo 25 videos por consulta, sin paginación automática. La cuota depende de tu proyecto.\nLas vistas no revelan CTR, retención ni ingresos. Vistas/suscriptores es una comparación descriptiva limitada.');label.setWordWrap(True);layout.addWidget(label)
    def make_opportunities(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Oportunidades');self.ideas=table(['Tema','Estado','Puntuación']);layout.addWidget(self.ideas)
        self.idea_details=QTextBrowser();layout.addWidget(self.idea_details);self.ideas.itemSelectionChanged.connect(self.show_idea)
        row=QHBoxLayout();button('Editar evaluación y notas',self.edit_opportunity,row);button('Eliminar',self.delete_opportunity,row);layout.addLayout(row)
    def make_exports(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Informes')
        label=QLabel('Exporta la investigación completa, incluidos los resultados fuera del filtro actual.\nLos archivos contienen fuentes y fechas; nunca incluyen la clave API.');label.setWordWrap(True);layout.addWidget(label)
        for title,kind in [('Exportar JSON','json'),('Exportar CSV','csv'),('Crear informe HTML local','html'),('Preparar para guion','script'),('Enviar a CreatorStudio (crear paquete)','creator')]:button(title,lambda checked=False,k=kind:self.export(k),layout)
        self.recent=combo(['Investigaciones guardadas']+self.settings.get('recent',[]));layout.addWidget(self.recent);button('Reabrir investigación seleccionada',self.open_recent,layout)
        self.pattern_label=QLabel();self.pattern_label.setWordWrap(True);layout.addWidget(self.pattern_label);layout.addStretch()
    def make_settings(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'Configuración avanzada')
        layout.addWidget(QLabel('Fuentes RSS / Atom · máximo 30 · selecciona y marca favoritas'))
        self.sources=table(['Fuente','Categoría','País','Favorita']);layout.addWidget(self.sources)
        row=QHBoxLayout();button('Añadir fuente',self.add_source,row);button('Quitar fuente',self.remove_source,row);button('Alternar favorita',self.toggle_favorite,row);layout.addLayout(row)
        form=QFormLayout();self.ttl=QSpinBox();self.ttl.setRange(0,1440);self.ttl.setValue(int(self.settings['ttl']));form.addRow('Caché (minutos; 0 desactiva)',self.ttl)
        self.history=QCheckBox('Guardar historial de consultas localmente (opcional)');self.history.setChecked(bool(self.settings['history']));form.addRow(self.history)
        self.radar_weights={};line=QHBoxLayout()
        for key,label in [('actualidad','Actualidad'),('fuentes','Fuentes'),('interes_observable','Interés')]:
            spin=QSpinBox();spin.setRange(0,100);spin.setValue(self.settings.get('radar_weights',research.DEFAULT_WEIGHTS).get(key,0));self.radar_weights[key]=spin;line.addWidget(QLabel(label));line.addWidget(spin)
        form.addRow('Pesos del radar',line)
        self.key=QLineEdit();self.key.setEchoMode(QLineEdit.Password);self.key.setPlaceholderText('Nueva clave API; vacío conserva la existente');form.addRow('Clave de YouTube',self.key);layout.addLayout(form)
        row=QHBoxLayout();button('Guardar configuración',self.save_settings,row);button('Eliminar clave',self.delete_key,row);button('Limpiar caché e historial',self.clear_cache,row);layout.addLayout(row)
        label=QLabel('Clave cifrada por Windows para este usuario y equipo. No se exporta.\nLa aplicación solo consulta internet al pulsar Buscar. Cancelar detiene las consultas pendientes; una solicitud activa puede tardar hasta 12 s.');label.setWordWrap(True);layout.addWidget(label)
    def make_ai(self):
        page=QWidget();layout=QVBoxLayout(page);self.tabs.addTab(page,'IA local')
        intro=QLabel('Ollama en este PC · una tarea simultánea · sin descargas ni servicios cloud.\nLa IA analiza extractos y genera borradores. Verifica afirmaciones, rumores y posibles contradicciones.');intro.setWordWrap(True);layout.addWidget(intro)
        row=QHBoxLayout();self.model=combo([self.settings.get('model','llama3.2:1b')]);row.addWidget(self.model,1);button('Detectar modelos instalados',self.detect_models,row);layout.addLayout(row)
        row=QHBoxLayout();button('Analizar resultado seleccionado',lambda:self.analyze_ai(False),row);button('Agrupar y analizar visibles (máx. 6)',lambda:self.analyze_ai(True),row);layout.addLayout(row)
        self.ai_cache=QCheckBox('Reutilizar análisis local durante 24 horas');self.ai_cache.setChecked(True);layout.addWidget(self.ai_cache)
        self.analysis_list=QListWidget();self.analysis_list.setMaximumHeight(85);self.analysis_list.currentRowChanged.connect(self.show_analysis);layout.addWidget(self.analysis_list)
        self.ai_text=QTextBrowser();self.ai_text.setOpenExternalLinks(False);self.ai_text.anchorClicked.connect(lambda u:QDesktopServices.openUrl(u) if u.scheme() in ('http','https') else None);layout.addWidget(self.ai_text)
        row=QHBoxLayout();button('Crear oportunidad con este análisis',self.ai_opportunity,row);button('Preparar para guion',lambda:self.export('script'),row);layout.addLayout(row)
    def days(self):return [0,1,7,30,90][self.period.currentIndex()]
    def refresh(self):
        category=self.category.currentText()
        categories=core.CATEGORIES+sorted({s['category'] for s in self.settings['sources']}|{r['category'] for r in self.project['items']}-set(core.CATEGORIES))
        self.category.clear();self.category.addItems(['Todas las categorías']+categories)
        if self.category.findText(category)>=0:self.category.setCurrentText(category)
        self.visible=core.filtered(self.project['items'],self.query.text(),'' if self.category.currentIndex()==0 else self.category.currentText(),self.country.text().strip(),self.days())
        self.visible.sort(key=lambda r:r.get('priority',{}).get('score',-1),reverse=True)
        fill(self.results,[(r['title'],r['source'],r['published'][:10] or 'Sin fecha',r.get('priority',{}).get('score','—')) for r in self.visible]);self.details.clear()
        self.video_rows=[r for r in self.project['items'] if r['source']=='YouTube' or 'viewCount' in r['observed']]
        fill(self.videos,[(r['title'],r['observed'].get('channel','—'),r['observed'].get('viewCount','No disponible'),r['observed'].get('duration','—'),r['published'][:10]) for r in self.video_rows])
        fill(self.ideas,[(o['topic'],o['status'],str(o['score'])+'/100') for o in self.project['opportunities']])
        fill(self.sources,[(s['name'],s['category'],s.get('country',''), 'Sí' if s.get('favorite') else 'No') for s in self.settings['sources']])
        self.channel_list.clear();self.channel_list.addItems(self.project['channels']);self.pattern_label.setText('Palabras repetidas en títulos (frecuencia en la muestra):\n'+', '.join(f'{w}: {n}' for w,n in core.patterns(self.project['items'])))
        self.analysis_list.blockSignals(True);self.analysis_list.clear();self.analysis_list.addItems([a['created'][:19]+' · '+a['result']['resumen'][:90] for a in self.project.get('analyses',[])]);self.analysis_list.blockSignals(False)
        self.ai_text.clear();self.idea_details.clear();self.video_detail.clear()
    def selected(self):
        i=self.results.currentRow();return self.visible[i] if 0<=i<len(self.visible) else None
    def show_details(self):
        r=self.selected()
        if not r:return
        e=core.html.escape
        self.details.setHtml(f'<h3>{e(r["title"])}</h3><p>{e(r["summary"][:4000])}</p><p>País: {e(r["country"] or "No disponible")} · Categoría: {e(r["category"])}</p><p>Publicación: {e(r["published"] or "No disponible")}<br>Consulta: {e(r["retrieved"])}</p><p>Señal: {len(r["sources"])} referencia(s) agrupada(s); no demuestra popularidad ni independencia entre fuentes. Procedencia: {e(r["origin"])}</p><p>Datos observados: {e(json.dumps(r["observed"],ensure_ascii=False))}</p>'+''.join(f'<p><a href="{e(s["url"])}">{e(s["name"])}</a></p>' for s in r['sources']))
        p=r.get('priority')
        if p:self.details.append('<p><b>Prioridad de revisión: '+str(p['score'])+'/100</b><br>'+e(json.dumps(p,ensure_ascii=False))+'</p>')
        groups=[g for g in self.project.get('groups',[]) if r['id'] in g['item_ids'] and len(g['item_ids'])>1]
        if groups:self.details.append('<p>Posible acontecimiento compartido con otros '+str(len(groups[0]['item_ids'])-1)+' registros. Agrupación aproximada de titulares; revisa sus fuentes.</p>')
    def show_video(self):
        i=self.videos.currentRow()
        if i<0 or i>=len(self.video_rows):return
        r=self.video_rows[i];o=r['observed'];ratio='No disponible'
        try:
            if int(o.get('subscriberCount',0))>0:ratio=f'{int(o["viewCount"])/int(o["subscriberCount"]):.2f}'
        except (ValueError,KeyError):pass
        self.video_detail.setPlainText(f'{r["title"]}\n{r["url"]}\nConsulta: {r["retrieved"]} · Procedencia: {r["origin"]}\nVistas / suscriptores actuales: {ratio}. No mide alcance entre suscriptores ni rendimiento futuro.\n'+json.dumps(o,ensure_ascii=False))
    def show_idea(self):
        i=self.ideas.currentRow()
        if i<0:return
        self.idea_details.setPlainText(json.dumps(self.project['opportunities'][i],ensure_ascii=False,indent=2))
    def start(self,fn,on_done=None):
        if self.worker is not None:self.status.setText('Ya hay una tarea en curso. Puedes cancelarla antes de iniciar otra.');return
        cancel=threading.Event();http=core.Http(self.home/'cache',self.ttl.value(),cancel);self.worker=Worker(lambda:fn(http),cancel)
        http.progress=self.worker.progress.emit;self.worker.progress.connect(self.status.setText)
        self.worker.done.connect(on_done or self.received);self.worker.failed.connect(lambda s:self.status.setText(s));self.worker.finished.connect(self.finished)
        self.cancel.setEnabled(True);self.search_button.setEnabled(False);self.today_button.setEnabled(False);self.ysearch.setEnabled(False);self.status.setText('Procesando… Puedes seguir revisando la investigación.');self.worker.start()
    def finished(self):
        self.worker.deleteLater();self.worker=None;self.cancel.setEnabled(False);self.search_button.setEnabled(True);self.today_button.setEnabled(True);self.ysearch.setEnabled(True)
        if self.closing:self.close()
    def received(self,data):
        # Actualizar un registro existente conserva su identificador local.
        old={core.canonical(r['url']):r for r in self.project['items']}
        for r in data['items']:
            key=core.canonical(r['url'])
            if key in old:r['id']=old[key]['id']
            old[key]=r
        self.project['items']=core.dedupe(list(old.values()));self.project['groups']=research.group_events(self.project['items']);self.dirty=True;self.refresh()
        self.status.setText(f'{len(data["items"])} resultados recibidos · {len(self.visible)} visibles · {data["requests"]} solicitudes · {data["hits"]} lecturas de caché.'+(' Fuentes con incidencias: '+' | '.join(data['errors']) if data['errors'] else ''))
    def search_radar(self):
        sources=[dict(s) for s in self.settings['sources'] if not self.favorite.isChecked() or s.get('favorite')]
        if not sources:self.error('Añade una fuente o desactiva Solo favoritas.');return
        self.record_history(self.query.text());self.start(lambda h:core.radar(h,sources))
    def search_today(self):
        weights={k:w.value() for k,w in self.radar_weights.items()}
        if not sum(weights.values()):self.error('Define al menos un peso del radar mayor que cero.');return
        self.period.setCurrentIndex(1)
        sources=[dict(s) for s in self.settings['sources'] if not self.favorite.isChecked() or s.get('favorite')]
        if not sources:self.error('Añade una fuente o desactiva Solo favoritas.');return
        self.record_history(self.query.text());self.start(lambda h:research.today(h,sources,weights))
    def search_channel_rss(self):
        channel=self.channel.text();days=[7,30,90,0][self.yperiod.currentIndex()]
        self.start(lambda h:research.youtube_feed(h,channel,days))
    def fetch_metadata(self):
        d=EntryDialog(self,'Metadatos públicos sin sesión',{'URL YouTube o TikTok':''})
        if d.exec():
            url=d.values()['URL YouTube o TikTok'];self.start(lambda h:research.public_metadata(h,url))
    def compare_channels(self):
        d=QDialog(self);d.setWindowTitle('Comparación de la muestra');d.resize(800,600);layout=QVBoxLayout(d);view=QTextBrowser();layout.addWidget(view)
        data=research.channels(self.project['items']);e=core.html.escape
        content='<h2>Canales y frecuencia observada</h2>'+''.join(f'<h3>{e(c["channel"])}</h3><p>{c["sample_size"]} registros · intervalo medio: {c["mean_gap_days"]} días · duración media: {c["mean_duration_seconds"]} s</p><p>Temas: {e(str(c["terms"]))}</p>' for c in data['channels'])
        content+='<h2>Videos por vistas acumuladas / día de antigüedad</h2>'+''.join(f'<p>{e(v["title"])} · {v["views_per_day"]} vistas/día · {v["age_days"]} días · {e(v["origin"])}</p>' for v in data['videos'][:30])
        content+=''.join('<p>'+e(w)+'</p>' for w in data['warnings']);view.setHtml(content);d.exec()
    def detect_models(self):
        def done(models):
            self.model.clear();self.model.addItems([m['name'] for m in models]);self.status.setText(f'{len(models)} modelo(s) local(es) detectado(s). No se descargó ninguno.')
        self.start(lambda h:intelligence.Ollama(self.home/'ai-cache',h.cancel).models(),done)
    def analyze_ai(self,multiple):
        rows=self.visible[:6] if multiple else ([self.selected()] if self.selected() else [])
        if not rows:self.error('Selecciona un resultado en Radar o carga noticias primero.');return
        model=self.model.currentText();cache=self.ai_cache.isChecked();self.settings['model']=model;self.persist_settings();self.tabs.setCurrentIndex(5)
        self.start(lambda h:intelligence.Ollama(self.home/'ai-cache',h.cancel,h.progress).analyze(rows,model,cache),self.ai_received)
    def ai_received(self,analysis):
        entries=self.project.setdefault('analyses',[])
        old=next((i for i,a in enumerate(entries) if a['id']==analysis['id']),None)
        if old is None:entries.append(analysis)
        else:entries[old]=analysis
        self.dirty=True;self.refresh();self.analysis_list.setCurrentRow(next(i for i,a in enumerate(entries) if a['id']==analysis['id']));self.status.setText('Análisis local listo'+(' (caché)' if analysis['cached'] else '')+'. Revisa las propuestas y las fuentes antes de usarlas.')
    def show_analysis(self,index):
        entries=self.project.get('analyses',[])
        if not 0<=index<len(entries):return
        a=entries[index];r=a['result'];e=core.html.escape
        content='<h2>'+e(r['categoria'])+'</h2><p>'+e(r['resumen'])+'</p><p><b>Borrador de IA local: requiere verificación humana.</b></p>'
        if a.get('quality_notes'):content+='<h3>Control de calidad y límites</h3><ul>'+''.join('<li>'+e(x)+'</li>' for x in a['quality_notes'])+'</ul>'
        for key,label in [('titulos','Tres títulos'),('ganchos','Tres ganchos'),('enfoques','Enfoques'),('verificar','Pendiente de verificar'),('patrones','Patrones sugeridos')]:content+='<h3>'+label+'</h3><p>'+e(a.get('field_provenance',{}).get(key,'ollama_borrador'))+'</p><ul>'+''.join('<li>'+e(x)+'</li>' for x in r[key])+'</ul>'
        for key,label,text in [('afirmaciones','Afirmaciones y procedencia','texto'),('grupos','Agrupaciones sugeridas','tema'),('contradicciones','Posibles contradicciones','descripcion')]:
            content+='<h3>'+label+'</h3>'
            content+=''.join('<p>'+e(x.get('tipo',''))+': '+e(x[text])+' ['+e(', '.join(x['fuentes']))+']</p>' for x in r[key]) or '<p>No identificadas por el modelo; no implica ausencia real.</p>'
        content+='<h3>Documentos entregados al modelo</h3>'+''.join(f'<p>{e(k)}: <a href="{e(s["url"])}">{e(s["title"])}</a> · {e(s["retrieved"])}</p>' for k,s in a['sources'].items())
        self.ai_text.setHtml(content)
    def ai_opportunity(self):
        i=self.analysis_list.currentRow()
        if i<0:self.error('Selecciona un análisis.');return
        a=self.project['analyses'][i];row=next((r for r in self.project['items'] if r['id'] in a['input_ids']),None)
        if not row:self.error('No está disponible el registro de origen de este análisis.');return
        self.evaluate(row,analysis=a)
    def search_youtube(self):
        def run():
            key=secrets.load(self.home/'youtube.dpapi')
            if not key:raise core.UserError('Añade tu clave en Configuración avanzada. También puedes importar CSV o enlaces sin API.')
            q=self.yquery.text().strip();ch=self.channel.text().strip();days=[7,30,90,0][self.yperiod.currentIndex()]
            if not q and not ch:raise core.UserError('Escribe un tema o canal.')
            self.start(lambda h:core.YouTube(h,key).search(q,days,ch))
        self.guarded(run)
    def cancel_search(self):
        if self.worker:self.worker.cancel.set();self.status.setText('Cancelando… esperando que termine la solicitud activa.')
    def save_query(self):
        q=self.query.text().strip()
        if q and q not in self.settings['queries']:
            self.settings['queries'].append(q);self.saved.addItem(q);self.persist_settings()
    def record_history(self,query):
        if self.history.isChecked():
            def run():
                path=self.home/'history.json';data=core.read_json(path) if path.exists() else [];data.append(dict(query=query,date=core.now()));core.atomic_json(path,data[-100:])
            self.guarded(run)
    def persist_settings(self):self.guarded(lambda:core.atomic_json(self.home/'settings.json',self.settings))
    def save_settings(self):
        def run():
            if self.key.text().strip():secrets.save(self.home/'youtube.dpapi',self.key.text().strip());self.key.clear()
            self.settings.update(ttl=self.ttl.value(),history=self.history.isChecked(),radar_weights={k:w.value() for k,w in self.radar_weights.items()});core.atomic_json(self.home/'settings.json',self.settings);self.status.setText('Configuración guardada. La clave permanece fuera de las investigaciones.')
        self.guarded(run)
    def delete_key(self):self.guarded(lambda:secrets.save(self.home/'youtube.dpapi',''));self.key.clear()
    def clear_cache(self):
        def run():
            for path in (self.home/'cache').glob('*.json'):path.unlink()
            (self.home/'history.json').unlink(missing_ok=True);self.status.setText('Caché e historial eliminados.')
        if self.worker:self.error('Espera a que termine la consulta antes de limpiar la caché.');return
        self.guarded(run)
    def add_source(self):
        if len(self.settings['sources'])>=30:self.error('Máximo 30 fuentes.');return
        d=EntryDialog(self,'Añadir RSS / Atom',{'Nombre':'','URL':'','Categoría':'General','País (ISO; opcional)':''})
        if d.exec():
            def run():
                v=d.values()
                if not v['Nombre']:raise core.UserError('Escribe un nombre.')
                self.settings['sources'].append(dict(name=v['Nombre'],url=core.safe_url(v['URL']),category=v['Categoría'] or 'General',country=v['País (ISO; opcional)'].upper(),favorite=True));self.persist_settings();self.refresh()
            self.guarded(run)
    def remove_source(self):
        i=self.sources.currentRow()
        if i>=0:self.settings['sources'].pop(i);self.persist_settings();self.refresh()
    def toggle_favorite(self):
        i=self.sources.currentRow()
        if i>=0:self.settings['sources'][i]['favorite']=not self.settings['sources'][i].get('favorite');self.persist_settings();self.refresh()
    def manual(self):
        d=EntryDialog(self,'Añadir información manual',{'Título':'','URL':'','Plataforma / fuente':'Manual','Categoría':'General','País':'','Publicado (ISO; opcional)':'','Resumen':''})
        if d.exec():
            def run():
                v=d.values();published=v['Publicado (ISO; opcional)']
                if not v['Título']:raise core.UserError('Escribe un título.')
                if published and core.date(published) is None:raise core.UserError('Usa una fecha ISO, por ejemplo 2026-11-04.')
                self.add_rows([core.item(v['Título'],v['URL'],v['Plataforma / fuente'],v['Categoría'],v['País'],published,v['Resumen'])])
            self.guarded(run)
    def add_rows(self,rows):self.project['items']=core.dedupe(self.project['items']+rows);self.dirty=True;self.refresh();self.status.setText(f'{len(rows)} registros importados; procedencia conservada.')
    def import_csv(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar datos manuales','','CSV (*.csv)')
        if path:self.guarded(lambda:self.add_rows(core.import_csv(path)))
    def import_trends(self):
        path,_=QFileDialog.getOpenFileName(self,'CSV de interés a lo largo del tiempo','','CSV (*.csv)')
        if not path:return
        d=EntryDialog(self,'Contexto de Google Trends',{'Tema':'','URL de la consulta':'https://trends.google.com/trends/','País':''})
        if d.exec():
            v=d.values();self.guarded(lambda:self.add_rows(core.import_trends(path,v['Tema'] or 'Google Trends',v['URL de la consulta'],v['País'])))
    def open_source(self):
        r=self.selected()
        if r:QDesktopServices.openUrl(QUrl(core.safe_url(r['url'])))
    def save_channel(self):
        ch=self.channel.text().strip()
        if ch and ch not in self.project['channels']:self.project['channels'].append(ch);self.dirty=True;self.refresh()
    def remove_channel(self):
        i=self.channel_list.currentRow()
        if i>=0:self.project['channels'].pop(i);self.dirty=True;self.refresh()
    def create_opportunity(self):
        r=self.selected()
        if not r:self.error('Selecciona primero un resultado del Radar.');return
        self.evaluate(r)
    def evaluate(self,row,existing=None,analysis=None):
        d=OpportunityDialog(self,row,existing)
        if analysis:d.notes.setPlainText('Borrador IA pendiente de verificar.\n'+'\n'.join(analysis['result']['verificar']));d.angle.setPlainText('\n'.join(analysis['result']['enfoques']))
        if d.exec():
            o=core.opportunity(row,{k:w.value() for k,w in d.values.items()},{k:w.value() for k,w in d.weights.items()},d.notes.toPlainText(),d.angle.toPlainText(),d.state.currentText())
            o['missing_data']=research.priority(row)['missing']+['Competencia, originalidad y dificultad son valoraciones editoriales.']
            if analysis:
                o['analysis_id']=analysis['id'];o['ai_titles']=analysis['result']['titulos'];o['ai_hooks']=analysis['result']['ganchos'];o['warnings']+=analysis['warnings']
                o['sources']=[dict(name=s['title'],url=s['url'],published=s['published'],retrieved=s['retrieved']) for s in analysis['sources'].values()]
            elif existing:
                o['warnings']=list(existing['warnings'])
                for k in ('analysis_id','ai_titles','ai_hooks'):
                    if k in existing:o[k]=existing[k]
            if existing:o['id']=existing['id'];self.project['opportunities'][self.project['opportunities'].index(existing)]=o
            else:self.project['opportunities'].append(o)
            self.dirty=True;self.refresh();self.tabs.setCurrentIndex(2)
    def edit_opportunity(self):
        i=self.ideas.currentRow()
        if i>=0:
            o=self.project['opportunities'][i];r=dict(title=o['topic'],category=o['category'],summary=o['summary'],sources=o['sources'],published=o['published'],retrieved=o['retrieved'],observed=o['observed'],origin=o['origin']);self.evaluate(r,o)
    def delete_opportunity(self):
        i=self.ideas.currentRow()
        if i>=0 and QMessageBox.question(self,'Eliminar','¿Eliminar esta oportunidad?')==QMessageBox.Yes:self.project['opportunities'].pop(i);self.dirty=True;self.refresh();self.idea_details.clear()
    def can_replace(self):
        if self.worker:self.error('Cancela o espera a que termine la consulta antes de cambiar de investigación.');return False
        if not self.dirty:return True
        answer=QMessageBox.question(self,'Cambios sin guardar','¿Guardar los cambios de la investigación?',QMessageBox.Save|QMessageBox.Discard|QMessageBox.Cancel)
        if answer==QMessageBox.Save:return self.save_project()
        return answer==QMessageBox.Discard
    def new_project(self):
        if self.can_replace():self.project=core.new_project();self.path=None;self.dirty=False;self.refresh()
    def save_project(self):
        path=self.path
        if not path:path,_=QFileDialog.getSaveFileName(self,'Guardar investigación','investigacion.json','JSON (*.json)')
        if not path:return False
        def run():core.atomic_json(path,self.project);self.path=path;self.dirty=False;self.record_recent(path);self.status.setText('Investigación guardada en '+path);return True
        return bool(self.guarded(run))
    def open_project(self):
        if not self.can_replace():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir investigación','','JSON (*.json)')
        if path:
            def run():self.project=core.validate_project(core.read_json(path));self.path=path;self.dirty=False;self.record_recent(path);self.refresh();self.status.setText('Investigación abierta.')
            self.guarded(run)
    def record_recent(self,path):
        self.settings['recent']=[path]+[p for p in self.settings.get('recent',[]) if p!=path][:9];self.recent.clear();self.recent.addItems(['Investigaciones guardadas']+self.settings['recent']);self.persist_settings()
    def open_recent(self):
        if self.recent.currentIndex()<1 or not self.can_replace():return
        path=self.recent.currentText()
        def run():self.project=core.validate_project(core.read_json(path));self.path=path;self.dirty=False;self.refresh();self.status.setText('Investigación abierta sin consultar internet.')
        self.guarded(run)
    def export(self,kind):
        if kind in ('creator','script'):
            path=QFileDialog.getExistingDirectory(self,'Carpeta para el paquete CreatorStudio')
            if path:
                def run():
                    folder=Path(path)/(('Guion-' if kind=='script' else 'CreatorStudio-')+core.datetime.now().strftime('%Y%m%d-%H%M%S'))
                    (research.script_package if kind=='script' else core.creator_package)(folder,self.project)
                    self.status.setText('Paquete local generado; no se envió información a ningún servicio.')
                self.guarded(run)
            return
        path,_=QFileDialog.getSaveFileName(self,'Exportar investigación','trendstudio.'+kind,f'{kind.upper()} (*.{kind})')
        if path:
            def run():
                if kind=='json':core.atomic_json(path,self.project)
                elif kind=='csv':core.export_csv(path,self.project['items'])
                else:Path(path).write_text(core.report(self.project),encoding='utf-8')
                self.status.setText('Exportación guardada en '+path)
            self.guarded(run)
    def closeEvent(self,event:QCloseEvent):
        if self.worker:
            self.closing=True;self.cancel_search();event.ignore();return
        if self.can_replace():event.accept()
        else:self.closing=False;event.ignore()

def main():
    app=QApplication(sys.argv);app.setStyle('Fusion');app.setStyleSheet(STYLE);app.setApplicationName('TrendStudio')
    window=MainWindow();window.show()
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(1200,app.quit)
    return app.exec()
