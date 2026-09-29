"""One document, one timeline. Drives existing controls without adding geometry."""
from pathlib import Path
from dataclasses import dataclass
import importlib.util
import FreeCAD as App

PACKAGE=Path(__file__).resolve().parent

def number(v):
    return v.Value if hasattr(v,'Value') else float(v)

def effective(o,seen=None):
    if o is None or not getattr(o,'Visibility',True):return False
    seen=set() if seen is None else set(seen)
    if o.Name in seen:return True
    seen.add(o.Name)
    return all(effective(p,seen) for p in o.InList if hasattr(p,'Group') and o in p.Group)

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3-2*t)

def between(p,a,b,start,end):
    return start+(end-start)*smooth((p-a)/(b-a))

def roundtrip(p,start,maximum):
    if p<.08:return between(p,0,.08,start,0)
    if p<.45:return between(p,.08,.45,0,maximum)
    if p<.55:return maximum
    if p<.92:return between(p,.55,.92,maximum,0)
    return between(p,.92,1,0,start)

@dataclass
class Clip:
    id: str
    title: str
    duration: float
    keys: list
    apply: object

class Session:
    def __init__(self,doc):
        self.doc=doc;self.name=doc.Name;self.clips=[];self.notes=[];self.static_scene=[]
        self.selected=[];self.duration=0.;self.time=0.;self.index=None
        self.snapshot={};self.changed_keys=set();self._build()
        for clip in self.clips:
            for name,prop in clip.keys:
                obj=doc.getObject(name)
                if obj is None or prop not in obj.PropertiesList:continue
                value=getattr(obj,prop)
                if prop=='Placement':value=App.Placement(value)
                elif hasattr(value,'Value'):value=value.Value
                self.snapshot[(name,prop)]=value

    def alive(self):
        return App.listDocuments().get(self.name) is self.doc

    def initial(self,name,prop):return self.snapshot[(name,prop)]

    def _scalar(self,name,prop,maximum,duration,title):
        def pose(p):
            setattr(self.doc.getObject(name),prop,roundtrip(p,number(self.initial(name,prop)),maximum))
            return title
        self.clips.append(Clip(name,title,duration,[(name,prop)],pose))

    def _build(self):
        d=self.doc
        office_keys=[('KT_Moving','PullOut')]+[('CC_Control',p) for p in ['ChairY','SeatHeight','SwivelAngle']]
        sofa_file=PACKAGE/'living_motion.py'
        if d.getObject('SB_Control') and effective(d.getObject('M12_Sofa')) and sofa_file.is_file():
            sofa=load('_rv_all_sofa',sofa_file)
            keys=office_keys+[('S27_Params','Travel')]+[('SB_Control',p) for p in ['Progress','UnlockLift','Stage']]
            if d.getObject('SB_Infill'):keys.append(('SB_Infill','Placement'))
            def living(p):
                return sofa.state(d,roundtrip(p,number(self.initial('SB_Control','Progress')),100))
            self.clips.append(Clip('living','办公收纳 → 沙发成床 → 复位',22,keys,living))
        elif effective(d.getObject('KT_Moving')) and effective(d.getObject('CC_Chair')):
            def office(p):
                tray=number(self.initial('KT_Moving','PullOut'));chair=number(self.initial('CC_Control','ChairY'))
                d.KT_Moving.PullOut=between(p,0,.18,tray,0) if p<.18 else 0 if p<.82 else between(p,.82,1,0,tray)
                d.CC_Control.ChairY=between(p,.18,.40,chair,-600) if p<.5 else between(p,.60,.82,-600,chair)
                return '琴托带 MIDI 收回，办公椅收入；按原路返回'
            self.clips.append(Clip('office','工作台、MIDI 与办公椅收纳',12,office_keys,office))
        if d.getObject('BD_Control') and effective(d.getObject('BD_Door')):
            self._scalar('BD_Control','OpenPercent',100,7,'卫生间卷门开合')
            self.clips[-1].id='bath'
        e01='SS_OH_E01' if d.getObject('SS_OH_E01') else 'OH_E01'
        for name in ['OH_L01','OH_L02','OH_L03','OH_L04','OH_L05','OH_K01',e01,'OH_E02']:
            if effective(d.getObject(name)) and hasattr(d.getObject(name),'OpenAngle'):
                self._scalar(name,'OpenAngle',86,4,d.getObject(name).Label.split('（')[0])
        entry_doors=[('SS_ED_Upper','入口上柜门'),('SS_ED_Middle','入口下柜门')] if d.getObject('SS_ED_Upper') else [('ED_Upper','入口上柜门'),('ED_Middle','入口中柜门'),('ED_Bottom','入口底柜门')]
        for name,title in entry_doors:
            if effective(d.getObject(name)) and hasattr(d.getObject(name),'OpenAngle'):
                self._scalar(name,'OpenAngle',90,5,title)
        # Current R6 appliance assemblies keep the original door solids and pivots.
        for name,maximum,duration,title in [
            ('AP_WasherSwing',95,6,'洗衣机门开启 → 关闭'),
            ('AP_FridgeSwing',105,6,'42 L 冰箱门开启 → 关闭'),
            ('WD_LeftDoor',90,5,'洗衣液收纳柜门开启 → 关闭'),
        ]:
            obj=d.getObject(name)
            if effective(obj) and hasattr(obj,'OpenAngle'):
                self._scalar(name,'OpenAngle',maximum,duration,title)
        if d.getObject('AP_FridgeSwing'):
            self.notes.append('当前R7电器门已接入；洗衣机铰轴为示意，厂家实际角度仍待核。电池从已有车外舱门检修，演示不拆床面。')
        # Only the ladder geometry already present and visible in this document is played.
        if d.getObject('TL_Control') and effective(d.getObject('TL_Ladder')):
            if getattr(d.TL_Control,'StowDestination','') == 'CabinetPocket':
                def cabinet_ladder(p):
                    start=number(self.initial('TL_Control','Progress'))
                    d.TL_Control.Progress=roundtrip(p,start,100)
                    value=d.TL_Control.Progress
                    if value<10:return '退出使用锁销，锁座回缩让开滑移路径'
                    if value<25:return '踏板上翻收齐'
                    if value<65:return '整梯转直、按地面高度缩短'
                    if value<70:return '滚珠脚接地，准备横移'
                    if value<95:return '保持朝向，伸缩上轨随梯一起横推入柜'
                    return '关闭梯仓窄门，运输锁销到位'
                self.clips.append(Clip('upright_ladder','柜内藏梯：翻板、直立、横推入柜、关门',30,[('TL_Control','Progress')],cabinet_ladder))
            elif 'StowTravel' in d.TL_Control.PropertiesList and d.getObject('CC_Control') and d.getObject('KT_Moving'):
                keys=[('TL_Control','Progress'),('CC_Control','ChairY'),('KT_Moving','PullOut')]
                def deep_ladder(p):
                    chair=number(self.initial('CC_Control','ChairY'));tray=number(self.initial('KT_Moving','PullOut'))
                    start=number(self.initial('TL_Control','Progress'))
                    d.KT_Moving.PullOut=between(p,0,.12,tray,0) if p<.12 else between(p,.96,1,0,tray) if p>.96 else 0
                    d.CC_Control.ChairY=between(p,.12,.26,chair,-600) if p<.26 else between(p,.86,.96,-600,chair) if p>.86 else -600
                    d.TL_Control.Progress=start if p<.26 or p>.86 else roundtrip((p-.26)/.60,start,100)
                    return '办公椅先让位；梯子直立后深藏柜后，再复位。攀爬前移开入口地毯。'
                self.clips.append(Clip('upright_ladder','藏梯加深：办公椅让位、横移400、复位',42,keys,deep_ladder))
            else:
                self._scalar('TL_Control','Progress',100,30,'直立横移梯：翻板、直立、横移收纳与复位')
                self.clips[-1].id='upright_ladder'
        if d.getObject('DS_Motion'):
            self.notes.append('旧楼梯演示已移除，统一播放器不会播放旧楼梯。')
        if d.getObject('TL_Control'):
            self.notes.append('当前为柜内藏梯：直立后横移344毫米入柜，无90度转向；上轨两级缩回柜内，关门与运输锁同步。攀爬前移开入口地毯。' if getattr(d.TL_Control,'StowDestination','') == 'CabinetPocket' else ('已接入当前直立横移梯；400行程版先收琴托、让开办公椅，完成后恢复。攀爬前移开入口地毯。' if 'StowTravel' in d.TL_Control.PropertiesList else '已接入直立横移梯；不回转梯子。'))
        else:
            self.notes.append('当前打开的文档尚无新直立横移梯；请使用已更新的 A27，旧楼梯演示已移除。')
        top_names=['TS_SlopeDoor','TS_FlatTop','TS_OuterSide','TS_RearPanel']
        top_parts=[d.getObject(name) for name in top_names]
        if all(top_parts) and all(not o.Shape.isNull() and o.Shape.isValid() for o in top_parts):
            self.static_scene=top_names
            self.notes.append('统一柜顶斜面与顶部储物结构已接入当前场景：四块板件随整车显示，播放和复位均不改变其位置或可见性。')
        else:
            self.notes.append('当前工程未完整包含统一柜顶四构件；演示仍可运行，但顶部结构不是最新版本。')

    def configure(self,ids):
        self.restore()
        chosen=set(ids);self.selected=[c for c in self.clips if c.id in chosen]
        self.duration=sum(c.duration for c in self.selected);self.time=0.;self.index=None

    def restore_pose(self):
        if not self.alive():self.index=None;return
        for name,prop in self.changed_keys:
            value=self.snapshot[(name,prop)]
            obj=self.doc.getObject(name)
            if obj is not None and prop in obj.PropertiesList:setattr(obj,prop,value)
        self.doc.recompute();self.changed_keys.clear();self.index=None

    def restore(self):
        self.restore_pose()

    @property
    def current_clip(self):
        return self.selected[self.index] if self.index is not None else None

    def seek(self,seconds):
        if not self.alive():raise RuntimeError('工程已关闭；请重新打开演示面板。')
        self.time=max(0.,min(self.duration,float(seconds)))
        if not self.selected or self.time>=self.duration:
            self.restore();return '播放完成，已恢复打开面板时的姿态'
        offset=0.
        for i,clip in enumerate(self.selected):
            if self.time<offset+clip.duration:
                if self.index!=i:self.restore_pose();self.index=i
                self.changed_keys.update(key for key in clip.keys if key in self.snapshot)
                label=clip.apply((self.time-offset)/clip.duration)
                self.doc.recompute()
                return label
            offset+=clip.duration

    def skip(self):
        if self.index is None:return self.seek(self.duration)
        return self.seek(sum(c.duration for c in self.selected[:self.index+1]))
