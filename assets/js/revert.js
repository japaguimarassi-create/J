(function(){"use strict";
var form=document.getElementById("revert-form"),result=document.getElementById("revert-result");if(!form||!result)return;
form.addEventListener("submit",function(e){
e.preventDefault();var current=document.getElementById("current-fw").value,previous=document.getElementById("previous-fw").value,dumps=document.getElementById("dumps").value,hdd=document.getElementById("hdd").value,tech=document.getElementById("tech").value,title,body,kind="warn";
if(current!=="14.02"){title="Este módulo foi preparado para 14.02.";body="O firmware informado não é 14.02. Consulte as referências para a versão correta.";}
else if(previous==="no"){title="14.00 não foi informado como firmware anterior imediato.";body="A reversão depende do estado dos slots e dos dados específicos desta unidade. Não há downgrade por PUP USB, DNS ou troca de HDD.";}
else if(previous==="yes"&&tech==="yes"&&(dumps==="yes"||hdd==="yes")){title="Pode valer uma avaliação profissional — sem garantia.";body="As respostas indicam histórico potencialmente relevante. Um técnico ainda precisa verificar slots, correspondência dos dados e compatibilidade do Syscon. Este resultado não aprova escrita de flash.";kind="good";}
else{title="Elegibilidade não demonstrada.";body="Faltam dados sobre o firmware anterior, backups ou avaliação técnica. Esta página não consegue ler NOR, Syscon ou slots internos. Não tente instalar PUP antigo.";}
result.className="result-box "+kind;result.innerHTML="<b>"+title+"</b><p>"+body+"</p>";
});
form.addEventListener("reset",function(){result.className="result-box";result.innerHTML="<b>Aguardando respostas.</b><p>Este formulário não acessa Syscon ou NOR e não realiza escrita.</p>";});
})();