(function(){
"use strict";
function byId(id){return document.getElementById(id);}
var ua=navigator.userAgent||"",m=ua.match(/PlayStation 4[ \/]([0-9]+\.[0-9]+)/i);
if(!m)m=ua.match(/PlayStation 4([0-9]+\.[0-9]+)/i);
var version=m?m[1]:"",wk=ua.match(/AppleWebKit\/([0-9.]+)/i);
if(byId("profile-device"))byId("profile-device").innerHTML=m?"PlayStation 4 Browser":"Navegador não identificado como PS4";
if(byId("profile-firmware"))byId("profile-firmware").innerHTML=version?version+" (indicação UA)":"Não informado pelo User-Agent";
if(byId("profile-webkit"))byId("profile-webkit").innerHTML=wk?wk[1]:"Não identificado";
if(byId("profile-ua"))byId("profile-ua").innerHTML=ua||"User-Agent indisponível";
if(byId("profile-appcache"))byId("profile-appcache").innerHTML=window.applicationCache?"API disponível":"API ausente";
if(byId("profile-sw"))byId("profile-sw").innerHTML=("serviceWorker" in navigator)?"API disponível":"API ausente";
if(byId("firmware-input")&&version)byId("firmware-input").value=version;
if(byId("launch-fw")&&version)byId("launch-fw").value=version;
function checkVersion(value,result,slot){
value=(value||"").replace(/^\s+|\s+$/g,"");
if(!/^[0-9]{1,2}\.[0-9]{2}$/.test(value)){if(result)result.innerHTML="Digite a versão no formato 14.00 ou 14.02.";if(slot)slot.hidden=true;return;}
if(value==="14.02"){if(result)result.innerHTML="14.02: bloqueado. Não há cadeia pública userland/kernel confirmada.";if(slot)slot.hidden=true;return;}
if(value==="14.00"){if(result)result.innerHTML="14.00: existe uma rota pública no G2All. Confirme a versão no menu do PS4.";if(slot)slot.hidden=false;return;}
if(result)result.innerHTML="Versão registrada. Esta integração libera apenas a rota confirmada 14.00.";
if(slot)slot.hidden=true;
}
if(byId("firmware-form"))byId("firmware-form").addEventListener("submit",function(e){e.preventDefault();checkVersion(byId("firmware-input").value,byId("firmware-result"),byId("g2all-launch-slot"));});
if(byId("launch-form"))byId("launch-form").addEventListener("submit",function(e){
e.preventDefault();var value=byId("launch-fw").value,confirmed=byId("launch-confirm").checked,result=byId("launch-result"),action=byId("launch-action"),blocked=byId("launch-blocked");
action.hidden=true;blocked.hidden=true;
if(value==="14.02"){result.innerHTML="14.02 não possui cadeia pública confirmada. Nenhum exploit será iniciado.";blocked.hidden=false;return;}
if(value!=="14.00"){result.innerHTML="Esta integração libera apenas a rota 14.00.";return;}
if(!confirmed){result.innerHTML="Marque a confirmação após conferir Configurações → Sistema → Informações do sistema.";return;}
result.innerHTML="14.00 confirmado manualmente. Abra o host upstream real.";
action.hidden=false;
});
if(byId("offline-cache-status")){if(window.applicationCache)byId("offline-cache-status").innerHTML="Application Cache disponível. Estado interno: "+window.applicationCache.status+".";else byId("offline-cache-status").innerHTML="Application Cache não está disponível nesta sessão. Os arquivos ainda podem estar no cache normal do navegador.";}
if("serviceWorker" in navigator&&location.protocol!=="file:"){window.addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){});});}
})();