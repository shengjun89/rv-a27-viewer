"""Qt controller for the current A27 full-vehicle animation."""
from pathlib import Path
import time,sys
import FreeCAD as App
from PySide import QtCore,QtGui,QtWidgets as Q
from animation_core import Session
from scene_view import FullVehicleScene

TARGET=Path(__file__).resolve().parents[2]/'房车完整布局_R7_右舱电池与电器开门演示.FCStd'
REGISTRY_REVISION=2026092901

def redraw():
    if App.GuiUp:
        import FreeCADGui as Gui
        # Queue painting; updateGui/processEvents re-enters Cocoa while the
        # current slider/timer/close callback still owns its widget state.
        Gui.getMainWindow().update()

def pause_other_players():
    names={'RV_StairDemo','RV_BathRollDemo','RV_SofaBedDemo','RV_TelescopicLadder'}
    app=Q.QApplication.instance()
    if not app:return
    widgets=list(app.topLevelWidgets())
    for top in list(widgets):widgets.extend(top.findChildren(Q.QDockWidget))
    for w in widgets:
        if w.objectName() in names or w.windowTitle().startswith('办公区｜'):
            if callable(getattr(w,'pause',None)):w.pause()

def bind_slider_actions(panel,legacy=False):
    if getattr(panel,'_rv_slider_actions_bound',False):return
    # Upgrade an already-open pre-fix panel without destroying its Qt widgets.
    if legacy:
        try:panel.slider.valueChanged.disconnect(panel.scrub)
        except (RuntimeError,TypeError):pass
    panel.slider.actionTriggered.connect(lambda action:panel.scrub(panel.slider.sliderPosition()))
    panel._rv_slider_actions_bound=True


class SaveGuard:
    """Restore temporary animation state before FreeCAD serializes the model."""
    def __init__(self,panel):
        self.panel=panel;self.registered=True
        App.addDocumentObserver(self)

    def stop(self):
        if self.registered:
            App.removeDocumentObserver(self);self.registered=False

    def slotStartSaveDocument(self,doc,filepath):
        panel=self.panel
        if panel and panel.session.doc is doc:
            panel.restore_for_save(filepath)

    def slotDeletedDocument(self,doc):
        panel=self.panel
        if panel and panel.session.doc is doc:
            panel.pause();panel.scene.restore();self.stop()


class DemoPanel(Q.QDockWidget):
    def __init__(self,doc,parent):
        super().__init__('整车一键演示｜A27 R7 电器门',parent)
        self.setObjectName('RV_AllDemos');self.setMinimumWidth(365)
        pause_other_players()
        self.scene=FullVehicleScene(doc);scene_count=len(self.scene.baseline)
        self.session=Session(doc)
        self.busy=False;self.last_tick=0.
        self._rv_registry_revision=REGISTRY_REVISION
        self.timer=QtCore.QTimer(self);self.timer.setInterval(80);self.timer.timeout.connect(self.tick)
        pane=Q.QWidget();self.setWidget(pane);box=Q.QVBoxLayout(pane)
        title=Q.QLabel('按当前视角，在完整车辆中逐项往返播放。\n宏不会旋转、平移、缩放或切换投影视图。')
        title.setWordWrap(True);box.addWidget(title)
        self.toggle_button=Q.QToolButton();self.toggle_button.setText('收起操作区')
        self.toggle_button.setCheckable(True);self.toggle_button.setChecked(True)
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow)
        self.toggle_button.toggled.connect(self.set_controls_expanded);box.addWidget(self.toggle_button)
        self.controls=Q.QWidget();controls_box=Q.QVBoxLayout(self.controls);controls_box.setContentsMargins(0,0,0,0)
        box.addWidget(self.controls)
        self.list=Q.QListWidget();self.list.setMinimumHeight(200);controls_box.addWidget(self.list)
        for clip in self.session.clips:
            item=Q.QListWidgetItem(clip.title,self.list)
            item.setData(QtCore.Qt.UserRole,clip.id)
            item.setFlags(item.flags()|QtCore.Qt.ItemIsUserCheckable)
            item.setCheckState(QtCore.Qt.Checked)
        select=Q.QHBoxLayout();controls_box.addLayout(select)
        for label,checked in [('全选',True),('清空选择',False)]:
            b=Q.QPushButton(label);b.clicked.connect(lambda unused=False,on=checked:self.check_all(on));select.addWidget(b)
        self.full_view_button=Q.QPushButton('恢复完整车显示')
        self.full_view_button.setIcon(self.style().standardIcon(Q.QStyle.SP_DesktopIcon))
        self.full_view_button.setToolTip('恢复整车部件显隐，不改变当前视角')
        self.full_view_button.clicked.connect(self.show_full_vehicle);controls_box.addWidget(self.full_view_button)
        self.play_button=Q.QPushButton('一键播放全部勾选项')
        self.play_button.setIcon(self.style().standardIcon(Q.QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_all);controls_box.addWidget(self.play_button)
        row=Q.QHBoxLayout();controls_box.addLayout(row)
        self.pause_button=Q.QPushButton('暂停 / 继续')
        self.pause_button.setIcon(self.style().standardIcon(Q.QStyle.SP_MediaPause))
        self.pause_button.clicked.connect(self.pause_resume);row.addWidget(self.pause_button)
        skip=Q.QPushButton('跳过当前项')
        skip.setIcon(self.style().standardIcon(Q.QStyle.SP_MediaSkipForward))
        skip.clicked.connect(self.skip);row.addWidget(skip)
        stop=Q.QPushButton('停止并恢复进入宏前状态')
        stop.setIcon(self.style().standardIcon(Q.QStyle.SP_MediaStop))
        stop.clicked.connect(self.reset);controls_box.addWidget(stop)
        row=Q.QHBoxLayout();controls_box.addLayout(row);row.addWidget(Q.QLabel('速度'))
        self.speed=Q.QComboBox()
        for label,value in [('0.5× 慢速',.5),('1× 正常',1.),('2× 快速',2.)]:self.speed.addItem(label,value)
        self.speed.setCurrentIndex(1);row.addWidget(self.speed)
        self.slider=Q.QSlider(QtCore.Qt.Horizontal);self.slider.setRange(0,10000)
        self.slider.sliderPressed.connect(self.pause)
        # setValue (including a delayed native echo) only changes the display.
        # Seek on actual drag/key/wheel actions, never on playback's own updates.
        bind_slider_actions(self)
        controls_box.addWidget(self.slider)
        self.status=Q.QLabel(f'就绪：{len(self.session.clips)} 项动作。正在准备完整车视图。');self.status.setWordWrap(True);controls_box.addWidget(self.status)
        self.clock=Q.QLabel('');controls_box.addWidget(self.clock)
        note=Q.QLabel('\n'.join(self.session.notes)+'\n宏按工程保存的整车显隐基线播放，不显示草图、参考网格或废弃系统；不会自动保存。若播放中触发保存，会先自动停止并恢复原姿态。\n可在播放中手动旋转、平移和缩放；停止或关闭面板会恢复进入宏前状态。')
        note.setWordWrap(True);controls_box.addWidget(note)
        self.escape_shortcut=QtGui.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Escape),self)
        self.escape_shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.escape_shortcut.activated.connect(self.close)
        self.save_guard=SaveGuard(self)
        app=Q.QApplication.instance()
        if app:app.aboutToQuit.connect(self.reset)
        if not self.session.clips:self.play_button.setEnabled(False)
        self.status.setText(f'演示已就绪：播放时应用 {scene_count} 个对象显隐状态、{len(self.session.clips)} 项动作。')

    def set_controls_expanded(self,expanded):
        self.controls.setVisible(bool(expanded))
        self.toggle_button.setText('收起操作区' if expanded else '展开操作区')
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow)

    def checked_ids(self):
        return [self.list.item(i).data(QtCore.Qt.UserRole) for i in range(self.list.count()) if self.list.item(i).checkState()==QtCore.Qt.Checked]

    def check_all(self,on):
        for i in range(self.list.count()):self.list.item(i).setCheckState(QtCore.Qt.Checked if on else QtCore.Qt.Unchecked)

    def update_status(self,label):
        s=self.session
        prefix=f'{s.index+1}/{len(s.selected)} · {s.current_clip.title}\n' if s.current_clip else ''
        self.status.setText(prefix+label)
        view_label='当前视角保持不变' if self.scene.active else '整车显隐已恢复'
        self.clock.setText(f'{s.time:.1f} / {s.duration:.0f} 秒 · {view_label}')
        self.slider.blockSignals(True);self.slider.setValue(round(10000*s.time/s.duration) if s.duration else 0);self.slider.blockSignals(False)

    def fail(self,exc):
        self.pause()
        try:self.session.restore()
        except Exception:pass
        try:self.scene.restore()
        except Exception:pass
        self.status.setText('播放已停止：'+str(exc))

    def show_full_vehicle(self):
        try:
            count=self.scene.enter()
            self.status.setText(f'完整车视图已就绪：已应用 {count} 个对象的保存显隐状态。')
            self.clock.setText('保持当前视角 · 仅恢复整车部件显示')
            redraw()
        except Exception as exc:self.fail(exc)

    def play_all(self):
        self.pause();pause_other_players()
        try:
            ids=self.checked_ids()
            if not ids:self.status.setText('请至少勾选一项动作。');return
            self.session.configure(ids);self.scene.enter()
            self.update_status(self.session.seek(0))
            self.last_tick=time.monotonic();self.timer.start();redraw()
        except Exception as exc:self.fail(exc)

    def pause(self):self.timer.stop()

    def pause_resume(self):
        if self.timer.isActive():self.pause();self.status.setText(self.status.text()+'\n已暂停');return
        if not self.session.selected or self.session.time>=self.session.duration:self.play_all();return
        pause_other_players();self.last_tick=time.monotonic();self.timer.start()

    def tick(self):
        if self.busy:return
        self.busy=True
        try:
            now=time.monotonic();delta=min(now-self.last_tick,.30);self.last_tick=now
            label=self.session.seek(self.session.time+delta*float(self.speed.currentData()))
            if self.session.time>=self.session.duration:
                self.pause();self.scene.restore()
                label='播放完成，动作和显隐状态均已恢复'
            self.update_status(label)
            redraw()
        except Exception as exc:self.fail(exc)
        finally:self.busy=False

    def scrub(self,value):
        if self.busy:return
        self.pause()
        try:
            if not self.session.selected:self.session.configure(self.checked_ids())
            self.scene.enter()
            label=self.session.seek(self.session.duration*value/10000)
            if self.session.duration and self.session.time>=self.session.duration:
                self.scene.restore();label='已跳到末尾，并恢复进入宏前状态'
            self.update_status(label);redraw()
        except Exception as exc:self.fail(exc)

    def skip(self):
        try:
            self.scene.enter();label=self.session.skip();self.last_tick=time.monotonic()
            if self.session.time>=self.session.duration:
                self.pause();self.scene.restore();label='全部项目已跳过，并恢复进入宏前状态'
            self.update_status(label)
            redraw()
        except Exception as exc:self.fail(exc)

    def reset(self):
        self.pause()
        try:
            self.session.restore();self.scene.restore();self.session.time=0.
            self.update_status('已恢复进入宏前的动作姿态和显隐状态');redraw()
        except Exception as exc:self.fail(exc)

    def restore_for_save(self,filepath):
        if not (
            self.timer.isActive()
            or self.scene.active
            or self.session.changed_keys
        ):
            return
        self.pause()
        self.session.restore()
        self.scene.restore()
        self.session.time=0.
        self.update_status('保存前已自动停止演示并恢复原姿态')
        redraw()

    def dispose(self):
        self.reset()
        if getattr(self,'save_guard',None):
            self.save_guard.stop()
            self.save_guard=None

    def closeEvent(self,event):
        self.reset();super().closeEvent(event)

def show_panel():
    import FreeCADGui as Gui
    doc=next((d for d in App.listDocuments().values() if d.FileName and Path(d.FileName).resolve()==TARGET.resolve()),None)
    if doc is None:doc=App.openDocument(str(TARGET))
    App.setActiveDocument(doc.Name)
    main=Gui.getMainWindow();old=main.findChild(Q.QDockWidget,'RV_AllDemos')
    if old and (not hasattr(old,'scene') or getattr(old,'_rv_registry_revision',None)!=REGISTRY_REVISION or old.session.doc is not doc):
        try:
            if hasattr(old,'dispose'):old.dispose()
            else:
                old.session.restore();old.scene.restore()
        except Exception:pass
        old.close();main.removeDockWidget(old);old.deleteLater();old=None
    if old:
        old.pause();old.session.restore();old.scene.restore()
        bind_slider_actions(old,legacy=True)
        old.scene=FullVehicleScene(doc);old.scene.enter()
        old.session=Session(doc)
        old._rv_registry_revision=REGISTRY_REVISION
        existing=[old.list.item(i).data(QtCore.Qt.UserRole) for i in range(old.list.count())]
        if existing!=[clip.id for clip in old.session.clips]:
            old.list.clear()
            for clip in old.session.clips:
                item=Q.QListWidgetItem(clip.title,old.list)
                item.setData(QtCore.Qt.UserRole,clip.id)
                item.setFlags(item.flags()|QtCore.Qt.ItemIsUserCheckable)
                item.setCheckState(QtCore.Qt.Checked)
        for i,clip in enumerate(old.session.clips):old.list.item(i).setText(clip.title)
        if not getattr(old,'save_guard',None):
            old.save_guard=SaveGuard(old)
        old.status.setText(f'演示已就绪：播放时应用 {len(old.scene.baseline)} 个对象显隐状态、{len(old.session.clips)} 项动作。')
        old.show();old.raise_();old.activateWindow();old.setFocus(QtCore.Qt.OtherFocusReason)
        return old
    panel=DemoPanel(doc,main);main._rv_all_demos=panel
    main.addDockWidget(QtCore.Qt.RightDockWidgetArea,panel);panel.show()
    return panel

def open_panel_deferred():
    """Leave FreeCAD's Python macro tracer before constructing the GUI/model."""
    import FreeCADGui as Gui
    main=Gui.getMainWindow()
    if getattr(main,'_rv_all_demos_open_pending',False):return
    main._rv_all_demos_open_pending=True
    def open_when_idle():
        try:show_panel()
        except Exception as exc:App.Console.PrintError('整车演示未能打开：'+str(exc)+'\n')
        finally:main._rv_all_demos_open_pending=False
    QtCore.QTimer.singleShot(0,open_when_idle)
