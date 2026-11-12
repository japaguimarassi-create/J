(function(){"use strict";
function storage(type){try{var s=type==="local"?localStorage:sessionStorage,k="hen14-test";s.setItem(k,"1");s.removeItem(k);return true;}catch(e){return false;}}
function row(name,ok,note){return '<div><b>'+name+'</b><span class="'+(ok?"ok":"warn")+'">'+(ok?"Disponível":"Não disponível")+(note?" · "+note:"")+'</span></div>';}
var button=document.getElementById("run-diagnostics");if(!button)return;
button.addEventListener("click",function(){
var checks=[["JavaScript",typeof window!=="undefined",""],["Local Storage",storage("local"),""],["Session Storage",storage("session"),""],["Fetch API",typeof window.fetch==="function",""],["URL API",typeof window.URL==="function",""],["Application Cache",!!window.applicationCache,"cache legado"],["Service Worker","serviceWorker" in navigator,"opcional"]];
var count=0,html="";for(var i=0;i<checks.length;i++){if(checks[i][1])count++;html+=row(checks[i][0],checks[i][1],checks[i][2]);}
document.getElementById("diagnostics-list").innerHTML=html;
document.getElementById("diagnostics-summary").innerHTML=count+"/"+checks.length+" recursos disponíveis. Isto não é um teste de exploit nem confirma jailbreak.";
});
})();