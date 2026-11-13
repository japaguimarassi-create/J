"use strict";
const CACHE="ps4-1402-lab-v1.4.0";
const FILES=["./","./index.html","./manifest.webmanifest","./health.json","./evidence.json","./firmware-delta.json","./firmware-delta.js"];
self.addEventListener("install",event=>event.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES)).then(()=>self.skipWaiting())));
self.addEventListener("activate",event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith("ps4-1402-lab-")&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener("fetch",event=>{
  const request=event.request;
  if(request.method!=="GET")return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin)return;
  if(request.mode==="navigate"){
    event.respondWith(fetch(request).then(response=>{if(response.ok)caches.open(CACHE).then(c=>c.put("./index.html",response.clone()));return response}).catch(()=>caches.match("./index.html")));
    return;
  }
  const cacheKey=new Request(url.origin+url.pathname);
  event.respondWith(caches.match(cacheKey).then(hit=>hit||fetch(request).then(response=>{
    if(response.ok)caches.open(CACHE).then(c=>c.put(cacheKey,response.clone()));
    return response;
  })));
});
