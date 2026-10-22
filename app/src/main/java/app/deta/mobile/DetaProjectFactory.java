package app.deta.mobile;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

final class DetaProjectFactory {
    enum Kind { GAME, SOCIAL, UTILITY }

    static final class Project {
        final String title;
        final String kind;
        final String prompt;
        final String summary;
        final Map<String, String> files;
        final byte[] zip;

        Project(String title, String kind, String prompt, String summary, Map<String, String> files, byte[] zip) {
            this.title = title;
            this.kind = kind;
            this.prompt = prompt;
            this.summary = summary;
            this.files = files;
            this.zip = zip;
        }

        String previewHtml() {
            String html = files.get("index.html");
            html = html.replace("<link rel=\"stylesheet\" href=\"style.css\">", "<style>" + files.get("style.css") + "</style>");
            return html.replace("<script src=\"app.js\"></script>", "<script>" + files.get("app.js") + "</script>");
        }

        String fileList() {
            StringBuilder value = new StringBuilder();
            for (String file : files.keySet()) {
                if (value.length() > 0) value.append(" · ");
                value.append(file);
            }
            return value.toString();
        }
    }

    private static final Pattern NAMED = Pattern.compile("(?iu)(?:chamado|chamada|com o nome|nomeado|nomeada)\\s+[\"“]?([\\p{L}\\p{N}][^\"”\\n,.]{0,38})");

    private DetaProjectFactory() {
    }

    static Project create(String rawPrompt) throws IOException {
        String prompt = rawPrompt == null ? "" : rawPrompt.trim();
        if (prompt.isEmpty()) throw new IllegalArgumentException("Descreva o app ou jogo que quer criar.");
        if (prompt.length() > 3000) throw new IllegalArgumentException("O pedido deve ter até 3.000 caracteres.");
        String normalized = normalize(prompt);
        Kind kind = detectKind(normalized);
        String title = detectTitle(prompt, kind);
        String slug = slug(title);
        Map<String, String> files = new LinkedHashMap<>();

        if (kind == Kind.GAME) {
            files.put("index.html", gameHtml(title, prompt));
            files.put("style.css", gameCss());
            files.put("app.js", gameJs(slug));
        } else if (kind == Kind.SOCIAL) {
            files.put("index.html", socialHtml(title, prompt));
            files.put("style.css", socialCss());
            files.put("app.js", socialJs(slug));
        } else {
            files.put("index.html", utilityHtml(title, prompt));
            files.put("style.css", utilityCss());
            files.put("app.js", utilityJs(slug));
        }

        String summary = kind == Kind.GAME
                ? "Jogo de navegador com pontuação, rodada de 30 segundos, suporte a toque e recorde local."
                : kind == Kind.SOCIAL
                ? "Protótipo social com publicações, busca, curtidas, comentários e armazenamento local."
                : "Aplicativo utilitário com itens, marcação de conclusão, exclusão e armazenamento local.";
        files.put("README.md", readme(title, prompt, summary, files.keySet()));
        String metadata = "{\n"
                + "  \"name\": \"" + jsonEscape(title) + "\",\n"
                + "  \"kind\": \"" + jsonEscape(kind.name().toLowerCase(Locale.ROOT)) + "\",\n"
                + "  \"brief\": \"" + jsonEscape(prompt) + "\",\n"
                + "  \"generator\": \"Deta local neural assistant + structured project builder\",\n"
                + "  \"neural_model_parameters\": " + DetaLocalModel.PARAMETER_COUNT + ",\n"
                + "  \"network_api_required\": false\n"
                + "}\n";
        files.put("project.json", metadata);

        byte[] zip = createZip(files);
        return new Project(title, kind.name().toLowerCase(Locale.ROOT), prompt, summary, files, zip);
    }

    private static Kind detectKind(String text) {
        if (containsAny(text, "jogo", "game", "plataforma", "runner", "arcade", "rpg", "aventura", "tiro", "puzzle")) return Kind.GAME;
        if (containsAny(text, "rede social", "social", "comunidade", "feed", "publicacoes", "publicacao", "chat", "mensagens", "seguidores")) return Kind.SOCIAL;
        return Kind.UTILITY;
    }

    private static boolean containsAny(String value, String... terms) {
        for (String term : terms) if (value.contains(term)) return true;
        return false;
    }

    private static String detectTitle(String prompt, Kind kind) {
        Matcher matcher = NAMED.matcher(prompt);
        if (matcher.find()) {
            String name = matcher.group(1).trim().replaceAll("\\s+", " ");
            name = name.replaceFirst("(?iu)\\s+(?:com|para|que tenha|com suporte a|e com)\\s+.*$", "").trim();
            if (!name.isEmpty()) return name.length() > 39 ? name.substring(0, 39).trim() : name;
        }
        if (kind == Kind.GAME) return "Jogo Deta";
        if (kind == Kind.SOCIAL) return "Comunidade Deta";
        return "App Deta";
    }

    private static String slug(String value) {
        String result = normalize(value).replaceAll("[^a-z0-9]+", "-").replaceAll("^-|-$", "");
        return result.isEmpty() ? "deta-project" : result;
    }

    private static String normalize(String value) {
        return Normalizer.normalize(value.toLowerCase(Locale.ROOT), Normalizer.Form.NFD)
                .replaceAll("\\p{M}+", "").replaceAll("\\s+", " ").trim();
    }

    private static String jsonEscape(String value) {
        StringBuilder escaped = new StringBuilder(value.length() + 16);
        for (int index = 0; index < value.length(); index++) {
            char ch = value.charAt(index);
            switch (ch) {
                case '"': escaped.append("\\\""); break;
                case '\\': escaped.append("\\\\"); break;
                case '\b': escaped.append("\\b"); break;
                case '\f': escaped.append("\\f"); break;
                case '\n': escaped.append("\\n"); break;
                case '\r': escaped.append("\\r"); break;
                case '\t': escaped.append("\\t"); break;
                default:
                    if (ch < 0x20) {
                        escaped.append(String.format(Locale.ROOT, "\\u%04x", (int) ch));
                    } else {
                        escaped.append(ch);
                    }
            }
        }
        return escaped.toString();
    }

    private static String esc(String value) {
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                .replace("\"", "&quot;").replace("'", "&#39;");
    }

    private static String header(String title, String subtitle) {
        return "<header class=\"top\"><div class=\"mark\">D</div><div><p class=\"eyebrow\">PROJETO GERADO LOCALMENTE</p><h1>"
                + esc(title) + "</h1><p class=\"sub\">" + esc(subtitle) + "</p></div></header>";
    }

    private static String gameHtml(String title, String prompt) {
        return "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
                + "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
                + "<title>" + esc(title) + "</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><main class=\"shell\">"
                + header(title, "Jogo jogável criado a partir do seu pedido: " + prompt)
                + "<section class=\"hero\"><div class=\"stats\"><div><span>PONTOS</span><strong id=\"score\">0</strong></div>"
                + "<div><span>TEMPO</span><strong id=\"time\">30</strong></div><div><span>RECORDE</span><strong id=\"best\">0</strong></div></div>"
                + "<div class=\"arena\" id=\"arena\"><button id=\"target\" class=\"target\" aria-label=\"Alvo\">+</button>"
                + "<div id=\"cover\" class=\"cover\"><h2 id=\"status\">Pronto?</h2><p id=\"info\">Toque nos alvos antes de o tempo acabar.</p>"
                + "<button id=\"start\" class=\"primary\">Começar</button></div></div></section>"
                + "<footer>Projeto offline · sem API de IA · recorde salvo neste navegador</footer></main><script src=\"app.js\"></script></body></html>";
    }

    private static String gameCss() {
        return ":root{color-scheme:dark;--bg:#090a12;--panel:#141725;--line:#2c3247;--text:#f4f5ff;--muted:#9da5bd;--accent:#aaa4ff;--green:#73e0bd;font-family:system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#1a2040,#090a12 65%);color:var(--text);min-height:100vh}.shell{max-width:860px;margin:auto;padding:22px 18px}.top{display:flex;gap:13px;align-items:center}.mark{width:46px;height:46px;border-radius:15px;background:var(--accent);display:grid;place-items:center;color:#101020;font-weight:900;font-size:23px}.eyebrow{font-size:10px;letter-spacing:.14em;color:var(--accent);font-weight:800;margin:0 0 5px}.top h1{font-size:clamp(22px,5vw,32px);margin:0}.sub{color:var(--muted);line-height:1.45}.hero{margin-top:24px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:12px}.stats div{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:15px}.stats span{display:block;color:var(--muted);font-size:10px}.stats strong{font-size:27px}.arena{height:min(56vh,430px);min-height:270px;position:relative;overflow:hidden;border-radius:22px;border:1px solid var(--line);background:radial-gradient(circle,#20294b,#101421)}button{font:inherit;font-weight:800;cursor:pointer;border:0;border-radius:13px;padding:12px 18px}.target{display:none;position:absolute;width:55px;height:55px;padding:0;border-radius:50%;background:var(--green);color:#061d19;font-size:32px;transform:translate(-50%,-50%)}.cover{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:20px;background:#080b19c9}.cover h2{font-size:27px;margin:0}.cover p{max-width:360px;color:var(--muted);line-height:1.55}.primary{background:var(--accent);color:#111121}footer{margin-top:22px;color:#7f879f;font-size:12px}";
    }

    private static String gameJs(String slug) {
        return "(()=>{const arena=document.getElementById('arena'),target=document.getElementById('target'),cover=document.getElementById('cover'),startButton=document.getElementById('start');"
                + "const scoreEl=document.getElementById('score'),timeEl=document.getElementById('time'),bestEl=document.getElementById('best'),key='" + slug + "-best';"
                + "let score=0,seconds=30,timer=null,playing=false,best=Number(localStorage.getItem(key)||0);bestEl.textContent=best;"
                + "function move(){const p=32,x=p+Math.random()*Math.max(1,arena.clientWidth-2*p),y=p+Math.random()*Math.max(1,arena.clientHeight-2*p);target.style.left=x+'px';target.style.top=y+'px'}"
                + "function finish(){playing=false;clearInterval(timer);target.style.display='none';cover.style.display='flex';document.getElementById('status').textContent='Fim de jogo';"
                + "document.getElementById('info').textContent='Pontos: '+score+' · Recorde: '+best;startButton.textContent='Jogar novamente'}"
                + "function start(){clearInterval(timer);score=0;seconds=30;playing=true;scoreEl.textContent=0;timeEl.textContent=30;cover.style.display='none';target.style.display='block';move();"
                + "timer=setInterval(()=>{seconds--;timeEl.textContent=seconds;if(seconds<=0)finish()},1000)}"
                + "target.addEventListener('pointerdown',e=>{e.preventDefault();if(!playing)return;score++;scoreEl.textContent=score;if(score>best){best=score;bestEl.textContent=best;localStorage.setItem(key,best)}move()});"
                + "startButton.addEventListener('click',start);document.addEventListener('keydown',e=>{if(e.key.toLowerCase()==='r')start()});window.addEventListener('resize',()=>{if(playing)move()})})();";
    }

    private static String socialHtml(String title, String prompt) {
        return "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
                + "<title>" + esc(title) + "</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><main class=\"shell\">"
                + header(title, "Protótipo de comunidade baseado no pedido: " + prompt)
                + "<section class=\"composer\"><label for=\"post\">Compartilhe uma ideia</label><textarea id=\"post\" maxlength=\"2000\" placeholder=\"Escreva algo para a comunidade\"></textarea>"
                + "<button id=\"publish\" class=\"primary\">Publicar</button></section><header class=\"feedhead\"><h2>Feed</h2><input id=\"search\" placeholder=\"Buscar publicações\"></header>"
                + "<section id=\"feed\" class=\"feed\"></section><footer>Publicações guardadas somente neste navegador. Não há contas remotas.</footer></main><script src=\"app.js\"></script></body></html>";
    }

    private static String socialCss() {
        return ":root{color-scheme:dark;--bg:#090a12;--panel:#141725;--line:#2d3349;--text:#f4f5ff;--muted:#a1a8bd;--accent:#aaa4ff;font-family:system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text)}.shell{max-width:760px;margin:auto;padding:24px 16px}.top{display:flex;gap:12px;align-items:center}.mark{width:44px;height:44px;display:grid;place-items:center;border-radius:14px;background:var(--accent);color:#111;font-weight:900}.eyebrow{font-size:10px;letter-spacing:.13em;color:var(--accent);margin:0 0 5px}.top h1{margin:0;font-size:27px}.sub{color:var(--muted);line-height:1.5}.composer,.post{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;margin-top:22px}.composer label{display:block;font-weight:700;margin-bottom:10px}textarea,input{font:inherit;color:var(--text);background:#0d1020;border:1px solid var(--line);border-radius:12px;padding:12px;width:100%}textarea{min-height:90px;display:block;margin-bottom:10px;resize:vertical}.primary{background:var(--accent);color:#101020;border:0;border-radius:12px;padding:11px 16px;font:inherit;font-weight:800}.feedhead{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-top:24px}.feedhead h2{font-size:20px}.feedhead input{max-width:55%}.feed{display:grid;gap:10px}.post p{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}.actions{display:flex;gap:8px}.actions button{flex:1;color:var(--muted);background:transparent;border:1px solid var(--line);border-radius:10px;padding:9px}footer{margin-top:25px;color:#7f879f;font-size:12px;line-height:1.5}";
    }

    private static String socialJs(String slug) {
        return "(()=>{const key='" + slug + "-posts',input=document.getElementById('post'),feed=document.getElementById('feed'),search=document.getElementById('search');let posts=[];"
                + "try{const v=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(v))posts=v}catch(e){}"
                + "function save(){localStorage.setItem(key,JSON.stringify(posts))}function button(t,fn){const b=document.createElement('button');b.textContent=t;b.addEventListener('click',fn);return b}"
                + "function render(){const q=search.value.trim().toLowerCase();feed.replaceChildren();const visible=posts.filter(p=>p.text.toLowerCase().includes(q));"
                + "if(!visible.length){const e=document.createElement('div');e.className='post';e.textContent='Nenhuma publicação. Escreva a primeira acima.';feed.append(e);return}"
                + "visible.forEach(p=>{const card=document.createElement('article');card.className='post';const meta=document.createElement('small');meta.textContent=new Date(p.date).toLocaleString('pt-BR');const text=document.createElement('p');text.textContent=p.text;"
                + "const actions=document.createElement('div');actions.className='actions';actions.append(button('♥ '+p.likes,()=>{p.likes++;save();render()}),button('Comentar',()=>{const c=prompt('Comentário');if(c&&c.trim()){p.comments.push(c.trim().slice(0,500));save();render()}}),button('Excluir',()=>{if(confirm('Excluir publicação?')){posts=posts.filter(x=>x.id!==p.id);save();render()}}));"
                + "if(p.comments.length){const comments=document.createElement('small');comments.textContent='Comentários: '+p.comments.join(' · ');card.append(meta,text,comments,actions)}else card.append(meta,text,actions);feed.append(card)})}"
                + "document.getElementById('publish').addEventListener('click',()=>{const value=input.value.trim();if(!value)return;posts.unshift({id:Date.now()+Math.random(),text:value,date:Date.now(),likes:0,comments:[]});input.value='';save();render()});search.addEventListener('input',render);render()})();";
    }

    private static String utilityHtml(String title, String prompt) {
        return "<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
                + "<title>" + esc(title) + "</title><link rel=\"stylesheet\" href=\"style.css\"></head><body><main class=\"shell\">"
                + header(title, "Aplicativo utilitário gerado a partir do pedido: " + prompt)
                + "<section class=\"composer\"><label for=\"task\">Novo item</label><div class=\"newtask\"><input id=\"task\" maxlength=\"300\" placeholder=\"Escreva uma tarefa ou anotação\">"
                + "<button id=\"add\" class=\"primary\">Adicionar</button></div></section><section class=\"toolbar\"><h2>Minha lista</h2><button id=\"clear\">Limpar concluídos</button></section>"
                + "<section id=\"items\" class=\"items\"></section><footer>Seus itens ficam salvos localmente no navegador.</footer></main><script src=\"app.js\"></script></body></html>";
    }

    private static String utilityCss() {
        return ":root{color-scheme:dark;--bg:#090a12;--panel:#141725;--line:#2d3349;--text:#f4f5ff;--muted:#a1a8bd;--accent:#aaa4ff;font-family:system-ui,sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text)}.shell{max-width:760px;margin:auto;padding:24px 16px}.top{display:flex;gap:12px;align-items:center}.mark{width:44px;height:44px;display:grid;place-items:center;border-radius:14px;background:var(--accent);color:#111;font-weight:900}.eyebrow{font-size:10px;letter-spacing:.13em;color:var(--accent);margin:0 0 5px}.top h1{margin:0;font-size:27px}.sub{color:var(--muted);line-height:1.5}.composer,.item{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:16px;margin-top:16px}.composer label{display:block;margin-bottom:10px;font-weight:700}.newtask{display:flex;gap:8px}input{min-width:0;flex:1;font:inherit;color:var(--text);background:#0d1020;border:1px solid var(--line);border-radius:12px;padding:12px}.primary,.toolbar button,.item button{background:var(--accent);color:#101020;border:0;border-radius:10px;padding:10px 12px;font:inherit;font-weight:700}.toolbar{display:flex;justify-content:space-between;align-items:center;margin-top:18px}.toolbar h2{font-size:20px}.items{display:grid;gap:8px}.item{display:flex;align-items:center;gap:10px;margin:0}.item span{flex:1;overflow-wrap:anywhere}.item.done span{text-decoration:line-through;color:var(--muted)}.item input{flex:0 0 auto;width:20px;height:20px}.item button{background:#2b3045;color:var(--text)}footer{margin-top:25px;color:#7f879f;font-size:12px}";
    }

    private static String utilityJs(String slug) {
        return "(()=>{const key='" + slug + "-items',input=document.getElementById('task'),items=document.getElementById('items');let data=[];try{const v=JSON.parse(localStorage.getItem(key)||'[]');if(Array.isArray(v))data=v}catch(e){}"
                + "function save(){localStorage.setItem(key,JSON.stringify(data))}function render(){items.replaceChildren();if(!data.length){const e=document.createElement('div');e.className='item';e.textContent='Ainda não há itens. Adicione o primeiro acima.';items.append(e);return}"
                + "data.forEach(task=>{const row=document.createElement('div');row.className='item'+(task.done?' done':'');const check=document.createElement('input');check.type='checkbox';check.checked=task.done;check.addEventListener('change',()=>{task.done=check.checked;save();render()});const text=document.createElement('span');text.textContent=task.text;const remove=document.createElement('button');remove.textContent='Excluir';remove.addEventListener('click',()=>{data=data.filter(x=>x.id!==task.id);save();render()});row.append(check,text,remove);items.append(row)})}"
                + "function add(){const text=input.value.trim();if(!text)return;data.unshift({id:Date.now()+Math.random(),text,done:false});input.value='';save();render()}document.getElementById('add').addEventListener('click',add);input.addEventListener('keydown',e=>{if(e.key==='Enter')add()});document.getElementById('clear').addEventListener('click',()=>{data=data.filter(x=>!x.done);save();render()});render()})();";
    }

    private static String readme(String title, String prompt, String summary, Iterable<String> paths) {
        StringBuilder list = new StringBuilder();
        for (String path : paths) list.append("- ").append(path).append('\n');
        return "# " + title + "\n\n" + summary + "\n\nPedido original:\n" + prompt
                + "\n\nArquivos:\n" + list
                + "\n\nAbra index.html num navegador moderno. Este projeto inicial funciona sem servidor e sem API de IA. "
                + "A Deta combina o checkpoint neural local com um construtor estruturado; o modelo continua experimental e o código gerado deve ser testado antes de publicação.\n";
    }

    private static byte[] createZip(Map<String, String> files) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (ZipOutputStream zip = new ZipOutputStream(bytes)) {
            for (Map.Entry<String, String> file : files.entrySet()) {
                ZipEntry entry = new ZipEntry(file.getKey());
                zip.putNextEntry(entry);
                zip.write(file.getValue().getBytes(StandardCharsets.UTF_8));
                zip.closeEntry();
            }
        }
        return bytes.toByteArray();
    }
}
