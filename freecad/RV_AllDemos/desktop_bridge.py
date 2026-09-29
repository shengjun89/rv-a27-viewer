"""Local desktop bridge for fixed full-vehicle play and stop actions."""
from pathlib import Path
import json,os,time,traceback
import FreeCAD as App,FreeCADGui as Gui
from PySide import QtCore
import player_ui

CACHE=Path.home()/'Library/Caches/RV_CAD_Demo'
STATE=CACHE/'status.json';COMMAND=CACHE/'command.json'
REVISION=player_ui.REGISTRY_REVISION

def write_json(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix('.'+str(os.getpid())+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2));tmp.replace(p)

class Bridge:
    def __init__(self,parent):
        self.booted=time.time();self.last='';self.request='';self.error='';self.started=False
        self.timer=QtCore.QTimer(parent);self.timer.setInterval(700)
        self.timer.timeout.connect(self.tick);self.timer.start()
        self.tick()
    def tick(self):
        try:
            if COMMAND.exists():
                req=json.loads(COMMAND.read_text())
                created=float(req.get('created_at',0))
                current=(
                    req.get('revision')==REVISION
                    and created>=self.booted-30
                )
                if not current:
                    self.last=req.get('id','')
                elif req.get('id')!=self.last and req.get('action') in {'play_full_vehicle','stop'}:
                    self.last=req['id'];self.request=self.last;self.error=''
                    p=player_ui.show_panel()
                    if req['action']=='play_full_vehicle':
                        p.check_all(True);p.speed.setCurrentIndex(1);p.play_all();self.started=True
                    else:
                        p.reset();self.started=False
                    main=Gui.getMainWindow();main.showNormal();main.raise_();main.activateWindow()
            p=Gui.getMainWindow().findChild(player_ui.Q.QDockWidget,'RV_AllDemos')
            autosave=App.ParamGet('User parameter:BaseApp/Preferences/Document').GetBool('AutoSaveEnabled',False)
            status={'pid':os.getpid(),'heartbeat':time.time(),'revision':REVISION,'request':self.request,'error':self.error,'autosave_enabled':autosave}
            if p:
                s=p.session
                status.update(file=s.doc.FileName,playing=p.timer.isActive(),time=s.time,duration=s.duration,clips=[c.title for c in s.selected],clip_index=s.index,progress=s.doc.TL_Control.Progress,completed=self.started and not p.timer.isActive() and s.duration>0 and s.time>=s.duration,full_vehicle_scene=p.scene.active,animation_transaction=p.scene.transaction_open,visibility_baseline=len(p.scene.baseline),visibility_applied=p.scene.applied_count,ui_status=p.status.text())
            write_json(STATE,status)
        except Exception:
            self.error=traceback.format_exc()
            write_json(STATE,{'pid':os.getpid(),'heartbeat':time.time(),'revision':REVISION,'request':self.request,'error':self.error})

def install():
    main=Gui.getMainWindow()
    old=getattr(main,'_rv_desktop_bridge',None)
    if old:old.timer.stop()
    main._rv_desktop_bridge=Bridge(main)
    return main._rv_desktop_bridge

def launch():
    def ready():
        try:
            player_ui.show_panel()
            install()
        except Exception:
            write_json(STATE,{'pid':os.getpid(),'heartbeat':time.time(),'error':traceback.format_exc()})
    QtCore.QTimer.singleShot(100,ready)
