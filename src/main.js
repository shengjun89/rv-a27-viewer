import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createCADMotion, cycleProgress } from './cad-motion.js';
import { createGhostMode, createElectricalOverlay } from './electrical.js';
import { createInverter } from './inverter.js';

const $ = (id) => document.getElementById(id);
const host = $('viewer');
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
let renderer, camera, scene, controls, model, info, cadMotion;
let electricalOverlay, ghostMode;
let electricalVisible = false;
let demoPanelWasOpen = true;
let frame = 0;
let motion = null;
let activeAction = null;
let playlist = [];
let pausedAt = null;
let topView = false;
const actionMeshes = new Map();
const motionNodes = new Map();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
let pointerStart = null;
const status = {
  ready: false,
  electricalVisible: false,
  contextOpacity: null,
  activeAction: null,
  transitioning: false,
  actions: 0,
  renderedFrames: 0,
  referenceLineSegments: 0,
  controlProgress: null,
  stage: null,
  duration: null,
  playlistRemaining: 0,
  paused: false,
  revision: null,
};

Object.defineProperty(window, 'viewerStatus', {
  get: () => ({
    ...status,
    camera: camera?.position.toArray(),
    drawCalls: renderer?.info.render.calls,
    triangles: renderer?.info.render.triangles,
    actionMeshes: Object.fromEntries(
      [...actionMeshes].map(([id, items]) => [id, items.length]),
    ),
    activeMotionDelta: getActiveMotionDelta(),
    pickTargets: getPickTargets(),
  }),
});

function getActiveMotionDelta() {
  let maximum = 0;
  for (const node of motionNodes.values()) {
    maximum = Math.max(
      maximum,
      node.mesh.position.distanceTo(node.base.position),
      node.mesh.quaternion.angleTo(node.base.quaternion),
      ...(node.mesh.morphTargetInfluences || []),
    );
  }
  return maximum;
}

function getPickTargets() {
  if (!status.ready || !renderer || !model) return {};
  const rect = renderer.domElement.getBoundingClientRect();
  const result = {};
  for (const [actionId, items] of actionMeshes) {
    for (const item of items) {
      const box = item.mesh.geometry.boundingBox ||
        (item.mesh.geometry.computeBoundingBox(), item.mesh.geometry.boundingBox);
      const center = box.getCenter(new THREE.Vector3());
      item.mesh.localToWorld(center);
      center.project(camera);
      if (Math.abs(center.x) > 1 || Math.abs(center.y) > 1) continue;
      raycaster.setFromCamera(new THREE.Vector2(center.x, center.y), camera);
      const hit = raycaster
        .intersectObject(model, true)
        .find((entry) =>
          Object.keys(entry.object.userData.motions || {}).includes(actionId),
        );
      if (!hit) continue;
      result[actionId] = {
        x: rect.left + (center.x + 1) * rect.width / 2,
        y: rect.top + (1 - center.y) * rect.height / 2,
      };
      break;
    }
  }
  return result;
}

function requestRender() {
  if (!frame && renderer) frame = requestAnimationFrame(render);
}

function render(time) {
  frame = 0;
  let keepRendering = false;
  if (motion && pausedAt === null) {
    const raw = Math.min(1, Math.max(0, (time - motion.started) / motion.duration));
    const action = cadMotion.actions.get(motion.actionId);
    const eased = raw * raw * (3 - 2 * raw);
    const progress = motion.segment
      ? motion.fromProgress + (motion.toProgress - motion.fromProgress) * eased
      : motion.returning
      ? motion.fromProgress + (action.baselineProgress - motion.fromProgress) * eased
      : cycleProgress(raw, action.baselineProgress);
    cadMotion.apply(motion.actionId, progress);
    status.controlProgress = progress;
    status.stage = [...action.stages].reverse().find((stage) => stage.at <= progress)?.label;
    if (raw >= 1) {
      const queued = motion.queued;
      const holdOpen = motion.segment && motion.toProgress === 100;
      if (!holdOpen) cadMotion.reset(motion.actionId);
      activeAction = holdOpen ? motion.actionId : null;
      motion = null;
      status.activeAction = activeAction;
      status.transitioning = false;
      if (queued) startAction(queued);
      else if (playlist.length) startAction(playlist.shift(), true);
    }
    keepRendering = Boolean(motion);
  }
  status.playlistRemaining = playlist.length;
  status.paused = pausedAt !== null;
  updatePlaybackUI();
  controls.update();
  renderer.render(scene, camera);
  status.renderedFrames += 1;
  if (keepRendering) requestRender();
}

function isCabinetAction(actionId) {
  return cadMotion?.actions.get(actionId)?.interaction === 'door' || /^(OH_|SS_OH_|SS_ED_)/.test(actionId);
}

function startAction(actionId, fullCycle = false) {
  pausedAt = null;
  const action = cadMotion.actions.get(actionId);
  activeAction = actionId;
  status.activeAction = actionId;
  status.controlProgress = action.baselineProgress;
  status.duration = info.actions.find((item) => item.id === actionId).duration;
  const cabinet = !fullCycle && isCabinetAction(actionId);
  motion = {
    actionId,
    segment: cabinet,
    fromProgress: 0,
    toProgress: 100,
    started: performance.now(),
    // CAD's actual opening stroke occupies 37% of its original round trip.
    duration: reducedMotion ? 1 : status.duration * (cabinet ? 370 : 1000),
  };
  status.transitioning = true;
  requestRender();
}

function setAction(actionId) {
  if (!status.ready || !actionMeshes.has(actionId)) return;
  playlist = [];
  if (pausedAt !== null && motion) { motion.started += performance.now() - pausedAt; pausedAt = null; }
  // A tap starts exactly one cabinet stroke. Ignore re-entry until it settles.
  if (motion && isCabinetAction(motion.actionId)) return;
  if (activeAction) {
    // Restore along the same CAD sequence before playing another system.
    // Never blend unrelated world-space endpoints through furniture.
    const row = info.actions.find((item) => item.id === activeAction);
    const baseline = cadMotion.actions.get(activeAction).baselineProgress;
    const progress = status.controlProgress ?? baseline;
    motion = {
      actionId: activeAction,
      returning: true,
      segment: isCabinetAction(activeAction),
      toProgress: 0,
      fromProgress: progress,
      queued: actionId === activeAction ? null : actionId,
      started: performance.now(),
      duration: reducedMotion ? 1 : Math.max(1, row.duration * 370 * Math.abs(progress - baseline) / 100),
    };
    status.transitioning = true;
    requestRender();
  } else {
    startAction(actionId);
  }
}

function updatePlaybackUI() {
  if (!$('motion-status')) return;
  const label = info?.actions.find((a) => a.id === activeAction)?.label;
  $('motion-status').textContent = status.ready
    ? (label ? `${label} · ${status.paused ? '已暂停' : status.stage || '演示中'}` : `${info.version} · ${info.actions.length} 项演示`)
    : '正在载入模型…';
  $('pause-motion').textContent = status.paused ? '继续' : '暂停';
  $('pause-motion').disabled = !motion;
}

function stopAnimations() {
  playlist = []; pausedAt = null; motion = null; activeAction = null;
  status.activeAction = null; status.transitioning = false;
  status.controlProgress = null; status.stage = null; status.paused = false;
  status.playlistRemaining = 0;
  cadMotion?.resetAll(); requestRender();
}

function playAll() {
  if (!status.ready) return;
  stopAnimations();
  playlist = info.actions.map((action) => action.id);
  if (playlist.length) startAction(playlist.shift(), true);
}

function pauseMotion() {
  if (!motion) return;
  if (pausedAt === null) pausedAt = performance.now();
  else { motion.started += performance.now() - pausedAt; pausedAt = null; }
  requestRender();
}

function resetModelAndView() {
  playlist = []; pausedAt = null;
  motion = null;
  activeAction = null;
  status.activeAction = null;
  status.transitioning = false;
  cadMotion.resetAll();
  status.controlProgress = null;
  status.stage = null;
  topView = false;
  $('top-view').setAttribute('aria-pressed', 'false');
  fitModel(info.cameraDirection);
  requestRender();
}

function fitModel(directionValues = info.cameraDirection) {
  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());
  const direction = new THREE.Vector3(...directionValues).normalize();
  const vfov = THREE.MathUtils.degToRad(camera.fov);
  const right = new THREE.Vector3()
    .crossVectors(new THREE.Vector3(0, 1, 0), direction)
    .normalize();
  const up = new THREE.Vector3().crossVectors(direction, right).normalize();
  let distance = 0;
  for (const x of [-0.5, 0.5])
    for (const y of [-0.5, 0.5])
      for (const z of [-0.5, 0.5]) {
        const corner = new THREE.Vector3(x * size.x, y * size.y, z * size.z);
        distance = Math.max(
          distance,
          corner.dot(direction) +
            Math.max(
              Math.abs(corner.dot(right)) /
                (Math.tan(vfov / 2) * camera.aspect),
              Math.abs(corner.dot(up)) / Math.tan(vfov / 2),
            ),
        );
      }
  camera.position
    .copy(center)
    .addScaledVector(direction, distance * (electricalVisible ? 1.12 : 1));
  controls.target.copy(center);
  camera.near = 0.015;
  camera.far = 150;
  camera.updateProjectionMatrix();
  controls.update();
}

function resize() {
  if (!renderer) return;
  const { width, height } = host.getBoundingClientRect();
  renderer.setSize(width, height);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  if (model) fitModel(topView ? [0.001, 1, 0.001] : camera.position.clone().sub(controls.target).toArray());
  requestRender();
}

function installInteractions() {
  const canvas = renderer.domElement;
  canvas.addEventListener('pointerdown', (event) => {
    pointerStart = { x: event.clientX, y: event.clientY, at: performance.now() };
  });
  canvas.addEventListener('pointerup', (event) => {
    if (!pointerStart) return;
    const distance = Math.hypot(
      event.clientX - pointerStart.x,
      event.clientY - pointerStart.y,
    );
    const elapsed = performance.now() - pointerStart.at;
    pointerStart = null;
    if (distance > 8 || elapsed > 450 || !status.ready) return;
    const rect = canvas.getBoundingClientRect();
    pointer.set(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1,
    );
    raycaster.setFromCamera(pointer, camera);
    const hit = raycaster
      .intersectObject(model, true)
      .find((item) => Object.keys(item.object.userData.motions || {}).length);
    if (!hit) return;
    const actionId = Object.keys(hit.object.userData.motions)[0];
    setAction(actionId);
  });

  function setElectricalVisible(next) {
    if (next === electricalVisible) return;
    electricalVisible = next;
    ghostMode(electricalVisible);
    electricalOverlay.visible = electricalVisible;
    status.electricalVisible = electricalVisible;
    status.contextOpacity = electricalVisible ? .04 : null;
    $('electrical-toggle').setAttribute('aria-pressed', String(electricalVisible));
    $('electrical-toggle').textContent = electricalVisible ? '隐藏电路' : '显示电路';
    $('electrical-panel').hidden = !electricalVisible;
    document.body.classList.toggle('electrical-mode', electricalVisible);
    const demoPanel = document.querySelector('.demo-panel');
    if (electricalVisible) { demoPanelWasOpen = demoPanel.open; demoPanel.open = false; }
    else demoPanel.open = demoPanelWasOpen;
    resize();
  }
  $('electrical-toggle').addEventListener('click', () => setElectricalVisible(!electricalVisible));
  for (const id of ['locate-inverter', 'locate-inverter-panel']) $(id).addEventListener('click', () => {
    setElectricalVisible(true);
    topView = false;
    $('top-view').setAttribute('aria-pressed', 'false');
    controls.target.set(2.53,1.83,.78);
    camera.position.set(1.35,2.25,-.95);
    controls.update();
    requestRender();
  });

  $('reset').addEventListener('click', resetModelAndView);
  $('play-all').addEventListener('click', playAll);
  $('pause-motion').addEventListener('click', pauseMotion);
  $('stop-motion').addEventListener('click', stopAnimations);
  $('play-selected').addEventListener('click', () => setAction($('action-select').value));
  $('top-view').addEventListener('click', () => {
    topView = !topView;
    $('top-view').setAttribute('aria-pressed', String(topView));
    fitModel(topView ? [0.001, 1, 0.001] : info.cameraDirection);
    requestRender();
  });
  for (const [id, scale] of [
    ['zoom-in', 0.78],
    ['zoom-out', 1.28],
  ]) {
    $(id).addEventListener('click', () => {
      const delta = camera.position.clone().sub(controls.target);
      delta.setLength(
        THREE.MathUtils.clamp(
          delta.length() * scale,
          controls.minDistance,
          controls.maxDistance,
        ),
      );
      camera.position.copy(controls.target).add(delta);
      requestRender();
    });
  }
  $('share').addEventListener('click', async () => {
    const payload = {
      title: 'A27 · 房车活动模型',
      text: '柜门点击开启、再点关闭；其他活动部件点击播放。',
      url: location.href,
    };
    try {
      if (navigator.share) {
        await navigator.share(payload);
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(location.href);
        $('share').setAttribute('aria-label', '链接已复制');
        setTimeout(() => $('share').setAttribute('aria-label', '分享模型'), 1800);
      }
    } catch (error) {
      if (error.name !== 'AbortError') console.error(error);
    }
  });
}

async function init() {
  try {
    renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'low-power',
    });
  } catch {
    $('loading-detail').textContent = '请使用 Safari 或 Chrome 打开';
    return;
  }
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.setClearColor('#f4f3ee');
  host.appendChild(renderer.domElement);
  camera = new THREE.PerspectiveCamera(38, 1, 0.015, 150);
  scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight('#fffcf2', '#aeb7a6', 1.7));
  const key = new THREE.DirectionalLight('#fff8e9', 2);
  key.position.set(3, 7, 4);
  scene.add(key);
  const fill = new THREE.DirectionalLight('#e8f2ff', 0.7);
  fill.position.set(-5, 3, -3);
  scene.add(fill);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.09;
  controls.minDistance = 0.5;
  controls.maxDistance = 25;
  controls.maxPolarAngle = Math.PI * 0.92;
  controls.screenSpacePanning = true;
  controls.touches.ONE = THREE.TOUCH.ROTATE;
  controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
  controls.addEventListener('change', requestRender);
  controls.addEventListener('start', () => {
    if (motion) requestRender();
  });
  resize();

  try {
    const response = await fetch('./model-info.json');
    if (!response.ok) throw new Error('metadata');
    info = await response.json();
    status.revision = info.revision;
    const gltf = await new GLTFLoader().loadAsync(`./rv-a27.glb?v=${info.assetHash || info.modelHash}`, (event) => {
      const percent = Math.min(
        96,
        Math.round((event.loaded / (event.total || info.bytes)) * 96),
      );
      $('progress').style.width = `${percent}%`;
      $('loading-detail').textContent = `正在载入活动模型 ${percent}%`;
    });
    model = gltf.scene;
    model.traverse((object) => {
      if (!object.isMesh && !object.isLine) return;
      object.userData = { ...object.parent?.userData, ...object.userData };
      if (object.isMesh) {
        object.material.flatShading = true;
        object.material.needsUpdate = true;
        const motions = object.userData.motions;
        if (motions) {
          const base = {
            position: object.position.clone(),
            quaternion: object.quaternion.clone(),
            scale: object.scale.clone(),
            morph: null,
          };
          const actions = {};
          for (const [actionId, target] of Object.entries(motions)) {
            const matrix = new THREE.Matrix4().fromArray(target.matrix);
            const position = new THREE.Vector3();
            const quaternion = new THREE.Quaternion();
            const scale = new THREE.Vector3();
            matrix.decompose(position, quaternion, scale);
            actions[actionId] = {
              position,
              quaternion,
              scale,
              morph: target.morph,
            };
            if (!actionMeshes.has(actionId)) actionMeshes.set(actionId, []);
            actionMeshes.get(actionId).push({ mesh: object });
          }
          motionNodes.set(object.uuid, { mesh: object, base, actions });
        }
      } else {
        object.material.depthWrite = false;
        object.material.transparent = true;
        const caboverReference = object.userData.zone === 'cabover_reference';
        object.material.opacity = caboverReference ? 0.78 : 0.3;
        if (caboverReference) {
          status.referenceLineSegments +=
            (object.geometry.index?.count || object.geometry.attributes.position.count) / 2;
        }
      }
    });
    for (const action of info.actions) {
      if (!actionMeshes.get(action.id)?.length) {
        throw new Error(`missing motion: ${action.id}`);
      }
    }
    if (info.motionSchema !== 2) throw new Error('Unsupported CAD timeline');
    const motionResponse = await fetch(`./motion-data.json?v=${info.motionHash}`);
    if (!motionResponse.ok) throw new Error('CAD timeline unavailable');
    const motionData = await motionResponse.json();
    if (motionData.modelHash !== info.modelHash) throw new Error('CAD timeline version mismatch');
    cadMotion = createCADMotion(model, motionData);
    cadMotion.resetAll();
    scene.add(model);
    ghostMode = createGhostMode(model);
    electricalOverlay = createElectricalOverlay();
    scene.add(electricalOverlay);
    scene.add(createInverter());
    for (const id of ['locate-inverter', 'locate-inverter-panel']) $(id).disabled = false;
    $('electrical-toggle').disabled = false;
    status.actions = info.actions.length;
    for (const action of info.actions) {
      const option = document.createElement('option'); option.value = action.id; option.textContent = action.label; $('action-select').append(option);
    }
    fitModel();
    installInteractions();
    status.ready = true;
    for (const id of ['play-all', 'play-selected', 'stop-motion', 'action-select']) $(id).disabled = false;
    if (new URLSearchParams(location.search).has('qa')) {
      window.motionTest = {
        play: setAction, playAll, pause: pauseMotion, stop: stopAnimations,
        seek(id, progress) {
          playlist = []; pausedAt = null; motion = null;
          cadMotion.resetAll();
          cadMotion.apply(id, progress);
          activeAction = id;
          status.activeAction = id;
          status.controlProgress = progress;
          status.transitioning = false;
          model.updateMatrixWorld(true);
          requestRender();
        },
        matrices() {
          model.updateMatrixWorld(true);
          return Object.fromEntries([...motionNodes.values()].map(({ mesh }) => [mesh.userData.object, mesh.matrixWorld.toArray()]));
        },
        reset: resetModelAndView,
      };
    }
    $('progress').style.width = '100%';
    $('loading').style.opacity = '0';
    setTimeout(() => {
      $('loading').style.display = 'none';
    }, reducedMotion ? 0 : 350);
    requestRender();
  } catch (error) {
    console.error(error);
    $('loading-detail').textContent = '活动模型未能载入，请刷新重试';
  }
}

window.addEventListener('resize', resize);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) requestRender();
});
init();
