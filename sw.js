var CACHE="hen-research-v2";
var FILES=["./","index.html","compatibility.html","research.html","goldhen.html","offline.html","assets/css/app.css","assets/js/app.js","manifest.json"];
self.addEventListener("install",function(e){
  e.waitUntil(caches.open(CACHE).then(function(cache){return cache.addAll(FILES)}));
  self.skipWaiting();
});
self.addEventListener("activate",function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(key){
      return key.indexOf("hen-research-")===0 && key!==CACHE;
    }).map(function(key){return caches.delete(key)}));
  }));
  self.clients.claim();
});
self.addEventListener("fetch",function(e){
  if(e.request.method!=="GET")return;
  e.respondWith(caches.open(CACHE).then(function(cache){
    return cache.match(e.request).then(function(hit){
      if(hit)return hit;
      return fetch(e.request).then(function(response){
        if(response&&response.ok&&new URL(e.request.url).origin===location.origin){
          cache.put(e.request,response.clone());
        }
        return response;
      }).catch(function(){return cache.match("offline.html")});
    });
  }));
});