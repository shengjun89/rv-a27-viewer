import json,re,hashlib,importlib.util
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gate',root/'scripts/check-render-release.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
review=json.loads((root/'docs/r5/render-review.json').read_text())
actual=['public/'+p for p in re.findall(r'<img[^>]+src="([^"]+)"',(root/'public/r5.html').read_text())]
assert set(actual)==set(review['used_assets']),'实际页面图片引用与审核清单不一致'
errors=gate.validate(review,root)
if errors:raise SystemExit('\n'.join(errors))
print('R5实际页面引用、独立审核和素材哈希一致')
