(function(){"use strict";
var root=document.documentElement;
try{var saved=localStorage.getItem("hen-theme");if(saved==="light"||saved==="dark")root.setAttribute("data-theme",saved);}catch(e){}
var themeButton=document.getElementById("theme-toggle");
if(themeButton)themeButton.addEventListener("click",function(){var next=root.getAttribute("data-theme")==="light"?"dark":"light";root.setAttribute("data-theme",next);try{localStorage.setItem("hen-theme",next);}catch(e){}});
var menuButton=document.querySelector(".menu-toggle"),menu=document.querySelector(".main-nav");
if(menuButton&&menu)menuButton.addEventListener("click",function(){var open=menu.classList.toggle("open");menuButton.setAttribute("aria-expanded",String(open));});
var ua=navigator.userAgent||"",ps4Match=ua.match(/PlayStation 4[ \/]([0-9]+\.[0-9]+)/i),fwHint=ps4Match?ps4Match[1]:"";
var device=document.getElementById("browser-device"),hint=document.getElementById("browser-firmware-hint"),engine=document.getElementById("browser-engine-hint"),details=document.getElementById("browser-ua-details");
var webkit=ua.match(/AppleWebKit\/([0-9.]+)/i);
if(device)device.textContent=ps4Match?"PlayStation browser detected":"Browser not identified as PS4";
if(hint)hint.textContent=fwHint?fwHint+" (User-Agent hint only)":"Not exposed by this User-Agent";
if(engine)engine.textContent=webkit?"WebKit "+webkit[1]:"Engine token unavailable";
if(details)details.textContent=ua||"User-Agent unavailable";
var firmwareInput=document.getElementById("firmware-input"),firmwareBadge=document.getElementById("firmware-detected"),firmwareResult=document.getElementById("firmware-result"),g2allSlot=document.getElementById("g2all-launch-slot");
if(firmwareInput&&fwHint)firmwareInput.value=fwHint;
if(g2allSlot)g2allSlot.hidden=true;
var firmwareForm=document.getElementById("firmware-form");
if(firmwareForm)firmwareForm.addEventListener("submit",function(event){
event.preventDefault();var value=(firmwareInput.value||"").trim();
if(!/^\d{1,2}\.\d{1,2}$/.test(value)){firmwareBadge.textContent="VERSION: INVALID";firmwareResult.textContent="Enter a version like 14.00 or 14.02.";if(g2allSlot)g2allSlot.hidden=true;return;}
value=value.replace(/^0+(?=\d)/,"");firmwareBadge.textContent="USER CONFIRMED: "+value;
if(g2allSlot)g2allSlot.hidden=value!=="14.00";
if(value==="14.00"){firmwareResult.textContent="14.00 confirmed. The real GamerHack G2All host has a dedicated route. Open it to let its own launcher check the console.";firmwareResult.style.color="var(--green)";}
else if(value==="14.02"){firmwareResult.textContent="14.02 BLOCKED: G2All stops at 14.00; the public 14.00 kernel route is patched on 14.02. No payload will be started.";firmwareResult.style.color="var(--red)";}
else{firmwareResult.textContent="Version "+value+" recorded. This project only links to the G2All public route for 14.00.";firmwareResult.style.color="var(--muted)";}
});
if("serviceWorker" in navigator&&location.protocol!=="file:"){window.addEventListener("load",function(){navigator.serviceWorker.register("sw.js").catch(function(){});});}
function focusables(){var nodes=document.querySelectorAll("a[href],button:not([disabled]),input:not([disabled]),textarea:not([disabled]),select:not([disabled])"),out=[];for(var i=0;i<nodes.length;i++){var r=nodes[i].getBoundingClientRect();if(r.width>0&&r.height>0)out.push(nodes[i]);}return out;}
document.addEventListener("keydown",function(event){var active=document.activeElement,tag=active&&active.tagName?active.tagName.toLowerCase():"";if(tag==="input"||tag==="textarea"||tag==="select")return;var key=event.key;if(key==="ArrowDown"||key==="ArrowRight"||key==="ArrowUp"||key==="ArrowLeft"){var list=focusables();if(!list.length)return;var index=-1;for(var i=0;i<list.length;i++)if(list[i]===active)index=i;var delta=(key==="ArrowDown"||key==="ArrowRight")?1:-1;var next=index<0?0:(index+delta+list.length)%list.length;event.preventDefault();list[next].focus();}
else if(key==="Escape"||key==="Backspace"){if(menu&&menu.classList.contains("open")){menu.classList.remove("open");if(menuButton){menuButton.setAttribute("aria-expanded","false");menuButton.focus();}}else if(history.length>1)history.back();}
});
})();