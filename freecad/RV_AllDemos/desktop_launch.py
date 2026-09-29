"""Open the current A27 and play all registered animations, reusing our window."""
from pathlib import Path
import json,os,time,uuid,subprocess
CACHE=Path.home()/'Library/Caches/RV_CAD_Demo';CACHE.mkdir(parents=True,exist_ok=True);CACHE.chmod(0o700)
STATE=CACHE/'status.json';COMMAND=CACHE/'command.json'
REVISION=2026092901
request={
    'id':str(uuid.uuid4()),
    'action':'play_full_vehicle',
    'revision':REVISION,
    'created_at':time.time(),
}
def alive():
    try:
        status=json.loads(STATE.read_text());os.kill(int(status['pid']),0)
        return time.time()-status['heartbeat']<8 and status.get('revision')==REVISION
    except (OSError,ValueError,KeyError):return False
reusable=alive()
tmp=COMMAND.with_suffix('.'+request['id']+'.tmp');tmp.write_text(json.dumps(request));tmp.replace(COMMAND)
if not reusable:
    macro=Path(__file__).resolve().parent.parent/'整车一键演示.FCMacro'
    subprocess.run(['/usr/bin/open','-n','-a','/Applications/FreeCAD.app','--args',str(macro)],check=True)
# Bounded startup acknowledgement for launcher troubleshooting; never edits CAD.
for _ in range(160):
    try:
        s=json.loads(STATE.read_text())
        if s.get('request')==request['id']:
            (CACHE/'last_launch.json').write_text(json.dumps({'request':request['id'],'reused_window':reusable,'acknowledged':True,'pid':s['pid'],'error':s.get('error','')},ensure_ascii=False,indent=2));break
    except (OSError,ValueError):pass
    time.sleep(.25)
else:
    (CACHE/'last_launch.json').write_text(json.dumps({'request':request['id'],'acknowledged':False,'reused_window':reusable}))
