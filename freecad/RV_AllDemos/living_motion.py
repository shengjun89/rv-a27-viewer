"""Pose driver for the office-chair and sofa-bed sequence."""
import FreeCAD as App


def number(value):
    return value.Value if hasattr(value, "Value") else float(value)


def ramp(progress, start, end):
    value = max(0.0, min(1.0, (progress - start) / (end - start)))
    return value * value * (3.0 - 2.0 * value)


def stage(progress, has_infill):
    if progress <= 0:
        return "使用位｜琴托展开、椅子在桌前、沙发收起"
    if progress < 15:
        return "琴托与MIDI收回"
    if progress < 30:
        return "办公椅收入桌下"
    if progress < 36:
        return "运输锁销上提50 mm｜锁销可达性待实配"
    if progress < 65:
        return "沙发排条与落地支腿抽出"
    if not has_infill:
        return "床架已展开｜软包厚度不匹配，补垫待定"
    if progress < 72:
        return "手动提起50 mm补垫候选"
    if progress < 80:
        return "手动移垫至空位"
    if progress < 90:
        return "补垫转平｜手动搬放，不是铰链机构"
    if progress < 95:
        return "补垫移至展开区"
    if progress < 100:
        return "补垫落到排条承托面"
    return "床位展示｜补垫候选；靠背保留，承载与实配待核"


def state(doc, progress):
    progress = max(0.0, min(100.0, float(progress)))
    control = doc.SB_Control
    doc.KT_Moving.PullOut = control.UseTray * (
        1.0 - ramp(progress, 0, 15)
    )
    doc.CC_Control.ChairY = (
        control.UseChairY
        + (control.StowChairY - control.UseChairY)
        * ramp(progress, 15, 30)
    )
    doc.CC_Control.SeatHeight = control.UseSeatHeight
    doc.CC_Control.SwivelAngle = control.UseSwivelAngle
    control.UnlockLift = 50.0 * ramp(progress, 30, 36)
    doc.S27_Params.Travel = (
        number(doc.S27_Params.MaxTravel) * ramp(progress, 36, 65)
    )
    control.Progress = progress

    infill = doc.getObject("SB_Infill")
    if infill:
        origin = App.Vector(control.PadX, control.PadY, control.PadZ)
        z_value = (
            origin.z
            + 80.0 * ramp(progress, 65, 72)
            - 80.0 * ramp(progress, 95, 100)
        )
        y_value = (
            origin.y
            + (-500.0 - origin.y) * ramp(progress, 72, 80)
            + (control.PadEndY + 500.0) * ramp(progress, 90, 95)
        )
        infill.Placement = App.Placement(
            App.Vector(origin.x, y_value, z_value),
            App.Rotation(
                App.Vector(1, 0, 0),
                -90.0 * ramp(progress, 80, 90),
            ),
        )

    control.Stage = stage(progress, bool(infill))
    doc.recompute()
    return control.Stage
