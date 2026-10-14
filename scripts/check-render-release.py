"""Validate review evidence and asset immutability; does not perform visual review."""
import hashlib,json,sys
from pathlib import Path

def validate(data,root):
    errors=[];items={};producer=data.get('producer')
    if not data.get('release') or not producer:errors.append('缺发布版本或出图执行者')
    def file_ok(path,digest,label):
        p=(root/path).resolve()
        if not p.is_relative_to(root.resolve()):errors.append(label+'路径越界');return
        if not p.is_file():errors.append(label+'文件缺失');return
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:errors.append(label+'文件变化，审核失效')
    for a in data.get('assets',[]):
        ident=a.get('id')
        if not ident or ident in items:errors.append('素材ID缺失或重复');continue
        items[ident]=a
    used=data.get('used_assets',[])
    deps=data.get('layout_dependencies')
    if not deps:errors.append('缺实际排版依赖清单')
    else:
        file_ok(deps.get('path',''),deps.get('sha256'),'排版依赖')
        try:
            rows=json.loads((root/deps['path']).read_text())
            actual={v for row in rows for v in (row.get('art'),row.get('secondary')) if v}
            if actual!=set(used):errors.append('排版实际引用与审核覆盖不一致')
        except Exception:errors.append('无法读取实际排版依赖')
    if not used:errors.append('未列使用素材')
    for ident in used:
        if ident not in items:errors.append(str(ident)+'缺审核记录');continue
        a=items[ident];pre=a.get('preflight',{});rev=a.get('review',{})
        if a.get('kind') not in ('spatial','concept','model-render'):errors.append(ident+'类别无效')
        for name,record in [('预审',pre),('成图审核',rev)]:
            if record.get('status')!='pass':errors.append(ident+name+'未通过')
            if not record.get('reviewer') or record.get('reviewer')==producer:errors.append(ident+name+'缺独立审核')
        if not pre.get('invariants'):errors.append(ident+'缺出图约束')
        if not rev.get('report'):errors.append(ident+'缺独立审核原始报告')
        else:file_ok(rev['report'].get('path',''),rev['report'].get('sha256'),ident+'审核报告')
        if not rev.get('evidence') or rev.get('unresolved',[]):errors.append(ident+'缺核图证据或仍有未决项')
        if a.get('kind')=='spatial':
            for k in ('openings','orientation','occlusion','proportions','state'):
                if rev.get('checks',{}).get(k)!='pass':errors.append(ident+'/'+k+'未通过')
        file_ok(a.get('output',''),a.get('sha256'),ident+'输出')
        if not a.get('sources'):errors.append(ident+'缺源参考')
        for source in a.get('sources',[]):file_ok(source.get('path',''),source.get('sha256'),ident+'源参考')
    return errors

if __name__=='__main__':
    data=json.loads(Path(sys.argv[1]).read_text());errors=validate(data,Path(sys.argv[2]))
    for error in errors:print('拒绝发布：'+error)
    if errors:sys.exit(1)
    print('审核记录与文件哈希一致；视觉结论由登记的独立审核员负责。')
