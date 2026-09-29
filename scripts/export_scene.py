"""Export A27 geometry, CAD stage samples, and exact cabinet hinges; never save CAD."""
from pathlib import Path
import collections
import hashlib
import importlib.util
import json
import math
import struct
import sys
import traceback

import FreeCAD as A
import FreeCADGui as Gui
import MeshPart


ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "freecad/RV_AllDemos/animation_core.py"
(ROOT / "public").mkdir(parents=True, exist_ok=True)


def load_session():
    spec = importlib.util.spec_from_file_location("_rv_web_animation", PLAYER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run():
    doc = A.ActiveDocument
    assert doc and doc.getObject("AP_FridgeSwing") and doc.getObject("BT_Study")
    model = Path(doc.FileName)
    before = hashlib.sha256(model.read_bytes()).hexdigest()
    original_modified = getattr(doc, "Modified", None)
    # Resolve all saved expressions once before taking the immutable baseline.
    # The document is closed without saving after export.
    doc.recompute()
    ancestors = {}
    skipped = []

    def parents(obj, seen=None):
        seen = set() if seen is None else seen
        for parent in obj.InList:
            if (
                hasattr(parent, "Group")
                and obj in parent.Group
                and parent.Name not in seen
            ):
                seen.add(parent.Name)
                parents(parent, seen)
        return seen

    def visible(obj):
        return bool(obj.ViewObject.Visibility) and all(
            doc.getObject(name).ViewObject.Visibility
            for name in ancestors[obj.Name]
        )

    def category(obj):
        name = obj.Name
        tree = ancestors[name]
        if (
            name.startswith(
                (
                    "TL_",
                    "SS_Upper",
                    "SS_Cross",
                    "SS_Transport",
                    "SS_Use",
                    "SS_Ball",
                    "SS_Caster",
                )
            )
            or "TL_Ladder" in tree
        ):
            return "ladder"
        if "OverheadCabinets" in tree or name.startswith(("OH_", "SS_OH_")):
            return "overhead"
        if (
            "AreaOffice" in tree
            or "KT_KeyboardTray" in tree
            or "CC_Chair" in tree
        ):
            return "office"
        if "M12_Sofa" in tree or name.startswith(("S27_", "SB_")):
            return "sofa"
        if "SS_DirectStow" in tree or name.startswith(
            ("IC_", "SS_SL_", "SS_ED_", "TS_")
        ):
            return "cabinet"
        if "AreaWet" in tree or name.startswith("BD_"):
            return "wet"
        if "AreaCab" in tree or name.startswith(("RS_", "PS_")):
            return "cab"
        return "structure"

    def is_leaf(obj):
        if not visible(obj) and obj.Name != "BodyReference001":
            return False
        if obj.Name.startswith(
            ("X_Axis", "Y_Axis", "Z_Axis", "XY_Plane", "XZ_Plane", "YZ_Plane")
        ):
            return False
        is_body = obj.TypeId == "PartDesign::Body"
        if not is_body and (
            hasattr(obj, "Group")
            or any(
                doc.getObject(parent).TypeId == "PartDesign::Body"
                for parent in ancestors[obj.Name]
            )
        ):
            return False
        if not is_body and obj.TypeId.startswith(
            ("Sketcher::", "PartDesign::", "TechDraw::")
        ):
            return False
        has_shape = hasattr(obj, "Shape") and not obj.Shape.isNull()
        has_mesh = hasattr(obj, "Mesh") and obj.Mesh.CountFacets > 0
        return has_shape or has_mesh

    def world_shape(obj):
        shape = obj.Shape.copy()
        transform = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        shape.Placement = transform.multiply(shape.Placement)
        return shape

    def world_mesh(obj):
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            shape = world_shape(obj)
            mesh = MeshPart.meshFromShape(
                Shape=shape,
                LinearDeflection=0.8,
                AngularDeflection=0.35,
                Relative=False,
            )
            return mesh.Topology
        mesh = obj.Mesh.copy()
        transform = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        mesh.transform(transform.toMatrix())
        return mesh.Topology

    def object_matrix(obj):
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            transform = (
                obj.getGlobalPlacement()
                .multiply(obj.Placement.inverse())
                .multiply(obj.Shape.Placement)
            )
        else:
            transform = obj.getGlobalPlacement().multiply(obj.Placement.inverse())
        origin = transform.multVec(A.Vector())
        axes = [
            transform.multVec(A.Vector(1, 0, 0)) - origin,
            transform.multVec(A.Vector(0, 0, 1)) - origin,
            transform.multVec(A.Vector(0, -1, 0)) - origin,
        ]
        web_axes = [[axis.x, axis.z, -axis.y] for axis in axes]
        matrix = [
            web_axes[0][0], web_axes[0][1], web_axes[0][2], 0,
            web_axes[1][0], web_axes[1][1], web_axes[1][2], 0,
            web_axes[2][0], web_axes[2][1], web_axes[2][2], 0,
            origin.x * 0.001, origin.z * 0.001, -origin.y * 0.001, 1,
        ]
        return [round(value, 7) for value in matrix]

    def local_state(obj):
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            vertices, triangles = world_mesh(obj)
            return {
                "vertices": web_points(vertices),
                "triangles": [list(triangle) for triangle in triangles],
                "matrix": [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                "geometry_hash": None,
            }
        shape = obj.Shape.copy()
        shape.Placement = A.Placement()
        mesh = MeshPart.meshFromShape(
            Shape=shape,
            LinearDeflection=0.8,
            AngularDeflection=0.35,
            Relative=False,
        )
        vertices, triangles = mesh.Topology
        return {
            "vertices": web_points(vertices),
            "triangles": [list(triangle) for triangle in triangles],
            "matrix": object_matrix(obj),
            "geometry_hash": shape.hashCode(),
        }

    def web_points(vertices):
        points = []
        for vertex in vertices:
            values = (vertex.x, vertex.z, -vertex.y)
            if any(not math.isfinite(value) or abs(value) > 1e7 for value in values):
                raise ValueError("invalid unbounded tessellation")
            points.append([round(value * 0.001, 6) for value in values])
        return points

    def signature(obj):
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            shape = obj.Shape.copy()
            shape.Placement = A.Placement()
            return (
                tuple(object_matrix(obj)),
                shape.hashCode(),
                len(shape.Vertexes),
                len(shape.Edges),
                len(shape.Faces),
                round(shape.Volume, 3),
            )
        matrix = obj.getGlobalPlacement().toMatrix().A
        return (
            tuple(round(value, 5) for value in matrix),
            obj.Mesh.CountPoints,
            obj.Mesh.CountFacets,
        )

    def material(obj):
        view = obj.ViewObject
        materials = getattr(view, "ShapeAppearance", [])
        color = (
            list(materials[0].DiffuseColor)[:3]
            if materials
            else list(getattr(view, "ShapeColor", (0.7, 0.7, 0.65)))[:3]
        )
        opacity = 1 - float(getattr(view, "Transparency", 0)) / 100
        return color, opacity

    for obj in doc.Objects:
        ancestors[obj.Name] = parents(obj)
    leaves = [obj for obj in doc.Objects if is_leaf(obj)]
    motion_module = load_session()
    living_module = motion_module.load("_rv_web_living", PLAYER.parent / "living_motion.py")
    # Consistent web start: office ready, doors closed, ladder in its cabinet.
    # The saved CAD had bed progress=100 but its MIDI tray still extended.
    # Only this disposable export document is normalized; the source is not saved.
    living_module.state(doc, 0)
    doc.BD_Control.OpenPercent = 0
    doc.TL_Control.Progress = 100
    for name in ["OH_L01", "OH_L02", "OH_L03", "OH_L04", "OH_L05", "OH_K01", "SS_OH_E01", "OH_E02", "SS_ED_Upper", "AP_WasherSwing", "AP_FridgeSwing", "WD_LeftDoor"]:
        if doc.getObject(name): doc.getObject(name).OpenAngle = 0
    doc.recompute()
    session = motion_module.Session(doc)
    action_labels = {
        "living": "工作台、MIDI 与沙发成床", "bath": "卫浴卷门",
        "OH_L01": "左柜 L01", "OH_L02": "左柜 L02", "OH_L03": "左柜 L03",
        "OH_L04": "左柜 L04", "OH_L05": "左柜 L05", "OH_K01": "厨房 K01",
        "SS_OH_E01": "端仓 E01", "OH_E02": "端仓 E02",
        "SS_ED_Upper": "入口上柜", "SS_ED_Middle": "入口下柜", "upright_ladder": "直推藏梯",
        "AP_WasherSwing": "洗衣机门", "AP_FridgeSwing": "42 L 冰箱门", "WD_LeftDoor": "洗衣液收纳柜门",
    }
    stage_defs = {
        "living": [(0, "琴托与 MIDI 收回"), (15, "办公椅收入桌下"), (30, "解锁沙发"),
                   (36, "沙发排条与落地腿展开"), (65, "提起补垫"), (72, "移开补垫"),
                   (80, "补垫转平"), (90, "补垫移至床架"), (95, "补垫落下"), (100, "床位展示")],
        "upright_ladder": [(0, "退出使用锁销"), (5, "锁座回缩"), (10, "踏板收齐"),
                           (25, "整梯直立并缩短"), (65, "滚珠脚接地"), (70, "横推入柜，上轨回缩"),
                           (95, "关门并锁止"), (100, "柜内收妥")],
    }
    action_changes, action_rows = {}, []
    motion_data = {"schema": 2, "modelHash": before, "actions": {}}
    base_meshes = {}
    reference_names = {"BodyReference001"}
    reference_rows = []
    for obj in leaves:
        if obj.Name in reference_names:
            continue
        try:
            vertices, triangles = world_mesh(obj)
            if not vertices or not triangles:
                skipped.append({"name": obj.Name, "reason": "empty tessellation"})
                continue
            base_meshes[obj.Name] = {
                "vertices": web_points(vertices),
                "triangles": [list(triangle) for triangle in triangles],
                "local": local_state(obj),
            }
        except Exception as error:
            skipped.append({"name": obj.Name, "reason": str(error)})

    target_meshes = collections.defaultdict(dict)
    export_checks = {"hinges": [], "cadSamples": {}}
    for clip in session.clips:
        session.restore()
        session.changed_keys.update(key for key in clip.keys if key in session.snapshot)
        cabinet = clip.id.startswith(("OH_", "SS_OH_", "SS_ED_")) or clip.id in {"AP_WasherSwing", "AP_FridgeSwing", "WD_LeftDoor"}
        speed = 6 if cabinet else 5
        initial = 100 if clip.id == "upright_ladder" else 0
        maximum = (float(getattr(doc.getObject(clip.id), "DemoMaxAngle", 90)) if clip.id in {"AP_WasherSwing", "AP_FridgeSwing", "WD_LeftDoor"} else 90 if clip.id.startswith("SS_ED_") else 86)
        matrices = {name: [] for name in base_meshes}
        samples = [0, 50, 100] if cabinet else [i / 2 for i in range(201)]
        geometry_frames = []
        morph_end = None
        group = doc.getObject(clip.id) if cabinet else None
        if group:
            placement = group.getGlobalPlacement()
            # Derive the signed WORLD hinge from CAD, including mirrored doors.
            # At zero angle FreeCAD's Rotation.Axis is ambiguous.
            group.OpenAngle = 1
            doc.recompute()
            delta = group.getGlobalPlacement().multiply(placement.inverse())
            axis = delta.Rotation.Axis
            degrees_per_unit = (math.degrees(delta.Rotation.Angle) + 180) % 360 - 180
            # FreeCAD may encode a -1 degree step as +359 around the same axis.
            assert abs(abs(degrees_per_unit)-1) < 1e-6, "Unexpected hinge ratio"
            hinge = {"pivot": web_points([placement.Base])[0],
                     "axis": [axis.x, axis.z, -axis.y], "degrees": maximum * degrees_per_unit}
            group.OpenAngle = 0
            doc.recompute()

        def pose(progress):
            if clip.id == "living":
                living_module.state(doc, progress)
            elif clip.id == "upright_ladder":
                doc.TL_Control.Progress = progress
            elif clip.id == "bath":
                doc.BD_Control.OpenPercent = progress
            else:
                group.OpenAngle = maximum * progress / 100
            doc.recompute()

        for progress in samples:
            pose(progress)
            for name in base_meshes:
                obj = doc.getObject(name)
                matrices[name].append(object_matrix(obj) if hasattr(obj, "Shape") else base_meshes[name]["local"]["matrix"])
            if clip.id == "bath" and progress % 5 == 0:
                roll = local_state(doc.BD_Roll)
                geometry_frames.append({"at": progress, "vertices": roll["vertices"], "triangles": roll["triangles"]})
            if clip.id == "bath" and progress == 100:
                morph_end = local_state(doc.BD_Screen)
            if progress in (0, 5, 10, 15, 25, 30, 36, 50, 65, 70, 72, 80, 90, 95, 100):
                fields = {}
                for name, props in {
                    "KT_Moving": ["PullOut"], "CC_Control": ["ChairY"], "S27_Params": ["Travel"],
                    "TL_Control": ["Tilt", "TreadAngle", "SideTravel", "PocketDoorOpen", "TransportLock", "StagePitch", "RollerMode"],
                }.items():
                    obj = doc.getObject(name)
                    fields[name] = {prop: motion_module.number(getattr(obj, prop)) for prop in props if prop in obj.PropertiesList}
                export_checks["cadSamples"].setdefault(clip.id, []).append({"progress": progress, "controls": fields})
        tracks = {}
        for name, values in matrices.items():
            base = base_meshes[name]["local"]
            changed = any(max(abs(a-b) for a,b in zip(value, base["matrix"])) > 1e-7 for value in values)
            is_screen = clip.id == "bath" and name == "BD_Screen"
            is_roll = clip.id == "bath" and name == "BD_Roll"
            if not (changed or is_screen or is_roll):
                continue
            track = {"frames": [{"at": progress, "matrix": value} for progress, value in zip(samples, values)]}
            vertices = None
            if cabinet:
                track = {"hinge": hinge, "baseMatrix": base["matrix"]}
                export_checks["hinges"].append({"action": clip.id, "object": name, "hinge": hinge, "baseMatrix": base["matrix"],
                                               "samples": [{"progress": progress, "matrix": value} for progress, value in zip(samples, values)]})
            if is_screen:
                assert base["triangles"] == morph_end["triangles"], "screen topology changed"
                vertices = morph_end["vertices"]
                track["morph"] = 0
            if is_roll:
                track["geometryFrames"] = geometry_frames
            tracks[name] = track
            target_meshes[name][clip.id] = {"matrix": values[-1], "vertices": vertices}
        action_changes[clip.id] = list(tracks)
        motion_data["actions"][clip.id] = {
            "baselineProgress": initial, "tracks": tracks, "interaction": "door" if cabinet else "cycle",
            "stages": [{"at": at, "label": label} for at, label in stage_defs.get(clip.id, [(0, "关闭"), (100, "开启")])],
        }
        action_rows.append({"id": clip.id, "label": action_labels.get(clip.id, clip.title),
                            "title": clip.title, "duration": clip.duration / speed,
                            "sourceDuration": clip.duration, "speed": speed, "objects": len(tracks), "interaction": "door" if cabinet else "cycle"})
        print("CAD_MOTION_SAMPLED", clip.id, len(tracks), flush=True)
        (ROOT / "export-progress.json").write_text(json.dumps({"lastAction":clip.id,"completed":len(action_rows),"total":len(session.clips)}))
        session.restore()
    animated_names = set(target_meshes)
    grouped = {}
    rows = []
    all_points = []

    def add_static(zone, color, mode, vertices, triangles, opacity=1):
        if not vertices or not triangles:
            return
        key = (
            zone,
            tuple(round(float(value), 3) for value in color[:3]),
            round(opacity, 2),
            mode,
        )
        batch = grouped.setdefault(key, {"v": [], "i": []})
        base = len(batch["v"])
        points = web_points(vertices)
        batch["v"].extend(points)
        all_points.extend(points)
        batch["i"].extend(base + index for tri in triangles for index in tri)

    for obj in leaves:
        if obj.Name in reference_names:
            shape = world_shape(obj)
            edges, indices = [], []
            for edge in shape.Edges:
                points = edge.discretize(Deflection=1.2)
                if len(points) > 96:
                    points = edge.discretize(Number=96)
                offset = len(edges)
                edges.extend(points)
                indices.extend((offset + i, offset + i + 1) for i in range(len(points) - 1))
            if indices:
                add_static("cabover_reference", [0.18, 0.28, 0.28], 1, edges, indices, 0.78)
                reference_rows.append({"name": obj.Name, "label": obj.Label, "edges": len(shape.Edges), "segments": len(indices)})
                rows.append({"name": obj.Name, "label": obj.Label, "zone": "cabover_reference", "triangles": 0, "animated": False, "actions": []})
            continue
        if obj.Name not in base_meshes:
            continue
        zone = category(obj)
        color, opacity = material(obj)
        base = base_meshes[obj.Name]
        triangles = len(base["triangles"])
        if obj.Name not in animated_names:
            add_static(
                zone,
                color,
                4,
                [A.Vector(p[0] * 1000, -p[2] * 1000, p[1] * 1000) for p in base["vertices"]],
                base["triangles"],
                opacity,
            )
            if hasattr(obj, "Shape") and not obj.Shape.isNull():
                edges = []
                indices = []
                for edge in world_shape(obj).Edges:
                    points = edge.discretize(Deflection=1.2)
                    if len(points) > 48:
                        points = edge.discretize(Number=48)
                    offset = len(edges)
                    edges.extend(points)
                    indices.extend(
                        (offset + index, offset + index + 1)
                        for index in range(len(points) - 1)
                    )
                add_static(zone, [0.13, 0.2, 0.2], 1, edges, indices, 0.42)
        all_points.extend(base["vertices"])
        rows.append(
            {
                "name": obj.Name,
                "label": obj.Label,
                "zone": zone,
                "triangles": triangles,
                "animated": obj.Name in animated_names,
                "actions": sorted(target_meshes.get(obj.Name, {})),
            }
        )

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "A27 FreeCAD activity export",
        },
        "scene": 0,
        "scenes": [{"nodes": []}],
        "nodes": [],
        "meshes": [],
        "materials": [],
        "buffers": [{}],
        "bufferViews": [],
        "accessors": [],
    }
    blob = bytearray()

    def accessor(values, component_type, value_type, include_bounds=False):
        while len(blob) % 4:
            blob.append(0)
        offset = len(blob)
        if value_type == "VEC3":
            flat = [component for value in values for component in value]
            blob.extend(struct.pack("<%sf" % len(flat), *flat))
        else:
            blob.extend(struct.pack("<%sI" % len(values), *values))
        view = len(gltf["bufferViews"])
        gltf["bufferViews"].append(
            {
                "buffer": 0,
                "byteOffset": offset,
                "byteLength": len(blob) - offset,
            }
        )
        item = {
            "bufferView": view,
            "componentType": component_type,
            "count": len(values),
            "type": value_type,
        }
        if value_type == "VEC3" and include_bounds:
            item.update(
                min=[min(value[index] for value in values) for index in range(3)],
                max=[max(value[index] for value in values) for index in range(3)],
            )
        index = len(gltf["accessors"])
        gltf["accessors"].append(item)
        return index

    def add_material(color, alpha, zone):
        linear = [
            value / 12.92
            if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
            for value in color
        ]
        item = {
            "name": zone,
            "pbrMetallicRoughness": {
                "baseColorFactor": [*linear, alpha],
                "metallicFactor": 0.05,
                "roughnessFactor": 0.72,
            },
            "doubleSided": True,
        }
        if alpha < 1:
            item["alphaMode"] = "BLEND"
        index = len(gltf["materials"])
        gltf["materials"].append(item)
        return index

    for (zone, color, alpha, mode), batch in grouped.items():
        position = accessor(batch["v"], 5126, "VEC3", True)
        indices = accessor(batch["i"], 5125, "SCALAR")
        material_index = add_material(color, alpha, zone)
        mesh_index = len(gltf["meshes"])
        gltf["meshes"].append(
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": position},
                        "indices": indices,
                        "material": material_index,
                        "mode": mode,
                    }
                ]
            }
        )
        node_index = len(gltf["nodes"])
        gltf["nodes"].append(
            {
                "mesh": mesh_index,
                "name": zone + ("_edges" if mode == 1 else ""),
                "extras": {"zone": zone, "outline": mode == 1},
            }
        )
        gltf["scenes"][0]["nodes"].append(node_index)

    morph_objects = 0
    for name in sorted(animated_names):
        obj = doc.getObject(name)
        base = base_meshes[name]["local"]
        action_targets = target_meshes[name]
        if not action_targets:
            continue
        color, alpha = material(obj)
        position = accessor(base["vertices"], 5126, "VEC3", True)
        indices = accessor(
            [index for tri in base["triangles"] for index in tri],
            5125,
            "SCALAR",
        )
        targets = []
        motions = {}
        for action_id, active in sorted(action_targets.items()):
            active_vertices = active["vertices"]
            morph_index = None
            if active_vertices is not None:
                morph_index = len(targets)
                deltas = [
                    [
                        round(active_vertex[index] - original[index], 6)
                        for index in range(3)
                    ]
                    for original, active_vertex in zip(
                        base["vertices"], active_vertices
                    )
                ]
                targets.append({"POSITION": accessor(deltas, 5126, "VEC3")})
            motions[action_id] = {
                "matrix": active["matrix"],
                "morph": morph_index,
            }
        material_index = add_material(color, alpha, category(obj))
        mesh_index = len(gltf["meshes"])
        primitive = {
            "attributes": {"POSITION": position},
            "indices": indices,
            "material": material_index,
            "mode": 4,
        }
        if targets:
            primitive["targets"] = targets
        mesh_item = {
            "primitives": [primitive],
            "extras": {"motions": motions},
        }
        if targets:
            mesh_item["weights"] = [0] * len(targets)
        gltf["meshes"].append(
            mesh_item
        )
        node_index = len(gltf["nodes"])
        gltf["nodes"].append(
            {
                "mesh": mesh_index,
                "name": name,
                "matrix": base["matrix"],
                "extras": {
                    "zone": category(obj),
                    "object": name,
                    "motions": motions,
                },
            }
        )
        gltf["scenes"][0]["nodes"].append(node_index)
        morph_objects += 1

    assert rows and all_points and action_rows and morph_objects
    gltf["buffers"][0]["byteLength"] = len(blob)
    json_chunk = json.dumps(gltf, separators=(",", ":")).encode()
    json_chunk += b" " * (-len(json_chunk) % 4)
    blob += b"\0" * (-len(blob) % 4)
    glb = (
        struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_chunk) + 8 + len(blob))
        + struct.pack("<II", len(json_chunk), 0x4E4F534A)
        + json_chunk
        + struct.pack("<II", len(blob), 0x004E4942)
        + blob
    )
    (ROOT / "public/rv-a27.glb").write_bytes(glb)

    motion_bytes = json.dumps(motion_data, ensure_ascii=False, separators=(",", ":")).encode()
    (ROOT / "public/motion-data.json").write_bytes(motion_bytes)
    (ROOT / "motion-export-checks.json").write_text(json.dumps(export_checks, ensure_ascii=False))
    previous_info = json.loads((ROOT / "public/model-info.json").read_text())
    orientation = Gui.activeDocument().activeView().getCameraOrientation()
    direction = orientation.multVec(A.Vector(0, 0, 1))
    lo = [min(point[index] for point in all_points) for index in range(3)]
    hi = [max(point[index] for point in all_points) for index in range(3)]
    metadata = {
        "version": "A27 R7",
        "revision": "20260929-r7-right-battery-doors",
        "parts": len(rows),
        "triangles": sum(row["triangles"] for row in rows),
        "bytes": len(glb),
        "bounds": [lo, hi],
        "cameraDirection": previous_info["cameraDirection"],
        "zones": dict(collections.Counter(row["zone"] for row in rows)),
        "modelHash": before,
        "assetHash": hashlib.sha256(glb).hexdigest(),
        "motionHash": hashlib.sha256(motion_bytes).hexdigest(),
        "motionSchema": 2,
        "status": "模型展示",
        "batteryBay": "沙发车外侧视图右半段，对应已有外舱门；保留床架",
        "batteryBoundsMm": [2055,-793.1,745,2700,-610.9,1009],
        "actions": action_rows,
        "animatedObjects": morph_objects,
        "referenceLines": reference_rows,
    }
    (ROOT / "public/model-info.json").write_text(
        json.dumps(metadata, ensure_ascii=False)
    )
    source_unchanged = before == hashlib.sha256(model.read_bytes()).hexdigest()
    report = {
        "metadata": metadata,
        "source": str(model),
        "sourceUnchanged": source_unchanged,
        "modifiedBefore": original_modified,
        "modifiedAfter": getattr(doc, "Modified", None),
        "objects": rows,
        "actionChanges": action_changes,
        "skipped": skipped,
    }
    (ROOT / "export-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2)
    )
    assert source_unchanged
    print("WEB_EXPORT_DONE", json.dumps(metadata, ensure_ascii=False))


try:
    run()
except Exception:
    (ROOT / "export-error.txt").write_text(traceback.format_exc())
    print(traceback.format_exc())
