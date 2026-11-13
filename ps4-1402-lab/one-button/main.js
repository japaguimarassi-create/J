"use strict";
(function () {
  var button=document.getElementById("start"),state=document.getElementById("state"),detail=document.getElementById("detail"),bar=document.getElementById("bar"),reportPanel=document.getElementById("reportPanel"),reportField=document.getElementById("report");
  var cacheName="jbhereps4-host-v9";
  var assets=["./","./index.html","./main.js","./probe.js","./sw.js","./cache.appcache","./manifest.webmanifest","./evidence.json"];
  var busy=false;
  function show(title,message,tone,percent){state.textContent=title;state.className=tone||"";detail.textContent=message;bar.style.width=String(percent||0)+"%";}
  function save(k,v){try{localStorage.setItem(k,v);}catch(e){}}
  function read(k){try{return localStorage.getItem(k);}catch(e){return null;}}
  function log(lines,msg){lines.push(new Date().toISOString()+" "+msg);}
  async function prepareOffline(lines){
    show("PREPARANDO CACHE","Armazenando os módulos do laboratório para uso offline.","",5);
    var cached=[];
    if("serviceWorker" in navigator&&window.isSecureContext){try{await navigator.serviceWorker.register("./sw.js");await navigator.serviceWorker.ready;log(lines,"Service Worker registrado.");}catch(e){log(lines,"Service Worker indisponível: "+e.message);}}
    if("caches" in window){try{var cache=await caches.open(cacheName);for(var i=0;i<assets.length;i++){try{var r=await fetch(assets[i],{cache:"reload"});if(!r.ok)throw new Error("HTTP "+r.status);await cache.put(assets[i],r.clone());cached.push(assets[i]);}catch(e){log(lines,"Cache "+assets[i]+": "+e.message);}show("CACHE "+(i+1)+"/"+assets.length,"Preparando os recursos locais.", "",5+Math.round((i+1)/assets.length*60));}}catch(e){log(lines,"Cache API: "+e.message);}}
    var complete=cached.length===assets.length;save("jbhereps4:prepared",complete?"7":"partial");log(lines,"Arquivos em cache: "+cached.length+"/"+assets.length);return complete;
  }
  async function readEvidence(){var r=await fetch("./evidence.json",{cache:"no-store"});if(!r.ok)throw new Error("Evidências HTTP "+r.status);return r.json();}
  async function postJSON(payload){var r=await fetch("./api/metadata",{method:"POST",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify(payload),cache:"no-store"});var data;try{data=await r.json();}catch(e){throw new Error("Backend retornou JSON inválido.");}if(!r.ok||!data.ok)throw new Error(data.error||("HTTP "+r.status));return data;}
  async function uploadReport(probe,evidence){
    var payload={schema:"jbhereps4-client-report/1",timestamp:probe.timestamp,firmwareHint:probe.firmwareHint,webkitHint:probe.webkitHint,deviceClass:probe.deviceClass,online:probe.online,secureContext:probe.secureContext,capabilities:probe.capabilities,safeChecks:probe.safeChecks,testSummary:probe.testSummary,evidenceSummary:{firmware14_02PublicChain:evidence.firmware14_02.publicChain,goldhen14_02Supported:!!evidence.goldhen.firmware14_02Supported}};
    var check=await postJSON(Object.assign({},payload,{selfTest:true}));
    if(check.selfTest!=="passed"||check.access!=="private"||check.write!==true||check.read!==true||check.delete!==true)throw new Error("Autoteste de armazenamento não confirmou escrita, leitura e remoção.");
    var result=await postJSON(payload);
    return result;
  }
  async function runDiagnostics(lines){
    show("TESTANDO NAVEGADOR","Verificando somente APIs expostas pelo próprio navegador.","",68);
    if(!window.JBhereSafeProbe)throw new Error("probe.js não carregou.");
    var probe=window.JBhereSafeProbe.run(),evidence=await readEvidence();
    log(lines,"Classe do navegador: "+probe.deviceClass);
    log(lines,"Firmware exposto: "+probe.firmwareHint);
    log(lines,"WebKit exposto: "+probe.webkitHint);
    log(lines,"APIs disponíveis: "+probe.testSummary.supportedApiCount+"/"+probe.testSummary.totalApiCount);log(lines,"Testes seguros aprovados: "+probe.testSummary.safeChecksPassed+"/"+probe.testSummary.safeChecksTotal);
    log(lines,"Nenhuma primitiva de exploit foi executada.");
    var report={product:"JBherePS4",version:"1.5.1",timestamp:new Date().toISOString(),probe:probe,evidence:evidence,tests:{browserProbe:"completed",firmwareDetection:probe.firmwareHint==="not-exposed"?"not-exposed":"hint-only",exploitExecution:"not-run",kernelAccess:false,firmwareModification:false,backendStorage:"pending"},jailbreakStatus:"EXPERIMENTAL_PARTIAL_KERNEL_CLAIM_NO_USABLE_HEN_VERIFIED",goldhenStatus:"NOT_SUPPORTED_BY_VERIFIED_PUBLIC_RELEASE",conclusion:"Há um relato público experimental de acesso parcial ao kernel em 14.02, mas o mesmo registro informa kernel panic ao iniciar jogos e falha de inicialização de HEN/GoldHEN. O código consultado herda offsets de 14.00 com shiftfit e não demonstra validação independente. Não há jailbreak completo e reproduzível verificado neste laboratório. O teste não executa essa cadeia.",storage:{status:"uploading"},log:lines};
    save("jbhereps4:lastReport",JSON.stringify(report,null,2));
    show("VALIDANDO BACKEND","Testando gravação, leitura e exclusão de um JSON temporário antes de enviar o relatório.","",82);
    try{
      var stored=await uploadReport(probe,evidence);
      report.tests.backendStorage="private-write-read-delete-confirmed";
      report.storage={status:"stored",access:"private",id:stored.id,pathname:stored.pathname};
      log(lines,"Autoteste do Blob privado: escrita/leitura/remoção confirmadas.");
      log(lines,"Relatório privado recebido: "+stored.pathname);
      show("RELATÓRIO PRIVADO RECEBIDO","Backend confirmou escrita e leitura privadas em metadata/reports/. ID: "+stored.id,"good",100);
    }catch(e){
      report.tests.backendStorage="failed";
      report.storage={status:"upload_failed",error:String(e.message||e).slice(0,180)};
      log(lines,"Falha no backend: "+report.storage.error);
      show("RELATÓRIO LOCAL · BACKEND FALHOU","O JSON foi preservado no navegador. Nenhuma alteração foi feita no PS4. "+report.storage.error,"warn",100);
    }
    var serialized=JSON.stringify(report,null,2);save("jbhereps4:lastReport",serialized);save("jbhereps4:lastLog",JSON.stringify(lines));reportField.value=serialized;reportPanel.hidden=false;reportPanel.open=true;
    button.textContent=report.storage.status==="stored"?"EXECUTAR NOVAMENTE":"TENTAR ENVIO NOVAMENTE";button.disabled=false;busy=false;return report;
  }
  async function start(){
    if(busy)return;busy=true;button.disabled=true;var lines=[];log(lines,"JBherePS4 v1.5.0 iniciado.");
    try{
      if(read("jbhereps4:prepared")!=="7"){
        var complete=await prepareOffline(lines);
        log(lines,complete?"Cache offline completo.":"Cache parcial; continuando com os testes disponíveis.");
        show("CACHE PRONTO","Preparação concluída. Iniciando os testes nesta mesma sessão.","",66);
      }
      await runDiagnostics(lines);
    }catch(e){log(lines,"Interrupção segura: "+e.message);save("jbhereps4:lastLog",JSON.stringify(lines));show("TESTE INTERROMPIDO","Nenhuma alteração foi feita no console. "+e.message,"bad",0);button.disabled=false;button.textContent="TENTAR NOVAMENTE";busy=false;}
  }
  var previous=read("jbhereps4:lastReport");if(previous){reportField.value=previous;reportPanel.hidden=false;}
  button.addEventListener("click",start);
  if("serviceWorker" in navigator&&window.isSecureContext)window.addEventListener("load",function(){navigator.serviceWorker.register("./sw.js").catch(function(){});});
  if(read("jbhereps4:prepared")==="7")button.textContent="EXECUTAR TESTE NOVAMENTE";
})();