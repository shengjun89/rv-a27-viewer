// 排版文字与已经核图的 imagegen 成图；不改变模型几何。
const fs=require('fs'),path=require('path');
const sharp=require(process.env.SHARP_PATH||'/Users/bytedance/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const root=path.resolve(__dirname,'../public/share/warm-natural');
const rows=JSON.parse(fs.readFileSync(path.join(__dirname,'share-warm-content.json'),'utf8'));
const esc=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
const text=(s,x,y,size=32,color='#536357',weight=400)=>`<text x="${x}" y="${y}" font-family="PingFang SC, sans-serif" font-size="${size}" fill="${color}" font-weight="${weight}">${esc(s)}</text>`;
const lines=(s,count)=>{const arr=[];while(s){arr.push(s.slice(0,count));s=s.slice(count);}return arr;};
(async()=>{
 fs.mkdirSync(path.join(root,'pages'),{recursive:true});const manifest=[];
 for(let i=0;i<rows.length;i++){
  const [chapter,title,art,subtitle,a,b,layout,secondary]=rows[i];
  const number=String(i+1).padStart(2,'0');
  const source=art==='materials'?'材料搭配概念提案':art==='exterior'?'外观 V12R2 模型衍生':'内饰 A27 R7 模型衍生';
  const mini=layout==='duo'||layout==='compare';
  let svg=`<svg width="1200" height="1600" xmlns="http://www.w3.org/2000/svg"><rect width="1200" height="1600" fill="#f7f3e9"/>`;
  svg+=text('房车装修手记  /  暖白自然篇',54,59,24,'#7b826e');
  svg+=text(number+' / 28',1050,59,22,'#8d7660');
  svg+=`<path d="M54 84H1146" stroke="#b5bda9"/>`;
  svg+=text(chapter,54,128,26,'#a07251');svg+=text(title,50,199,60,'#344c3c',600);
  svg+=text(subtitle,54,1189,mini?32:38,'#344c3c',600);
  let y=1250;
  for(const paragraph of [a,b]){for(const line of lines(paragraph,mini?22:33)){svg+=text(line,54,y,mini?28:31);y+=44;}y+=17;}
  if(layout==='palette'){
   const colors=['#f2ebdd','#b88c58','#99a78a','#b17c61','#9b7d42'];
   colors.forEach((c,j)=>{svg+=`<circle cx="${81+j*92}" cy="1460" r="22" fill="${c}"/>`;});
   svg+=text('暖白 · 木色 · 浅绿 · 陶土 · 黄铜',560,1470,24,'#8d7660');
  }
  svg+=`<path d="M54 1518H1146" stroke="#b5bda9"/>`;
  svg+=text(source+' · AI 美化参考，非施工尺寸图',54,1555,22,'#7a7e70');
  svg+='</svg>';
  const layers=[{input:Buffer.from(svg)}];
  const hero=await sharp(path.join(root,'assets',art+'.png')).resize(1120,896,{fit:'contain',background:'#f7f3e9'}).toBuffer();layers.push({input:hero,left:40,top:225});
  const badge=Buffer.from(`<svg width="250" height="38"><rect width="250" height="38" rx="4" fill="#f7f3e9" fill-opacity=".92"/>${text('AI 美化 · 材质与氛围提案',10,26,18,'#50614d')}</svg>`);layers.push({input:badge,left:56,top:1070});
  if(mini){const key=layout==='compare'?(art==='kitchen'?'kitchen-model':'model'):secondary;
   layers.push({input:await sharp(path.join(root,'assets',key+'.png')).resize(300,240,{fit:'contain',background:'#f7f3e9'}).toBuffer(),left:850,top:1210});
   layers.push({input:Buffer.from(`<svg width="310" height="34">${text(layout==='compare'?'原模型 · 比例与结构参照':'局部搭配 · AI 参考',0,26,20,'#7a7e70')}</svg>`),left:850,top:1465});
  }
  const name=`${number}.jpg`;await sharp({create:{width:1200,height:1600,channels:3,background:'#f7f3e9'}}).composite(layers).jpeg({quality:94,chromaSubsampling:'4:4:4'}).toFile(path.join(root,'pages',name));
  manifest.push({number:i+1,title,chapter,image:'warm-natural/pages/'+name,art,layout:layout||'hero',width:1200,height:1600,kind:'AI美化参考',source});
 }
 fs.writeFileSync(path.join(root,'pages.json'),JSON.stringify(manifest,null,2));
 const thumbs=await Promise.all(manifest.map(async(p,i)=>({input:await sharp(path.join(root,'pages',String(i+1).padStart(2,'0')+'.jpg')).resize(210,280).toBuffer(),left:(i%7)*210,top:Math.floor(i/7)*280})));
 await sharp({create:{width:1470,height:1120,channels:3,background:'#fff'}}).composite(thumbs).jpeg({quality:90}).toFile(path.join(root,'contact.jpg'));
 console.log('已生成28张1200×1600分享图');
})();
