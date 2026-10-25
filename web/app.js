import {DEFAULT_SOURCE,parseForge,sampleObject,findSceneDuration,upsertKeyframe} from "./forge.mjs";
const $=function(id){return document.getElementById(id);},sourceEditor=$("forgeSource"),canvas=$("canvas2d"),ctx=canvas.getContext("2d");
let project=null,frame=0,playing=false,startedAt=0,startFrame=0,selected="orb",THREE=null,scene3=null,camera3=null,renderer3=null,meshByName=new Map(),cameraAngle=.35,cameraTilt=.25,cameraDistance=5.5,drag=null,toastTimer=null;
sourceEditor.value=DEFAULT_SOURCE;
function toast(message){$("toast").textContent=message;$("toast").classList.add("show");clearTimeout(toastTimer);toastTimer=setTimeout(function(){$("toast").classList.remove("show");},2800);}
function status(message,error=false){$("statusText").textContent=message;$("parseState").textContent=error?"ERROS":"SEM ERROS";$("parseState").style.color=error?"#ff777f":"var(--accent)";}
function saveState(value){$("saveState").textContent=value;}
function objectByName(name){return project&&project.objects.find(function(obj){return obj.name===name;});}
function activeView(view){document.querySelectorAll(".viewtab").forEach(function(el){el.classList.toggle("active",el.dataset.view===view);});$("stage2d").classList.toggle("active",view==="2d");$("stage3d").classList.toggle("active",view==="3d");$("stageCode").classList.toggle("active",view==="code");if(view==="3d"){resizeThree();drawThree();}if(view==="2d")draw2d();}
function panelView(panel){document.querySelectorAll(".righttab").forEach(function(el){el.classList.toggle("active",el.dataset.panel===panel);});$("inspector").classList.toggle("hidden",panel!=="inspector");$("aiPanel").classList.toggle("hidden",panel!=="ai");$("learnPanel").classList.toggle("hidden",panel!=="learn");}
function refreshObjects(){
 const list=$("objectList"),select=$("selectedObject");list.replaceChildren();select.replaceChildren();
 project.objects.forEach(function(obj){const option=document.createElement("option");option.value=obj.name;option.textContent=obj.name;select.append(option);const button=document.createElement("button");button.className="object-row"+(obj.name===selected?" selected":"");const icon=document.createElement("span");icon.className="shape-icon "+(obj.type==="circle"?"circle":obj.type==="rect"?"rect":obj.type==="text"?"text":"cube");if(obj.type==="text")icon.textContent="T";if(obj.type==="cube")icon.textContent="◇";const label=document.createElement("span");label.textContent=obj.name;const kind=document.createElement("em");kind.textContent=obj.type==="cube"?"3D":obj.type==="text"?"TXT":"2D";button.append(icon,label,kind);button.addEventListener("click",function(){selected=obj.name;refreshAll();panelView("inspector");});list.append(button);});
 if(!objectByName(selected))selected=project.objects[0]?project.objects[0].name:"";select.value=selected;$("objectCount").textContent=String(project.objects.length).padStart(2,"0");
}
function refreshInspector(){const obj=objectByName(selected);if(!obj)return;const p=sampleObject(obj,frame);$("propX").value=Number(p.x||0);$("propY").value=Number(p.y||0);$("propScale").value=Number(p.scale===undefined?1:p.scale);const color=/^#[0-9a-fA-F]{6}$/.test(p.color||"")?p.color:"#65e8d4";$("propColor").value=color;$("colorValue").textContent=color.toUpperCase();$("objectType").textContent=obj.type==="cube"?"3D OBJECT":obj.type==="text"?"TEXT OBJECT":"2D OBJECT";}
function renderTimeline(){
 const duration=findSceneDuration(project);$("frameSlider").max=String(duration);$("frameSlider").value=String(Math.min(frame,duration));const sec=Math.floor(frame/project.fps),sub=frame%project.fps;$("frameInfo").textContent="FRAME "+String(frame).padStart(3,"0")+" / "+String(duration).padStart(3,"0");$("timeReadout").textContent="00:"+String(sec).padStart(2,"0")+":"+String(sub).padStart(2,"0");$("durationReadout").textContent=(duration/project.fps).toFixed(1)+" s";
 const ruler=$("ruler");ruler.replaceChildren();for(let i=0;i<=4;i++){const tick=document.createElement("span");tick.textContent=String(Math.round(duration*i/4)).padStart(3,"0");ruler.append(tick);}const tracks=$("tracks");tracks.replaceChildren();project.objects.slice(0,5).forEach(function(obj){const row=document.createElement("div");row.className="track-row";const name=document.createElement("span");name.textContent=obj.name;const line=document.createElement("div");line.className="track-line";obj.keyframes.forEach(function(key){const marker=document.createElement("i");marker.style.left="calc("+Math.min(100,key.at/duration*100)+"% - 3px)";line.append(marker);});row.append(name,line);tracks.append(row);});
}
function draw2d(){
 if(!project)return;const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);ctx.fillStyle=project.background;ctx.fillRect(0,0,w,h);ctx.strokeStyle="#ffffff08";ctx.lineWidth=1;
 for(let x=0;x<=w;x+=48){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}for(let y=0;y<=h;y+=48){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
 project.objects.forEach(function(obj){if(obj.type==="cube")return;const p=sampleObject(obj,frame),x=Number(p.x||0),y=Number(p.y||0),scale=Number(p.scale===undefined?1:p.scale);ctx.save();ctx.globalAlpha=Math.max(0,Math.min(1,Number(p.opacity===undefined?1:p.opacity)));ctx.translate(x,y);ctx.rotate(Number(p.rotation||0));ctx.scale(scale,scale);ctx.fillStyle=p.color||"#65e8d4";
 if(obj.type==="circle"){const r=Number(p.radius||24);ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.strokeStyle="#e5fffa66";ctx.lineWidth=1.4;ctx.stroke();ctx.beginPath();ctx.arc(-r*.28,-r*.32,Math.max(2,r*.13),0,Math.PI*2);ctx.fillStyle="#ffffff99";ctx.fill();}
 if(obj.type==="rect")ctx.fillRect(0,0,Number(p.width||80),Number(p.height||50));if(obj.type==="text"){ctx.font="700 "+Math.max(8,Number(p.size||20))+"px Manrope,sans-serif";ctx.textBaseline="top";ctx.fillText(String(p.value||obj.name),0,0);}
 if(obj.name===selected){const bw=obj.type==="circle"?Number(p.radius||24)*2:obj.type==="rect"?Number(p.width||80):ctx.measureText(String(p.value||obj.name)).width,bh=obj.type==="circle"?Number(p.radius||24)*2:obj.type==="rect"?Number(p.height||50):Number(p.size||20)*1.3;ctx.strokeStyle="#94bcff";ctx.lineWidth=1;ctx.setLineDash([5,4]);ctx.strokeRect(obj.type==="circle"?-bw/2:0,obj.type==="circle"?-bh/2:0,bw,bh);}ctx.restore();});
}
async function initThree(){
 try{THREE=await import("https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js");scene3=new THREE.Scene();scene3.background=new THREE.Color("#0b101a");camera3=new THREE.PerspectiveCamera(45,1,.1,100);renderer3=new THREE.WebGLRenderer({antialias:true,alpha:false});renderer3.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer3.outputColorSpace=THREE.SRGBColorSpace;$("threeCanvas").append(renderer3.domElement);scene3.add(new THREE.AmbientLight(0xffffff,1.8));const light=new THREE.DirectionalLight(0xffffff,2.3);light.position.set(3,5,4);scene3.add(light);const grid=new THREE.GridHelper(10,20,0x385265,0x202d3c);grid.position.y=-1.1;scene3.add(grid);resizeThree();rebuildThree();drawThree();$("threeStatus").textContent="WebGL ativo";setupCameraControls();}
 catch(e){$("threeStatus").textContent="3D indisponível";status("Preview 3D exige internet e WebGL; o editor 2D continua disponível.",true);}
}
function resizeThree(){if(!renderer3||!camera3)return;const root=$("threeCanvas"),w=Math.max(1,root.clientWidth),h=Math.max(1,root.clientHeight);renderer3.setSize(w,h,false);camera3.aspect=w/h;camera3.updateProjectionMatrix();}
function updateCamera(){if(!camera3)return;const x=cameraDistance*Math.sin(cameraAngle)*Math.cos(cameraTilt),z=cameraDistance*Math.cos(cameraAngle)*Math.cos(cameraTilt),y=cameraDistance*Math.sin(cameraTilt);camera3.position.set(x,y,z);camera3.lookAt(0,0,0);}
function setupCameraControls(){const el=$("threeCanvas");el.addEventListener("pointerdown",function(e){drag={x:e.clientX,y:e.clientY};el.setPointerCapture(e.pointerId);});el.addEventListener("pointermove",function(e){if(!drag)return;cameraAngle-=(e.clientX-drag.x)*.008;cameraTilt=Math.max(-1.2,Math.min(1.2,cameraTilt+(e.clientY-drag.y)*.008));drag={x:e.clientX,y:e.clientY};updateCamera();drawThree();});el.addEventListener("pointerup",function(){drag=null;});el.addEventListener("pointercancel",function(){drag=null;});el.addEventListener("wheel",function(e){cameraDistance=Math.max(2,Math.min(14,cameraDistance+e.deltaY*.008));updateCamera();drawThree();},{passive:true});updateCamera();}
function rebuildThree(){if(!THREE||!scene3)return;meshByName.forEach(function(mesh){scene3.remove(mesh);mesh.geometry.dispose();mesh.material.dispose();});meshByName.clear();project.objects.filter(function(obj){return obj.type==="cube";}).forEach(function(obj){const size=Number(obj.props.size||1),mesh=new THREE.Mesh(new THREE.BoxGeometry(size,size,size),new THREE.MeshStandardMaterial({color:obj.props.color||"#65e8d4",metalness:.18,roughness:.34}));scene3.add(mesh);meshByName.set(obj.name,mesh);});}
function drawThree(){if(!THREE||!renderer3||!project)return;project.objects.filter(function(obj){return obj.type==="cube";}).forEach(function(obj){const mesh=meshByName.get(obj.name);if(!mesh)return;const p=sampleObject(obj,frame);mesh.position.set(Number(p.x||0),Number(p.y||0),Number(p.z||0));mesh.rotation.set(Number(p.rotationX||0),Number(p.rotationY||0),Number(p.rotationZ||0));mesh.scale.setScalar(Math.max(.001,Number(p.scale===undefined?1:p.scale)));if(/^#[0-9a-fA-F]{6}$/.test(p.color||""))mesh.material.color.set(p.color);});updateCamera();renderer3.render(scene3,camera3);}
function refreshAll(){project=parseForge(sourceEditor.value);$("projectName").textContent=project.name;$("sideName").textContent=project.name;$("lineCount").textContent=sourceEditor.value.split(/\r?\n/).length+" LINHAS";refreshObjects();refreshInspector();renderTimeline();draw2d();if(renderer3){rebuildThree();drawThree();}if(project.errors.length)status(project.errors.length+" erro(s) · linha "+project.errors[0].line+": "+project.errors[0].message,true);else status("Script FORGE analisado sem erros");return project;}
function applyProps(){const obj=objectByName(selected);if(!obj)return;const values={x:Number($("propX").value),y:Number($("propY").value),scale:Number($("propScale").value),color:$("propColor").value};if(!Number.isFinite(values.x)||!Number.isFinite(values.y)||!Number.isFinite(values.scale)){toast("Confira os valores numéricos.");return;}sourceEditor.value=upsertKeyframe(sourceEditor.value,obj.type==="cube"?"key3":"key",obj.name,frame,values);saveState("Alterações não exportadas");refreshAll();toast("Keyframe escrito na linguagem FORGE.");}
function addCircle(){const name="shape_"+(project.objects.length+1);sourceEditor.value+="\n\ncircle "+name+" x=480 y=270 radius=32 color=#79a9ff\nkey "+name+" at="+frame+" x=480 y=270 scale=1";selected=name;refreshAll();activeView("2d");toast("Objeto "+name+" adicionado.");}
function download(name,content,type){const blob=new Blob([content],{type:type}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=name;a.click();setTimeout(function(){URL.revokeObjectURL(url);},1000);}
function exportCode(){download("scene.forge",sourceEditor.value,"text/plain;charset=utf-8");saveState("FORGE exportado");toast("Arquivo scene.forge baixado.");}
function exportProject(){const check=parseForge(sourceEditor.value);download("motionforge-project.json",JSON.stringify({format:"motionforge-project",version:1,source:sourceEditor.value,project:{name:check.name,fps:check.fps,width:check.width,height:check.height}},null,2),"application/json");saveState("Exportado");toast("Projeto JSON exportado.");}
function newProject(){if(sourceEditor.value!==DEFAULT_SOURCE&&!confirm("Criar uma nova cena e substituir o script atual?"))return;sourceEditor.value='scene "Nova Cena" fps=24 width=960 height=540\nbackground color=#0b1020\ncircle orb x=480 y=270 radius=32 color=#65e8d4\nkey orb at=0 x=480 y=270 scale=1\nkey orb at=24 x=480 y=160 scale=1.2\nkey orb at=48 x=480 y=270 scale=1';frame=0;selected="orb";refreshAll();saveState("Novo projeto");}
function openFile(file){if(!file)return;const reader=new FileReader();reader.onload=function(){try{const data=JSON.parse(String(reader.result)),src=typeof data==="string"?data:data.source;if(typeof src!=="string")throw new Error("O JSON não contém source FORGE.");sourceEditor.value=src;frame=0;refreshAll();saveState("Projeto aberto");toast("Projeto carregado.");}catch(e){toast(e.message||"JSON inválido.");}};reader.readAsText(file);}
function addMessage(role,text,label){const article=document.createElement("article");article.className="message";const avatar=document.createElement("b");avatar.textContent=role==="user"?"◉":"✦";const content=document.createElement("div"),strong=document.createElement("strong"),p=document.createElement("p");strong.textContent=label||(role==="user"?"Você":"Forge AI");p.textContent=text;content.append(strong,p);article.append(avatar,content);$("chatLog").append(article);$("chatLog").scrollTop=$("chatLog").scrollHeight;}
async function postJSON(path,payload){const res=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)}),data=await res.json().catch(function(){return {};});if(!res.ok)throw new Error(data.error||("HTTP "+res.status));return data;}
async function runAI(mode){const prompt=$("aiPrompt").value.trim()||(mode==="brainstorm"?"Sugira uma pequena cena 2D/3D para demonstrar FORGE.":"");if(!prompt){toast("Escreva uma instrução.");return;}addMessage("user",prompt,"Você");$("aiPrompt").value="";["brainstormBtn","sendBtn","trainBtn","searchBtn"].forEach(function(id){$(id).disabled=true;});$("modelTitle").textContent="Processamento em andamento";$("modelInfo").textContent="Consultando o backend local…";
 try{const endpoint=mode==="brainstorm"?"/api/brainstorm":"/api/assistant";const payload={prompt:prompt,source:sourceEditor.value,frame:frame,save_example:$("saveForTraining").checked};if(mode==="brainstorm"&&$("useReferencesForAI")&&$("useReferencesForAI").checked){const referenceContext=await buildReferencePayload();payload.reference_notes=referenceContext.reference_notes;payload.reference_images=referenceContext.reference_images;if(referenceContext.reference_images.length)addMessage("assistant","Analisando "+referenceContext.reference_images.length+" imagem(ns)/quadros enviados ao professor visual e usando as notas das referências.","Biblioteca visual");}const result=await postJSON(endpoint,payload);addMessage("assistant",result.response||"Sem resposta textual.",result.mode==="student"?"Forge AI · aluno 250K":"Forge AI · consenso dos professores");$("modelTitle").textContent=result.mode==="student"?"Modelo-aluno carregado":"Brainstorm concluído";$("modelInfo").textContent=result.saved?"Consenso salvo no dataset local.":result.mode==="student"?"Resposta gerada pelo aluno treinado.":"Resposta consolidada dos três professores.";if(result.forge){sourceEditor.value=result.forge;refreshAll();saveState("Script recebido da IA");}if(result.vote_summary)addMessage("assistant",result.vote_summary,"Placar de avaliação");if(result.errors&&result.errors.length)addMessage("assistant",result.errors.join("\n"),"Diagnóstico");}
 catch(e){addMessage("assistant","Falha: "+e.message+"\nConfira server.py, Ollama e se os três modelos estão instalados.","IA local indisponível");$("modelTitle").textContent="Backend indisponível";$("modelInfo").textContent="O editor visual continua funcionando.";}
 finally{["brainstormBtn","sendBtn","trainBtn","searchBtn"].forEach(function(id){$(id).disabled=false;});}}
async function searchWeb(){const q=$("aiPrompt").value.trim();if(!q){toast("Digite o tema da pesquisa no campo de instrução.");return;}const box=$("sources");box.classList.remove("hidden");box.textContent="Pesquisando…";try{const res=await fetch("/api/search?q="+encodeURIComponent(q)),data=await res.json();if(!res.ok)throw new Error(data.error||"Pesquisa falhou.");box.replaceChildren();const title=document.createElement("strong");title.textContent="Fontes encontradas";box.append(title);(data.results||[]).forEach(function(item){const a=document.createElement("a");a.href=item.url;a.target="_blank";a.rel="noopener noreferrer";a.textContent=item.title||item.url;const p=document.createElement("p");p.textContent=item.snippet||item.url;box.append(a,p);});if(!data.results||!data.results.length)box.append(document.createTextNode("Nenhum resultado."));}catch(e){box.textContent="Pesquisa não disponível: "+e.message;}}
async function trainStudent(){["brainstormBtn","sendBtn","trainBtn","searchBtn"].forEach(function(id){$(id).disabled=true;});$("modelTitle").textContent="Treinando aluno 250K";$("modelInfo").textContent="Treinamento local; pode levar alguns minutos.";try{const result=await postJSON("/api/train",{epochs:8});addMessage("assistant",result.response||result.log||"Treinamento finalizado.","Forge AI · treinamento");$("modelTitle").textContent=result.success?"Aluno treinado":"Treinamento falhou";$("modelInfo").textContent=result.success?"Checkpoint salvo localmente.":"Confira os requisitos e o log.";}catch(e){addMessage("assistant","Não foi possível treinar: "+e.message,"Treinamento");$("modelInfo").textContent="Instale os requisitos de ai/requirements.txt.";}finally{["brainstormBtn","sendBtn","trainBtn","searchBtn"].forEach(function(id){$(id).disabled=false;});}}
function animate(now){if(playing&&project){const duration=findSceneDuration(project);frame=(startFrame+Math.floor((now-startedAt)/1000*project.fps))%(duration+1);renderTimeline();draw2d();drawThree();refreshInspector();}
const REFERENCE_DB_NAME="motionforge-apprentice-library";
const REFERENCE_STORE="references";
let referenceDbPromise=null;
let referenceObjectUrls=[];
function openReferenceDb(){
 if(referenceDbPromise)return referenceDbPromise;
 referenceDbPromise=new Promise(function(resolve,reject){
  if(!window.indexedDB){reject(new Error("Este navegador não oferece armazenamento local de referências."));return;}
  const request=indexedDB.open(REFERENCE_DB_NAME,1);
  request.onupgradeneeded=function(){const db=request.result;if(!db.objectStoreNames.contains(REFERENCE_STORE))db.createObjectStore(REFERENCE_STORE,{keyPath:"id"});};
  request.onsuccess=function(){resolve(request.result);};
  request.onerror=function(){reject(request.error||new Error("Não foi possível abrir a biblioteca local."));};
 });
 return referenceDbPromise;
}
function referenceTransaction(mode,action){
 return openReferenceDb().then(function(db){return new Promise(function(resolve,reject){
  const tx=db.transaction(REFERENCE_STORE,mode),store=tx.objectStore(REFERENCE_STORE);let result;
  try{result=action(store);}catch(error){reject(error);return;}
  tx.oncomplete=function(){resolve(result&&result.result!==undefined?result.result:result);};
  tx.onerror=function(){reject(tx.error||new Error("Falha ao salvar a referência."));};
  tx.onabort=function(){reject(tx.error||new Error("A operação foi cancelada."));};
 });});
}
function getStoredReferences(){
 return openReferenceDb().then(function(db){return new Promise(function(resolve,reject){
  const request=db.transaction(REFERENCE_STORE,"readonly").objectStore(REFERENCE_STORE).getAll();
  request.onsuccess=function(){resolve((request.result||[]).sort(function(a,b){return b.addedAt-a.addedAt;}));};
  request.onerror=function(){reject(request.error||new Error("Não foi possível ler as referências."));};
 });});
}
function referenceId(){return (window.crypto&&crypto.randomUUID)?crypto.randomUUID():String(Date.now())+"-"+Math.random().toString(36).slice(2);}
function makeElement(tag,className,text){
 const element=document.createElement(tag);
 if(className)element.className=className;
 if(text!==undefined)element.textContent=text;
 return element;
}
async function renderReferenceList(){
 referenceObjectUrls.forEach(function(url){URL.revokeObjectURL(url);});
 referenceObjectUrls=[];
 const container=$("referenceList");
 container.replaceChildren();
 try{
  const references=await getStoredReferences();
  $("referenceStatus").textContent=references.length?references.length+" referência(s) guardada(s) somente neste aparelho.":"Nenhuma referência adicionada ainda.";
  references.forEach(function(reference){
   const card=makeElement("article","saved-reference");
   const url=URL.createObjectURL(reference.blob);referenceObjectUrls.push(url);
   if(reference.type==="image"){
    const image=makeElement("img","reference-preview");image.src=url;image.alt=reference.title;image.loading="lazy";card.append(image);
   }else{
    const video=makeElement("video","reference-preview");video.src=url;video.controls=true;video.muted=true;video.playsInline=true;video.preload="metadata";card.append(video);
   }
   card.append(makeElement("b","",reference.title||reference.name));
   card.append(makeElement("div","reference-meta",(reference.type==="image"?"IMAGEM":"VÍDEO")+" · "+(reference.size/1048576).toFixed(1)+" MB"));
   if(reference.note)card.append(makeElement("p","",reference.note));
   const actions=makeElement("div","reference-actions");
   const visual=makeElement("button","","Usar como referência");
   visual.type="button";visual.addEventListener("click",function(){
    $("aiPrompt").value="Estude esta referência visual e planeje uma animação FORGE pequena. Explique a pose/ação, o timing, os quadros-chave e o que pode ser aprendido sem copiar mecanicamente a imagem. Use a nota anexada como contexto.";
    panelView("ai");toast("Referência pronta para o Brainstorm.");
   });
   const remove=makeElement("button","","Remover");
   remove.type="button";remove.addEventListener("click",async function(){
    try{await referenceTransaction("readwrite",function(store){return store.delete(reference.id);});await renderReferenceList();toast("Referência removida.");}
    catch(error){$("referenceStatus").textContent=error.message;}
   });
   actions.append(visual,remove);card.append(actions);container.append(card);
  });
 }catch(error){$("referenceStatus").textContent="Biblioteca indisponível: "+error.message;}
}
async function saveSelectedReferences(){
 const input=$("referenceFiles"),files=Array.from(input.files||[]);
 if(!files.length){$("referenceStatus").textContent="Escolha ao menos uma imagem ou vídeo primeiro.";return;}
 const note=$("referenceNote").value.trim();
 const customTitle=$("referenceTitle").value.trim();
 const maxBytes=40*1024*1024;
 for(const file of files){
  if(!(file.type.startsWith("image/")||file.type.startsWith("video/"))){$("referenceStatus").textContent="Tipo de arquivo não aceito: "+file.name;return;}
  if(file.size>maxBytes){$("referenceStatus").textContent=file.name+" ultrapassa o limite de 40 MB.";return;}
 }
 $("addReference").disabled=true;
 $("referenceStatus").textContent="Guardando material localmente…";
 try{
  const db=await openReferenceDb();
  await new Promise(function(resolve,reject){
   const tx=db.transaction(REFERENCE_STORE,"readwrite"),store=tx.objectStore(REFERENCE_STORE);
   files.forEach(function(file,index){
    store.put({id:referenceId(),name:file.name,title:customTitle?(files.length===1?customTitle:customTitle+" — "+file.name):file.name,note:note,type:file.type.startsWith("image/")?"image":"video",mime:file.type,size:file.size,blob:file,addedAt:Date.now()+index});
   });
   tx.oncomplete=resolve;tx.onerror=function(){reject(tx.error||new Error("Falha ao gravar o arquivo."));};tx.onabort=function(){reject(tx.error||new Error("Gravação cancelada."));};
  });
  input.value="";$("referenceTitle").value="";
  await renderReferenceList();
  toast(files.length+" referência(s) guardada(s) neste aparelho.");
 }catch(error){$("referenceStatus").textContent="Não foi possível guardar: "+error.message;}
 finally{$("addReference").disabled=false;}
}
function jpegDataUrl(blob,time){
 return new Promise(function(resolve,reject){
  const url=URL.createObjectURL(blob);
  const cleanup=function(){URL.revokeObjectURL(url);};
  const renderSource=function(source,width,height){
   const maxSide=384,scale=Math.min(1,maxSide/Math.max(width,height));
   const w=Math.max(1,Math.round(width*scale)),h=Math.max(1,Math.round(height*scale));
   const canvas=document.createElement("canvas");canvas.width=w;canvas.height=h;
   const context=canvas.getContext("2d",{alpha:false});
   context.fillStyle="#ffffff";context.fillRect(0,0,w,h);context.drawImage(source,0,0,w,h);
   canvas.toBlob(function(output){cleanup();if(!output){reject(new Error("Falha ao reduzir uma referência visual."));return;}
    const reader=new FileReader();reader.onload=function(){resolve(String(reader.result).split(",")[1]||"");};reader.onerror=function(){reject(new Error("Falha ao codificar a imagem."));};reader.readAsDataURL(output);
   },"image/jpeg",0.52);
  };
  if(blob.type.startsWith("image/")){
   if("createImageBitmap" in window){createImageBitmap(blob).then(function(bitmap){renderSource(bitmap,bitmap.width,bitmap.height);if(bitmap.close)bitmap.close();}).catch(function(){cleanup();reject(new Error("Não foi possível abrir uma imagem."));});}
   else{const image=new Image();image.onload=function(){renderSource(image,image.naturalWidth,image.naturalHeight);};image.onerror=function(){cleanup();reject(new Error("Não foi possível abrir uma imagem."));};image.src=url;}
   return;
  }
  const video=document.createElement("video");video.preload="auto";video.muted=true;video.playsInline=true;video.src=url;
  let done=false;
  const fail=function(){if(done)return;done=true;cleanup();reject(new Error("Não foi possível ler os quadros deste vídeo."));};
  video.onerror=fail;
  video.onloadedmetadata=function(){
   const duration=Number.isFinite(video.duration)?video.duration:0;
   const target=Math.max(0,Math.min(Math.max(0,duration-.05),Number(time)||0));
   video.onseeked=function(){if(done)return;done=true;renderSource(video,video.videoWidth||384,video.videoHeight||216);};
   try{video.currentTime=target;if(video.readyState>=2&&target===0)video.onseeked();}catch(error){fail();}
  };
  video.load();
 });
}
async function buildReferencePayload(){
 const references=await getStoredReferences();
 const notes=references.slice(0,16).map(function(item,index){
  return (index+1)+". "+item.title+" ["+(item.type==="image"?"imagem":"vídeo")+"]"+(item.note?" — nota: "+item.note:"");
 }).join("\n").slice(0,5000);
 const images=[];
 let approximateChars=0;
 for(const reference of references){
  if(images.length>=4)break;
  try{
   if(reference.type==="image"){
    const encoded=await jpegDataUrl(reference.blob,0);
    if(encoded&&approximateChars+encoded.length<560000){images.push(encoded);approximateChars+=encoded.length;}
   }else{
    const video=document.createElement("video");video.preload="metadata";video.muted=true;video.src=URL.createObjectURL(reference.blob);
    const metadata=await new Promise(function(resolve,reject){
     const timer=setTimeout(function(){reject(new Error("Tempo limite ao ler vídeo."));},5000);
     video.onloadedmetadata=function(){clearTimeout(timer);resolve(Number.isFinite(video.duration)?video.duration:0);};
     video.onerror=function(){clearTimeout(timer);reject(new Error("Falha ao abrir vídeo."));};
     video.load();
    }).catch(function(){return 0;});
    if(video.src.startsWith("blob:"))URL.revokeObjectURL(video.src);
    if(metadata>0){
     for(const fraction of [0.15,0.55,0.9]){
      if(images.length>=4)break;
      const encoded=await jpegDataUrl(reference.blob,metadata*fraction).catch(function(){return "";});
      if(encoded&&approximateChars+encoded.length<560000){images.push(encoded);approximateChars+=encoded.length;}
     }
    }else{
     const encoded=await jpegDataUrl(reference.blob,0).catch(function(){return "";});
     if(encoded&&approximateChars+encoded.length<560000){images.push(encoded);approximateChars+=encoded.length;}
    }
   }
  }catch(error){console.warn("A referência foi mantida, mas não virou um quadro visual:",error);}
 }
 return {reference_notes:notes,reference_images:images};
}
$("referenceFiles").addEventListener("change",function(){
 const files=Array.from($("referenceFiles").files||[]);
 if(files.length===1&& !$("referenceTitle").value.trim())$("referenceTitle").value=files[0].name;
 $("referenceStatus").textContent=files.length?files.length+" arquivo(s) selecionado(s); clique em Guardar para mantê-los neste aparelho.":"Nenhum arquivo selecionado.";
});
$("addReference").addEventListener("click",saveSelectedReferences);
$("planWithReferences").addEventListener("click",function(){
 $("aiPrompt").value="Estude minhas referências visuais e notas. Ensine-me a transformar minha ideia em uma cena FORGE: descreva o que realmente observou, faça um storyboard curto, defina poses-chave e timing, gere um script válido e proponha um exercício pequeno. Não invente detalhes ausentes. Minha ideia: ";
 panelView("ai");$("aiPrompt").focus();$("aiPrompt").setSelectionRange($("aiPrompt").value.length,$("aiPrompt").value.length);toast("Escreva sua ideia depois de “Minha ideia:” e envie um Brainstorm.");
});
renderReferenceList();

requestAnimationFrame(animate);}
document.querySelectorAll(".viewtab").forEach(function(el){el.addEventListener("click",function(){activeView(el.dataset.view);});});document.querySelectorAll(".righttab").forEach(function(el){el.addEventListener("click",function(){panelView(el.dataset.panel);});});
$("frameSlider").addEventListener("input",function(e){frame=Number(e.target.value);renderTimeline();draw2d();drawThree();refreshInspector();});$("playBtn").addEventListener("click",function(){playing=!playing;if(playing){startedAt=performance.now();startFrame=frame;$("playBtn").textContent="Ⅱ";}else $("playBtn").textContent="▶";});$("firstBtn").addEventListener("click",function(){frame=0;renderTimeline();draw2d();drawThree();refreshInspector();});$("lastBtn").addEventListener("click",function(){frame=findSceneDuration(project);renderTimeline();draw2d();drawThree();refreshInspector();});$("selectedObject").addEventListener("change",function(e){selected=e.target.value;refreshAll();});$("propColor").addEventListener("input",function(e){$("colorValue").textContent=e.target.value.toUpperCase();});$("applyProps").addEventListener("click",applyProps);$("addBtn").addEventListener("click",addCircle);$("newBtn").addEventListener("click",newProject);$("saveBtn").addEventListener("click",exportProject);$("exportBtn").addEventListener("click",exportCode);$("openBtn").addEventListener("click",function(){$("openFile").click();});$("openFile").addEventListener("change",function(e){openFile(e.target.files&&e.target.files[0]);});$("brainstormBtn").addEventListener("click",function(){runAI("brainstorm");});$("sendBtn").addEventListener("click",function(){runAI("assistant");});$("searchBtn").addEventListener("click",searchWeb);$("trainBtn").addEventListener("click",trainStudent);$("aiPrompt").addEventListener("keydown",function(e){if(e.key==="Enter"&&(e.ctrlKey||e.metaKey))runAI("assistant");});$("fitBtn").addEventListener("click",function(){draw2d();resizeThree();drawThree();toast("Preview reajustado.");});sourceEditor.addEventListener("input",function(){saveState("Alterações não exportadas");$("lineCount").textContent=sourceEditor.value.split(/\r?\n/).length+" LINHAS";});
refreshAll();initThree();fetch("/api/status").then(function(r){return r.json();}).then(function(data){$("modelTitle").textContent=data.student_ready?"Aluno local treinado":"IA local preparada";$("modelInfo").textContent=data.student_ready?"Checkpoint de 250K detectado.":"Modelos-professores são opcionais e precisam estar instalados.";}).catch(function(){$("modelTitle").textContent="Editor offline";$("modelInfo").textContent="Inicie python server.py para IA, pesquisa e treino.";});window.addEventListener("resize",function(){resizeThree();drawThree();});requestAnimationFrame(animate);
