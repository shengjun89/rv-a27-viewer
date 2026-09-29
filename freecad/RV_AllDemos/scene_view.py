"""Temporary full-vehicle presentation state for the A27 animation player."""
import json
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import FreeCAD as App

DOCUMENT_PREFS = "User parameter:BaseApp/Preferences/Document"
# R1 replaces these solid cabinet bodies with appliance installation bays.
# Keep the historical presentation baseline usable for earlier A27 documents.
APPLIANCE_REPLACED = {
    "P035", "P077", "SS_P268", "SS_P269", "SS_ED_Middle",
    "SS_ED_Middle_Panel", "SS_ED_Middle_Handle", "SS_SL_CabinetSide",
    "SS_P261", "SS_P262", "Body", "BaseFeature001",
}
PRESENTATION_HIDDEN = {
    "BodyReferences",
    "LayoutDrawings",
    "OfficialComparison",
}
PRESENTATION_SHOWN = {
    "SourceParts",
    "AreaCab",
    "AreaOffice",
    "AreaWet",
    "AreaEntry",
    "AreaLining",
    "RestoredSystems",
    "RS_Seats",
    "RS_Office",
    "RS_Entry",
    "RS_Overhead",
    "M12_Sofa",
    "KT_Moving",
    "CC_Chair",
    "BD_Door",
    "OH_L01",
    "OH_L02",
    "OH_L03",
    "OH_L04",
    "OH_L05",
    "OH_K01",
    "SS_OH_E01",
    "OH_E01",
    "OH_E02",
    "SS_ED_Upper",
    "SS_ED_Middle",
    "ED_Upper",
    "ED_Middle",
    "ED_Bottom",
    "TL_Ladder",
    "TS_SlopeDoor",
    "TS_FlatTop",
    "TS_OuterSide",
    "TS_RearPanel",
}


def document_visibility(path):
    with ZipFile(Path(path)) as archive:
        root = ElementTree.fromstring(archive.read("GuiDocument.xml"))
    result = {}
    for provider in root.findall("./ViewProviderData/ViewProvider"):
        value = provider.find("./Properties/Property[@name='Visibility']/Bool")
        if value is not None:
            result[provider.attrib["name"]] = value.attrib.get("value") == "true"
    if not result:
        raise RuntimeError("工程文件中没有可用的整车显隐基线。")
    return result


def saved_visibility(path):
    """Combine the clean A27 baseline with objects added in later revisions."""
    current = document_visibility(path)
    baseline_path = Path(__file__).with_name("full_vehicle_visibility.json")
    if not baseline_path.is_file():
        return current
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline = dict(data["visibility"])
    baseline.update(
        (name, visible)
        for name, visible in current.items()
        if name not in baseline
    )
    return baseline


class FullVehicleScene:
    """Apply the saved full-vehicle scene and later restore the user's view."""

    def __init__(self, doc):
        self.doc = doc
        self.name = doc.Name
        self.baseline = saved_visibility(doc.FileName)
        for name in PRESENTATION_SHOWN:
            if name in self.baseline:
                self.baseline[name] = True
        pending = [
            self.doc.getObject(name)
            for name in PRESENTATION_SHOWN
            if self.doc.getObject(name) is not None
        ]
        seen = set()
        while pending:
            obj = pending.pop()
            if obj.Name in seen:
                continue
            seen.add(obj.Name)
            for parent in obj.InList:
                if hasattr(parent, "Group") and obj in parent.Group:
                    if parent.Name in self.baseline:
                        self.baseline[parent.Name] = True
                    pending.append(parent)
        for name in PRESENTATION_HIDDEN:
            if name in self.baseline:
                self.baseline[name] = False
        if self.doc.getObject("AP_R1") is not None:
            for name in APPLIANCE_REPLACED:
                if name in self.baseline:
                    self.baseline[name] = False
            self.baseline["AP_R1"] = True
        # Recessed floor and exterior trim supersede the intact historical solids.
        for replacement, original in [("BT_RecessedFloor", "S27_014"), ("BT_RearFixedPanel", "S27_011")]:
            if self.doc.getObject(replacement) is not None:
                self.baseline[original] = False
        self.active = False
        self.visibility = {}
        self.applied_count = 0
        self.autosave_enabled = None
        self.transaction_open = False

    def alive(self):
        return App.listDocuments().get(self.name) is self.doc

    def ordered(self, state):
        depths = {}

        def depth(name, visiting=None):
            if name in depths:
                return depths[name]
            visiting = set() if visiting is None else set(visiting)
            if name in visiting:
                return 0
            visiting.add(name)
            obj = self.doc.getObject(name)
            if obj is None:
                return 0
            parents = [
                parent
                for parent in obj.InList
                if hasattr(parent, "Group") and obj in parent.Group
            ]
            value = 0 if not parents else 1 + max(
                depth(parent.Name, visiting) for parent in parents
            )
            depths[name] = value
            return value

        return sorted(state.items(), key=lambda item: depth(item[0]))

    def enter(self):
        if not self.alive():
            raise RuntimeError("工程已关闭；请重新打开演示面板。")
        if not self.active:
            self.visibility = {
                obj.Name: bool(obj.ViewObject.Visibility)
                for obj in self.doc.Objects
                if hasattr(obj, "ViewObject")
                and hasattr(obj.ViewObject, "Visibility")
            }
            preferences = App.ParamGet(DOCUMENT_PREFS)
            self.autosave_enabled = preferences.GetBool("AutoSaveEnabled", False)
            if self.autosave_enabled:
                preferences.SetBool("AutoSaveEnabled", False)
            self.doc.openTransaction("A27 full-vehicle presentation")
            self.transaction_open = True
            self.active = True

        self.applied_count = 0
        for name, visible in self.ordered(self.baseline):
            obj = self.doc.getObject(name)
            if (
                obj is not None
                and hasattr(obj, "ViewObject")
                and hasattr(obj.ViewObject, "Visibility")
            ):
                obj.ViewObject.Visibility = visible
                self.applied_count += 1

        return self.applied_count

    def restore(self):
        if not self.active:
            return
        try:
            if not self.alive():
                return
            if self.transaction_open:
                self.doc.abortTransaction()
                self.doc.recompute()
                self.transaction_open = False
            for name, visible in self.ordered(self.visibility):
                obj = self.doc.getObject(name)
                if (
                    obj is not None
                    and hasattr(obj, "ViewObject")
                    and hasattr(obj.ViewObject, "Visibility")
                    and bool(obj.ViewObject.Visibility) != visible
                ):
                    obj.ViewObject.Visibility = visible
        finally:
            if self.autosave_enabled is not None:
                App.ParamGet(DOCUMENT_PREFS).SetBool(
                    "AutoSaveEnabled", self.autosave_enabled
                )
                self.autosave_enabled = None
            self.active = False
            self.transaction_open = False
            self.visibility = {}
