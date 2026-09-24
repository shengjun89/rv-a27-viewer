import * as THREE from 'three';

const smooth = (t) => {
  const v = THREE.MathUtils.clamp(t, 0, 1);
  return v * v * (3 - 2 * v);
};

// CAD's 8% lead-in, 37% travel, 10% hold, 37% return, 8% tail.
// A stored ladder starts at 100: reverse the cycle, not the order of its joints.
export function cycleProgress(time, baseline = 0) {
  let value = 0;
  if (time < 0.45) value = smooth((time - 0.08) / 0.37);
  else if (time < 0.55) value = 1;
  else if (time < 0.92) value = 1 - smooth((time - 0.55) / 0.37);
  return baseline + (100 - 2 * baseline) * value;
}

function transform(matrix) {
  const position = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  new THREE.Matrix4().fromArray(matrix).decompose(position, quaternion, scale);
  return { position, quaternion, scale };
}

export function prepareTrack(track) {
  if (track.hinge) {
    const pivot = new THREE.Vector3(...track.hinge.pivot);
    return {
      ...track,
      base: new THREE.Matrix4().fromArray(track.baseMatrix),
      pivot,
      axis: new THREE.Vector3(...track.hinge.axis).normalize(),
      toPivot: new THREE.Matrix4().makeTranslation(...pivot.toArray()),
      fromPivot: new THREE.Matrix4().makeTranslation(...pivot.clone().negate().toArray()),
    };
  }
  return { ...track, frames: track.frames.map((f) => ({ at: f.at, ...transform(f.matrix) })) };
}

const rotation = new THREE.Matrix4();
const matrix = new THREE.Matrix4();
export function sampleTransform(track, progress, object) {
  const p = THREE.MathUtils.clamp(progress, 0, 100);
  if (track.hinge) {
    rotation.makeRotationAxis(track.axis, THREE.MathUtils.degToRad(track.hinge.degrees * p / 100));
    matrix.copy(track.toPivot).multiply(rotation).multiply(track.fromPivot).multiply(track.base);
    matrix.decompose(object.position, object.quaternion, object.scale);
    return;
  }
  const frames = track.frames;
  let lo = 0;
  let hi = frames.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].at <= p) lo = mid;
    else hi = mid;
  }
  const a = frames[lo];
  const b = frames[hi];
  const mix = THREE.MathUtils.clamp((p - a.at) / (b.at - a.at || 1), 0, 1);
  object.position.lerpVectors(a.position, b.position, mix);
  object.quaternion.slerpQuaternions(a.quaternion, b.quaternion, mix);
  object.scale.lerpVectors(a.scale, b.scale, mix);
}

export function createCADMotion(model, data) {
  const objects = new Map();
  model.traverse((object) => {
    if (object.isMesh && object.userData.object) objects.set(object.userData.object, object);
  });
  const actions = new Map();
  for (const [id, action] of Object.entries(data.actions)) {
    const tracks = [];
    for (const [name, raw] of Object.entries(action.tracks)) {
      const object = objects.get(name);
      if (!object) throw new Error(`Missing CAD motion object: ${name}`);
      const track = prepareTrack(raw);
      if (track.geometryFrames) {
        track.geometries = track.geometryFrames.map((frame) => {
          const geometry = new THREE.BufferGeometry();
          geometry.setAttribute('position', new THREE.Float32BufferAttribute(frame.vertices.flat(), 3));
          geometry.setIndex(frame.triangles.flat());
          geometry.computeVertexNormals();
          geometry.computeBoundingBox();
          return { at: frame.at, geometry };
        });
      }
      tracks.push({ object, track });
    }
    actions.set(id, { ...action, tracks });
  }
  function apply(id, progress) {
    for (const { object, track } of actions.get(id).tracks) {
      sampleTransform(track, progress, object);
      if (track.morph !== undefined) object.morphTargetInfluences[track.morph] = progress / 100;
      if (track.geometries) {
        const index = Math.round(progress / 100 * (track.geometries.length - 1));
        object.geometry = track.geometries[index].geometry;
      }
    }
  }
  return {
    actions,
    apply,
    reset(id) { apply(id, actions.get(id).baselineProgress); },
    resetAll() { for (const id of actions.keys()) this.reset(id); },
  };
}
