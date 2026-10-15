import json,re,hashlib,importlib.util
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gate',root/'scripts/check-render-release.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
review=json.loads((root/'docs/r7/render-review.json').read_text())
actual=['public/'+p for p in re.findall(r'<img[^>]+src="([^"]+)"',(root/'public/r7.html').read_text())]
assert set(actual)==set(review['used_assets']),'实际页面图片引用与审核清单不一致'
errors=gate.validate(review,root)
if errors:raise SystemExit('\n'.join(errors))
print('R7实际页面引用、独立审核和素材哈希一致')

manifest=json.loads((root/'public/versions.json').read_text())
for asset in manifest['assets']:
 if asset['path'] in ('render-details-r7.glb','downloads/RV_R7_FrontSurface_FreeCAD.zip'):
  assert hashlib.sha256((root/'public'/asset['path']).read_bytes()).hexdigest()==asset['sha256'],asset['path']+'版本哈希不一致'
assert './render-details-r7.glb?v=20261015-r7' in (root/'src/main.js').read_text()
