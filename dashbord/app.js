const COL=['#2f7de1','#f28c28','#2fae66','#9b59b6','#e14b4b','#17a2b8'];
const fmt=(n,d=0)=>n==null||isNaN(n)?'—':n.toLocaleString('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d});
const MONTHS=['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь'];
function findCol(h,re){return h.find(x=>re.test(String(x).toLowerCase()))}
function parse(wb){const ws=wb.Sheets[wb.SheetNames[0]];const rows=XLSX.utils.sheet_to_json(ws,{cellDates:true,defval:null});if(!rows.length)throw new Error('В таблице нет строк');const h=Object.keys(rows[0]);
 const c={date:findCol(h,/дата/),farm:findCol(h,/ферм|подраздел|площад/),gross:findCol(h,/валов/),sold:findCol(h,/сдано|реализ|продаж/),rev:findCol(h,/выруч/),fat:findCol(h,/жир/),cows:findCol(h,/поголов|коров/),calf:findCol(h,/телят/)};
 const miss=Object.entries({Дата:c.date,Ферма:c.farm,'Валовой надой':c.gross}).filter(e=>!e[1]).map(e=>e[0]);if(miss.length)throw new Error('Не нашёл столбцы: '+miss.join(', '));
 return rows.filter(r=>r[c.date]&&r[c.farm]).map(r=>{let d=r[c.date];if(!(d instanceof Date))d=new Date(d);return{d,day:d.getDate(),farm:String(r[c.farm]).trim(),gross:+r[c.gross]||0,sold:+r[c.sold]||0,rev:+r[c.rev]||0,fat:r[c.fat]==null?null:+r[c.fat],cows:r[c.cows]==null?null:+r[c.cows],calf:+r[c.calf]||0}})}
let charts=[];
function render(data){charts.forEach(c=>c.destroy());charts=[];const farms=[...new Set(data.map(r=>r.farm))];const days=[...new Set(data.map(r=>r.day))].sort((a,b)=>a-b);
 const by=f=>data.filter(r=>r.farm==f);const sum=(a,k)=>a.reduce((s,r)=>s+(r[k]||0),0);
 const d0=data[0].d;document.getElementById('title').textContent='Молочное производство — '+MONTHS[d0.getMonth()]+' '+d0.getFullYear();
 document.getElementById('sub').textContent='Фермы: '+farms.map(f=>{const dd=by(f).map(r=>r.day);return f+' (данные за '+Math.min(...dd)+'–'+Math.max(...dd)+' число)'}).join(', ');
 const G=sum(data,'gross'),S=sum(data,'sold'),R=sum(data,'rev'),C=sum(data,'calf');
 const wfat=a=>{const w=a.filter(r=>r.fat!=null);return w.reduce((s,r)=>s+r.fat*r.gross,0)/w.reduce((s,r)=>s+r.gross,0)};
 const split=(k,d=0,suf='')=>farms.map(f=>f+': '+fmt(sum(by(f),k),d)+suf).join(' · ');
 const tiles=[['Валовой надой, л',fmt(G),split('gross')],['Сдано на продажу, л',fmt(S),fmt(S/G*100,1)+' % от валового'],['Выручка с НДС, ₽',fmt(R),split('rev',0,' ₽')],['Средняя цена, ₽/л',fmt(R/S,2),'выручка / сданное молоко'],['Средняя жирность, %',fmt(wfat(data),2),farms.map(f=>f+': '+fmt(wfat(by(f)),2)).join(' · ')],['Передано телятам, л',fmt(C),fmt(C/G*100,1)+' % от валового']];
 document.getElementById('tiles').innerHTML=tiles.map(t=>`<div class="tile"><div class="tl">${t[0]}</div><div class="tv">${t[1]}</div><div class="ts">${t[2]}</div></div>`).join('');
 const ser=fn=>farms.map((f,i)=>({label:f,data:days.map(d=>{const r=by(f).find(x=>x.day==d);return r?fn(r):null}),borderColor:COL[i],backgroundColor:COL[i],pointBackgroundColor:'#fff',pointBorderColor:COL[i],pointRadius:3,borderWidth:2.5,tension:.3,spanGaps:false}));
 const base=(extra={})=>Object.assign({responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{position:'bottom',labels:{boxWidth:28,font:{size:12}}},tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmt(c.parsed.y??c.parsed.x,(c.parsed.y??0)<100?2:0)}}},scales:{x:{grid:{color:'#eef0f3'}},y:{grid:{color:'#eef0f3'},ticks:{callback:v=>fmt(v,v<10&&v%1?1:0)}}}},extra);
 const defs=[['Валовой надой по дням, л','line',ser(r=>r.gross)],['Выручка по дням с НДС, ₽','bar',ser(r=>r.rev)],['Цена за литр с НДС, ₽','line',ser(r=>r.sold?r.rev/r.sold:null)],['Средняя жирность, %','line',ser(r=>r.fat)],['Надой на одну корову в день, л','line',ser(r=>r.cows?r.gross/r.cows:null)],['Поголовье коров на дойке','line',ser(r=>r.cows)],['Распределение валового надоя, л','stack',null],['Передача телятам по дням, л','bar',ser(r=>r.calf)]];
 const grid=document.getElementById('grid');grid.innerHTML='';
 defs.forEach(([t,type,ds])=>{const card=document.createElement('div');card.className='card';card.innerHTML=`<h3>${t}</h3><div class="cw"><canvas></canvas></div>`;grid.appendChild(card);const cv=card.querySelector('canvas');
  if(type=='stack'){charts.push(new Chart(cv,{type:'bar',data:{labels:farms,datasets:[{label:'Сдано на продажу',data:farms.map(f=>sum(by(f),'sold')),backgroundColor:COL[2]},{label:'Передано телятам',data:farms.map(f=>sum(by(f),'calf')),backgroundColor:COL[3]},{label:'Прочее',data:farms.map(f=>Math.max(0,sum(by(f),'gross')-sum(by(f),'sold')-sum(by(f),'calf'))),backgroundColor:'#c9ced6'}]},options:base({indexAxis:'y',scales:{x:{stacked:true,grid:{color:'#eef0f3'},ticks:{callback:v=>fmt(v)}},y:{stacked:true,grid:{display:false}}}})}))}
  else charts.push(new Chart(cv,{type:type,data:{labels:days,datasets:ds},options:base()}))});
 document.getElementById('dash').style.display='block'}
function load(buf,name){try{const wb=XLSX.read(buf,{type:'array',cellDates:true});render(parse(wb));document.getElementById('msg').textContent='Загружен файл: '+name;document.getElementById('msg').className='ok'}catch(e){document.getElementById('msg').textContent='Ошибка: '+e.message;document.getElementById('msg').className='err'}}
window.addEventListener('DOMContentLoaded',()=>{const inp=document.getElementById('file');inp.addEventListener('change',()=>{const f=inp.files[0];if(f)f.arrayBuffer().then(b=>load(b,f.name))});
 const dz=document.body;dz.addEventListener('dragover',e=>e.preventDefault());dz.addEventListener('drop',e=>{e.preventDefault();const f=e.dataTransfer.files[0];if(f)f.arrayBuffer().then(b=>load(b,f.name))});
 if(window.SAMPLE){const b=Uint8Array.from(atob(window.SAMPLE),c=>c.charCodeAt(0));load(b.buffer,'primer-dannyh.xlsx (пример)')}});
