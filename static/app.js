const $=id=>document.getElementById(id);
let uploads=[];let exporting=false;let truckAscending=true;
const countryNames={GB:'Groot-Brittannië',IE:'Ierland',NL:'Nederland',FR:'Frankrijk',DE:'Duitsland',BE:'België'};
function notice(id,text){$(id).textContent=text;$(id).classList.toggle('hidden',!text)}
function truckNumber(doc){const match=(doc.truck||'').match(/\bTRUCK\s*(\d+)/i);return match?Number(match[1]):null}
function documents(){return uploads.filter(u=>u.doc).map(u=>u.doc).sort((a,b)=>{const left=truckNumber(a),right=truckNumber(b);if(left===null)return right===null?0:1;if(right===null)return -1;return truckAscending?left-right:right-left})}
function removeUpload(id){const upload=uploads.find(u=>u.id===id);upload?.controller.abort();uploads=uploads.filter(u=>u.id!==id);notice('exportNotice','');render()}
function valid(doc){return /^[0-9]{2}[A-Z]{2}[A-Z0-9]{14}$/.test(doc.mrn.trim().toUpperCase())&&/^[A-Z]{2}$/.test(doc.country.trim().toUpperCase())&&!!doc.plate.trim()&&!!doc.booking.trim()}
function duplicates(){const counts={};documents().forEach(d=>counts[d.mrn.trim().toUpperCase()]=(counts[d.mrn.trim().toUpperCase()]||0)+1);return counts}
function update(){
 const docs=documents();const counts=duplicates();let ready=0;
 docs.forEach((doc,i)=>{doc.type=doc.country.trim().toUpperCase()==='GB'?'EU':doc.country.trim()?'TT2':'';const duplicate=counts[doc.mrn.trim().toUpperCase()]>1;const good=valid(doc)&&!duplicate;if(good)ready++;const status=$('status'+i);status.textContent=duplicate?'Dubbel MRN':good?'✓ Compleet':'○ Aanvullen';status.classList.toggle('ready',good);const type=$('type'+i);type.textContent=doc.type||'—';type.className='type'+(doc.type==='TT2'?' tt2':'')});
 const pending=uploads.some(u=>u.status==='pending');const errors=uploads.some(u=>u.status==='error');
 $('export').disabled=exporting||!docs.length||ready!==docs.length||pending||errors;
 $('summary').textContent=docs.length?ready+' van '+docs.length+' documenten compleet':pending?'PDF’s worden uitgelezen':'Nog geen documenten toegevoegd';
 $('summaryDetail').textContent=errors?'Verwijder bestanden die niet konden worden uitgelezen voordat je exporteert.':pending?'Wacht tot alle PDF’s zijn uitgelezen.':docs.length?'Controleer het MRN en bestemmingsland. Vul bij iedere regel het kenteken en bookingnummer in.':'Het importbestand gebruikt de kolommen van je Portbase-template.';
 $('step1').classList.toggle('active',!docs.length||pending);$('step2').classList.toggle('active',!!docs.length&&!pending&&ready<docs.length);$('step3').classList.toggle('active',!!docs.length&&ready===docs.length&&!errors&&!pending);
}
function fieldCell(value,label,oninput,css){const td=document.createElement('td');const input=document.createElement('input');input.value=value;input.placeholder=label;input.setAttribute('aria-label',label);if(css)input.className=css;input.maxLength=100;input.addEventListener('input',()=>{oninput(input.value);notice('exportNotice','');update()});td.append(input);return td}
function render(){
 $('truckHeading').setAttribute('aria-sort',truckAscending?'ascending':'descending');$('sortTruck').textContent='Truck nummer '+(truckAscending?'↑':'↓');$('sortTruck').setAttribute('aria-label',truckAscending?'Truck nummer: laag naar hoog. Klik voor hoog naar laag.':'Truck nummer: hoog naar laag. Klik voor laag naar hoog.');
 $('filelist').replaceChildren();uploads.forEach(upload=>{
  const row=document.createElement('div');row.className='file-item';row.style.alignItems='center';const name=document.createElement('span');name.textContent=upload.file.name;name.style.flex='1';name.style.minWidth='0';
  const info=document.createElement('small');info.textContent=upload.status==='pending'?'Bezig met uitlezen…':upload.status==='error'?'Niet uitgelezen':Math.round(upload.file.size/1024)+' KB';
  const button=document.createElement('button');button.className='file-remove';button.textContent='Verwijderen';button.setAttribute('aria-label',upload.file.name+' verwijderen');button.onclick=()=>removeUpload(upload.id);row.append(name,info,button);$('filelist').append(row);
  if(upload.error){const error=document.createElement('div');error.className='notice';error.textContent=upload.error;$('filelist').append(error)}
 });
 $('filelist').classList.toggle('hidden',!uploads.length);notice('uploadNotice',uploads.length?uploads.length+' PDF'+(uploads.length===1?'':'’s')+' toegevoegd. Bestanden worden alleen lokaal verwerkt.':'');
 const docs=documents();$('rows').replaceChildren();docs.forEach((doc,i)=>{
  const row=document.createElement('tr');const index=i+1;
  const mrn=fieldCell(doc.mrn,'MRN document '+index,value=>doc.mrn=value,'mrn');const source=document.createElement('div');source.className='docname';source.textContent=doc.name+' · '+doc.pages+' pagina'+(doc.pages===1?'':'’s');mrn.append(source);if(doc.warnings.length){const warning=document.createElement('div');warning.className='row-warning';warning.textContent=doc.warnings.join(' ');mrn.append(warning)}row.append(mrn);
  const country=fieldCell(doc.country,'Bestemmingsland document '+index,value=>doc.country=value,'country-input');country.firstChild.maxLength=2;country.firstChild.style.textTransform='uppercase';row.append(country);
  const type=document.createElement('td');const tag=document.createElement('span');tag.id='type'+i;type.append(tag);row.append(type);
  const truck=document.createElement('td');truck.textContent=doc.truck||'Niet vermeld';truck.style.fontSize='11px';
  if(doc.truck_source){truck.title='Bron: transportveld ['+doc.truck_source+']';const source=document.createElement('div');source.className='docname';source.textContent='['+doc.truck_source+']';truck.append(source)}
  row.append(truck);
  row.append(fieldCell(doc.plate,'Kenteken document '+index,value=>doc.plate=value));row.append(fieldCell(doc.booking,'Bookingnummer document '+index,value=>doc.booking=value));
  const status=document.createElement('td');const span=document.createElement('span');span.className='status';span.id='status'+i;status.append(span);row.append(status);
  const remove=document.createElement('td');const button=document.createElement('button');button.className='remove';button.textContent='×';button.setAttribute('aria-label','Document '+index+' verwijderen');button.onclick=()=>removeUpload(doc.uploadId);remove.append(button);row.append(remove);$('rows').append(row);
 });
 $('tableWrap').classList.toggle('hidden',!docs.length);$('empty').classList.toggle('hidden',!!docs.length);$('reset').classList.toggle('hidden',!uploads.length);$('count').textContent=docs.length+' document'+(docs.length===1?'':'en');update();
}
async function selected(files){
 const inputFiles=[...files];$('files').value='';notice('exportNotice','');
 const added=[];
 for(const file of inputFiles){
  if(!file.name.toLowerCase().endsWith('.pdf')){notice('exportNotice','Alleen PDF-bestanden kunnen worden toegevoegd.');continue}
  if(uploads.some(u=>u.file.name===file.name&&u.file.size===file.size&&u.file.lastModified===file.lastModified))continue;
  if(uploads.length>=200){notice('exportNotice','Voeg maximaal 200 PDF’s tegelijk toe.');break}
  const upload={id:crypto.randomUUID(),file,status:'pending',controller:new AbortController()};uploads.push(upload);added.push(upload);
 }
 render();
 for(const upload of added){
  if(!uploads.includes(upload))continue;
  try{
   if(upload.file.size>20*1024*1024)throw new Error('Een PDF mag maximaal 20 MB groot zijn.');
   const response=await fetch('/api/extract',{method:'POST',headers:{'Content-Type':'application/pdf','X-Portbase-Request':'local'},body:upload.file,signal:upload.controller.signal});const result=await response.json();
   if(!response.ok)throw new Error(result.error||'De PDF kon niet worden uitgelezen.');
   if(uploads.includes(upload)){upload.doc={...result,name:upload.file.name,uploadId:upload.id,plate:'',booking:''};upload.status='ready'}
  }catch(error){if(error.name!=='AbortError'&&uploads.includes(upload)){upload.status='error';upload.error=error.message}}
  render();
 }
}
$('choose').onclick=()=>$('files').click();$('files').onchange=e=>selected(e.target.files);
for(const event of ['dragenter','dragover'])$('drop').addEventListener(event,e=>{e.preventDefault();$('drop').classList.add('over')});$('drop').addEventListener('dragleave',()=>$('drop').classList.remove('over'));$('drop').addEventListener('drop',e=>{e.preventDefault();$('drop').classList.remove('over');selected(e.dataTransfer.files)});
$('reset').onclick=()=>{uploads.forEach(u=>u.controller.abort());uploads=[];notice('exportNotice','');render()};
$('sortTruck').onclick=()=>{truckAscending=!truckAscending;render()};
$('export').onclick=async()=>{
 exporting=true;update();notice('exportNotice','');
 try{
  const response=await fetch('/api/prepare-export',{method:'POST',headers:{'Content-Type':'application/json','X-Portbase-Request':'local'},body:JSON.stringify({documents:documents().map(({mrn,country,plate,booking})=>({mrn,country,plate,booking}))})});
  if(!response.ok){const result=await response.json();throw new Error(result.error||'Exporteren is mislukt.')}
  const result=await response.json();const a=document.createElement('a');a.href=result.download_url;a.download='Portbase-import.xls';document.body.append(a);a.click();a.remove();notice('exportNotice','Het XLS-bestand is aangemaakt en de download is gestart. Open het in Excel om de export te controleren.');
 }catch(error){notice('exportNotice',error.message)}finally{exporting=false;update()}
};
$('help').onclick=()=>$('dialog').showModal();$('close').onclick=()=>$('dialog').close();render();
