import html
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any


KINDS = {"browser-game", "social-app", "python-cli"}


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    if not slug:
        raise ValueError("Project name must contain at least one letter or number.")
    return slug[:60].rstrip("-")


def _browser_game() -> dict[str, str]:
    return {
        "index.html": r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#090a12">
  <title>__TITLE__</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="shell">
    <header class="topbar"><div class="mark">D</div><div><p class="eyebrow">PROJETO JOGÁVEL</p><h1>__TITLE__</h1></div><button id="reset" class="subtle">Reiniciar</button></header>
    <section class="hero"><p class="eyebrow">OBJETIVO</p><h2>Toque nos alvos para ganhar pontos.</h2><p>Você tem 30 segundos. Funciona com mouse, toque e teclado.</p></section>
    <section class="stats" aria-live="polite"><div><span>PONTOS</span><strong id="score">0</strong></div><div><span>TEMPO</span><strong id="time">30</strong></div><div><span>RECORDE</span><strong id="best">0</strong></div></section>
    <section class="arena-wrap"><div id="arena" class="arena" tabindex="0" aria-label="Área do jogo"><button id="target" class="target" aria-label="Alvo">+</button><div id="overlay" class="overlay"><div><h3>Pronto?</h3><p>Comece a partida e acerte o maior número de alvos.</p><button id="start" class="primary">Começar partida</button></div></div></div></section>
    <section class="tips"><span>TOQUE</span><span>R — REINICIAR</span><span>RECORDE SALVO NESTE DISPOSITIVO</span></section>
    <footer>__TITLE__ · projeto local sem API</footer>
  </main>
  <script src="game.js"></script>
</body>
</html>
""",
        "style.css": r""":root{color-scheme:dark;--bg:#090a12;--panel:#141725;--line:#2c3247;--text:#f4f5ff;--muted:#9da5bd;--accent:#aaa4ff;--green:#73e0bd;font-family:Inter,system-ui,-apple-system,sans-serif}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#19203b 0,#090a12 55%);color:var(--text);min-height:100vh}.shell{width:min(920px,100%);margin:auto;padding:24px clamp(16px,4vw,38px) 30px}.topbar{display:flex;align-items:center;gap:14px}.mark{width:48px;height:48px;border-radius:16px;background:linear-gradient(140deg,#a6a0ff,#7469ff);display:grid;place-items:center;font-weight:900;color:#080a18;font-size:24px}.eyebrow{font-size:10px;letter-spacing:.16em;color:var(--accent);font-weight:800;margin:0 0 5px}.topbar h1{margin:0;font-size:clamp(19px,4vw,27px)}button{font:inherit;font-weight:750;cursor:pointer;border:0;border-radius:14px;padding:12px 18px}.subtle{margin-left:auto;background:#242a3c;color:var(--text)}.hero{margin:38px 0 20px}.hero h2{font-size:clamp(24px,5vw,38px);margin:0 0 10px}.hero p:last-child{color:var(--muted);margin:0;line-height:1.55}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:22px 0}.stats div{padding:16px;border:1px solid var(--line);border-radius:18px;background:#111522}.stats span{display:block;color:var(--muted);font-size:10px;letter-spacing:.12em}.stats strong{display:block;font-size:28px;margin-top:5px}.arena-wrap{padding:8px;background:#101421;border:1px solid var(--line);border-radius:24px}.arena{height:min(48vh,390px);min-height:260px;position:relative;overflow:hidden;border-radius:18px;background:radial-gradient(circle at 50% 50%,#1d2543,#101421 70%);outline:none;touch-action:manipulation}.target{display:none;position:absolute;width:56px;height:56px;border-radius:50%;padding:0;background:var(--green);color:#071b19;font-size:33px;box-shadow:0 0 0 8px #73e0bd20,0 7px 24px #0008;transform:translate(-50%,-50%)}.overlay{position:absolute;inset:0;display:grid;place-items:center;text-align:center;padding:22px;background:#0a0d19cf}.overlay>div{max-width:330px}.overlay h3{font-size:25px;margin:0 0 6px}.overlay p{color:var(--muted);line-height:1.55}.primary{background:var(--accent);color:#101022;padding:14px 22px}.tips{display:flex;flex-wrap:wrap;gap:9px 16px;color:var(--muted);font-size:10px;letter-spacing:.08em;margin:16px 4px}footer{border-top:1px solid var(--line);padding-top:18px;margin-top:24px;color:#747d97;font-size:12px}@media(max-width:480px){.shell{padding-top:16px}.mark{width:42px;height:42px}.subtle{padding:10px}.stats div{padding:12px}.stats strong{font-size:24px}}
""",
        "game.js": r"""(() => {
  const arena = document.getElementById("arena");
  const target = document.getElementById("target");
  const overlay = document.getElementById("overlay");
  const startButton = document.getElementById("start");
  const resetButton = document.getElementById("reset");
  const scoreOutput = document.getElementById("score");
  const timeOutput = document.getElementById("time");
  const bestOutput = document.getElementById("best");
  const key = "__SLUG__-best";
  let score = 0;
  let seconds = 30;
  let timer = null;
  let playing = false;
  let best = Number(localStorage.getItem(key) || 0);
  bestOutput.textContent = String(best);

  function moveTarget() {
    const pad = 34;
    const x = pad + Math.random() * Math.max(1, arena.clientWidth - pad * 2);
    const y = pad + Math.random() * Math.max(1, arena.clientHeight - pad * 2);
    target.style.left = x + "px";
    target.style.top = y + "px";
  }

  function finish() {
    playing = false;
    clearInterval(timer);
    timer = null;
    target.style.display = "none";
    overlay.style.display = "grid";
    overlay.querySelector("h3").textContent = "Fim de jogo";
    overlay.querySelector("p").textContent = "Você fez " + score + " ponto(s). Seu recorde local é " + best + ".";
    startButton.textContent = "Jogar novamente";
  }

  function start() {
    clearInterval(timer);
    score = 0;
    seconds = 30;
    playing = true;
    scoreOutput.textContent = "0";
    timeOutput.textContent = "30";
    overlay.style.display = "none";
    target.style.display = "block";
    moveTarget();
    timer = setInterval(() => {
      seconds -= 1;
      timeOutput.textContent = String(seconds);
      if (seconds <= 0) finish();
    }, 1000);
    arena.focus();
  }

  target.addEventListener("pointerdown", event => {
    event.preventDefault();
    if (!playing) return;
    score += 1;
    scoreOutput.textContent = String(score);
    if (score > best) {
      best = score;
      bestOutput.textContent = String(best);
      localStorage.setItem(key, String(best));
    }
    moveTarget();
  });

  startButton.addEventListener("click", start);
  resetButton.addEventListener("click", start);
  document.addEventListener("keydown", event => {
    if (event.key.toLowerCase() === "r") start();
    if (event.key === " " && !playing) {
      event.preventDefault();
      start();
    }
  });
  window.addEventListener("resize", () => { if (playing) moveTarget(); });
})();
""",
        "README.md": "# __TITLE__\n\n__BRIEF__\n\nAbra index.html no navegador. O jogo funciona localmente, salva o recorde no navegador e não depende de API, servidor ou conta.\n",
    }


def _social_app() -> dict[str, str]:
    return {
        "index.html": r"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#090a12">
  <title>__TITLE__</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main class="layout">
    <aside class="sidebar"><a class="brand" href="#"><span class="mark">D</span><span>__TITLE__</span></a><nav><a class="active" href="#inicio">⌂ <span>Início</span></a><a href="#criar">＋ <span>Criar publicação</span></a><a href="#sobre">◇ <span>Sobre o protótipo</span></a></nav><p class="side-note">Protótipo local. Não há contas nem servidor.</p></aside>
    <section class="content" id="inicio">
      <header><div><p class="eyebrow">ESPAÇO DA COMUNIDADE</p><h1>Seu feed</h1></div><label class="search">⌕ <input id="search" placeholder="Buscar publicações" aria-label="Buscar publicações"></label></header>
      <section class="composer" id="criar"><div class="avatar">D</div><form id="post-form"><label for="post-input">Compartilhe uma ideia</label><textarea id="post-input" maxlength="2000" placeholder="O que você quer compartilhar?" required></textarea><div class="compose-footer"><span id="counter">0/2000</span><button class="primary" type="submit">Publicar</button></div></form></section>
      <div class="feed-header"><h2>Publicações</h2><span id="post-count">0 itens</span></div>
      <section id="feed" class="feed" aria-live="polite"></section>
      <footer id="sobre">Os dados ficam apenas neste navegador. Para uso real com várias pessoas, será necessário um servidor seguro e autenticação.</footer>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
""",
        "style.css": r""":root{color-scheme:dark;--bg:#090a12;--panel:#141725;--surface:#202437;--line:#2d3349;--text:#f4f5ff;--muted:#a1a8bd;--accent:#aaa4ff;font-family:Inter,system-ui,-apple-system,sans-serif}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);min-height:100vh}.layout{max-width:1180px;margin:auto;display:grid;grid-template-columns:220px minmax(0,760px);gap:32px;padding:24px}.sidebar{position:sticky;top:24px;height:calc(100vh - 48px);display:flex;flex-direction:column}.brand{display:flex;align-items:center;gap:11px;color:var(--text);font-size:19px;font-weight:800;text-decoration:none}.mark,.avatar{width:40px;height:40px;display:grid;place-items:center;border-radius:14px;background:var(--accent);color:#121221;font-weight:900}.sidebar nav{display:grid;gap:7px;margin-top:35px}.sidebar nav a{padding:13px 14px;border-radius:13px;text-decoration:none;color:var(--muted);font-size:17px;display:flex;gap:13px;align-items:center}.sidebar nav a.active,.sidebar nav a:hover{background:#252a3c;color:var(--text)}.side-note{margin-top:auto;color:#777f98;font-size:12px;line-height:1.6}.content{min-width:0}header{display:flex;gap:12px;align-items:center;justify-content:space-between;margin:6px 0 24px}.eyebrow{font-size:10px;letter-spacing:.15em;font-weight:800;color:var(--accent);margin:0 0 5px}h1{font-size:32px;margin:0}h2{font-size:19px}.search{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:11px 13px;display:flex;gap:8px;align-items:center;color:var(--muted)}.search input{width:160px;max-width:35vw;color:var(--text);font:inherit;background:transparent;border:0;outline:0}.composer,.post{background:var(--panel);border:1px solid var(--line);border-radius:19px;padding:17px;display:flex;gap:13px}.composer form{flex:1;min-width:0}.composer form>label{display:block;font-weight:750;margin:2px 0 12px}.composer textarea{width:100%;min-height:100px;resize:vertical;background:#0e1120;color:var(--text);border:1px solid var(--line);border-radius:12px;padding:13px;font:inherit;line-height:1.5}.compose-footer{display:flex;justify-content:space-between;align-items:center;margin-top:10px;color:var(--muted);font-size:12px}.primary{border:0;border-radius:12px;background:var(--accent);color:#101020;font:inherit;font-weight:800;padding:11px 17px;cursor:pointer}.feed-header{display:flex;align-items:center;justify-content:space-between;margin:26px 2px 13px}.feed-header h2{margin:0}.feed-header span{font-size:12px;color:var(--muted)}.feed{display:grid;gap:12px}.post{display:block}.post-head{display:flex;gap:11px;align-items:center}.post-head .avatar{flex:0 0 38px;width:38px;height:38px;border-radius:50%;background:#343b60;color:var(--text)}.post-head strong{display:block;font-size:14px}.post-head small{display:block;color:var(--muted);margin-top:3px}.post-content{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;margin:16px 0}.post-actions{display:flex;gap:10px;border-top:1px solid var(--line);padding-top:12px;flex-wrap:wrap}.post-actions button{flex:1;background:transparent;border:0;color:var(--muted);font:inherit;padding:8px;cursor:pointer}.post-actions button:hover,.post-actions button.liked{color:var(--accent)}.empty{border:1px dashed var(--line);border-radius:18px;padding:35px;text-align:center;color:var(--muted)}footer{color:#7b8298;font-size:12px;line-height:1.6;margin:28px 2px}@media(max-width:760px){.layout{display:block;padding:16px}.sidebar{position:static;height:auto;margin-bottom:24px}.sidebar nav{grid-template-columns:repeat(3,minmax(0,1fr));margin-top:16px}.sidebar nav a{font-size:12px;padding:10px 7px;gap:6px;justify-content:center}.sidebar nav a span{display:inline}.side-note{display:none}header{align-items:flex-start;flex-direction:column}h1{font-size:28px}.search,.search input{width:100%;max-width:none}.search input{flex:1}.composer{padding:13px}.composer .avatar{display:none}}
""",
        "app.js": r"""(() => {
  const storageKey = "__SLUG__-posts";
  const form = document.getElementById("post-form");
  const input = document.getElementById("post-input");
  const counter = document.getElementById("counter");
  const feed = document.getElementById("feed");
  const search = document.getElementById("search");
  const postCount = document.getElementById("post-count");
  let posts = loadPosts();

  function loadPosts() {
    try {
      const value = JSON.parse(localStorage.getItem(storageKey) || "[]");
      return Array.isArray(value) ? value.filter(item => item && typeof item.text === "string") : [];
    } catch {
      return [];
    }
  }

  function savePosts() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(posts));
    } catch {
      alert("O armazenamento local está cheio. Apague publicações antigas e tente novamente.");
    }
  }

  function makeButton(label, action, liked) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    if (liked) button.classList.add("liked");
    button.addEventListener("click", action);
    return button;
  }

  function render() {
    const query = search.value.trim().toLocaleLowerCase("pt-BR");
    const visible = posts.filter(post => post.text.toLocaleLowerCase("pt-BR").includes(query));
    feed.replaceChildren();
    postCount.textContent = visible.length + (visible.length === 1 ? " item" : " itens");
    if (visible.length === 0) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = query ? "Nenhuma publicação corresponde à busca." : "Ainda não há publicações. Crie a primeira acima.";
      feed.append(empty);
      return;
    }

    visible.forEach(post => {
      const article = document.createElement("article");
      article.className = "post";
      const head = document.createElement("div");
      head.className = "post-head";
      const avatar = document.createElement("div");
      avatar.className = "avatar";
      avatar.textContent = "D";
      const metadata = document.createElement("div");
      const author = document.createElement("strong");
      author.textContent = "Publicação local";
      const date = document.createElement("small");
      date.textContent = new Date(post.createdAt).toLocaleString("pt-BR");
      metadata.append(author, date);
      head.append(avatar, metadata);

      const content = document.createElement("p");
      content.className = "post-content";
      content.textContent = post.text;

      const actions = document.createElement("div");
      actions.className = "post-actions";
      actions.append(
        makeButton((post.liked ? "♥" : "♡") + " " + post.likes, () => {
          post.liked = !post.liked;
          post.likes = Math.max(0, post.likes + (post.liked ? 1 : -1));
          savePosts();
          render();
        }, post.liked),
        makeButton("Comentar", () => {
          const comment = prompt("Escreva um comentário:");
          if (comment && comment.trim()) {
            post.comments = Array.isArray(post.comments) ? post.comments : [];
            post.comments.push(comment.trim().slice(0, 500));
            savePosts();
            render();
          }
        }),
        makeButton("Comentários " + ((post.comments || []).length), () => {
          const comments = post.comments || [];
          alert(comments.length ? comments.map((item, index) => (index + 1) + ". " + item).join("\n") : "Ainda não há comentários.");
        }),
        makeButton("Excluir", () => {
          if (confirm("Excluir esta publicação local?")) {
            posts = posts.filter(item => item.id !== post.id);
            savePosts();
            render();
          }
        })
      );
      article.append(head, content, actions);
      feed.append(article);
    });
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    const value = input.value.trim();
    if (!value) return;
    posts.unshift({
      id: (globalThis.crypto && crypto.randomUUID) ? crypto.randomUUID() : String(Date.now()) + Math.random().toString(16).slice(2),
      text: value,
      createdAt: Date.now(),
      likes: 0,
      liked: false,
      comments: []
    });
    savePosts();
    input.value = "";
    counter.textContent = "0/2000";
    render();
  });

  input.addEventListener("input", () => {
    counter.textContent = input.value.length + "/2000";
  });
  search.addEventListener("input", render);
  render();
})();
""",
        "README.md": "# __TITLE__\n\n__BRIEF__\n\nAbra index.html em um navegador. Este protótipo oferece publicações, busca, likes e comentários locais. Os dados não são enviados a um servidor; para uso com várias pessoas, implemente backend, autenticação e regras de privacidade.\n",
    }


def _python_cli() -> dict[str, str]:
    return {
        "main.py": r"""import argparse
import json
from pathlib import Path


DATA_FILE = Path.home() / ".local" / "share" / "__SLUG__" / "tasks.json"


def load_tasks():
    if not DATA_FILE.exists():
        return []
    try:
        value = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read task data: {exc}") from exc
    if not isinstance(value, list):
        raise RuntimeError("Task data must be a JSON list.")
    return value


def save_tasks(tasks):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DATA_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(DATA_FILE)


def main():
    parser = argparse.ArgumentParser(description="__TITLE__ - local task manager")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List tasks")
    add = commands.add_parser("add", help="Add a task")
    add.add_argument("text")
    done = commands.add_parser("done", help="Mark a task as complete")
    done.add_argument("task_id", type=int)
    remove = commands.add_parser("remove", help="Remove a task")
    remove.add_argument("task_id", type=int)
    args = parser.parse_args()
    tasks = load_tasks()

    if args.command == "list":
        if not tasks:
            print("No tasks yet.")
        for task in tasks:
            state = "x" if task["done"] else " "
            print(f'[{state}] {task["id"]}: {task["text"]}')
        return

    if args.command == "add":
        text = args.text.strip()
        if not text:
            parser.error("Task text cannot be empty.")
        task_id = max((task["id"] for task in tasks), default=0) + 1
        tasks.append({"id": task_id, "text": text, "done": False})
        save_tasks(tasks)
        print(f"Added task {task_id}.")
    elif args.command == "done":
        task = next((task for task in tasks if task["id"] == args.task_id), None)
        if task is None:
            parser.error(f"Task {args.task_id} was not found.")
        task["done"] = True
        save_tasks(tasks)
        print(f"Completed task {task['id']}.")
    elif args.command == "remove":
        kept = [task for task in tasks if task["id"] != args.task_id]
        if len(kept) == len(tasks):
            parser.error(f"Task {args.task_id} was not found.")
        save_tasks(kept)
        print(f"Removed task {args.task_id}.")


if __name__ == "__main__":
    main()
""",
        "README.md": "# __TITLE__\n\n__BRIEF__\n\nPython 3.11+. Execute python main.py --help para ver os comandos. O estado fica em um arquivo local no diretório do usuário.\n",
    }


def create_project(
    kind: str,
    name: str,
    output_dir: str | Path,
    brief: str = "",
) -> dict[str, Any]:
    selected_kind = (kind or "").strip().lower()
    if selected_kind not in KINDS:
        raise ValueError(f"Unsupported project kind. Choose one of: {', '.join(sorted(KINDS))}.")
    project_name = " ".join((name or "").split()).strip()
    if len(project_name) > 100:
        raise ValueError("Project name must be at most 100 characters.")
    slug = _slug(project_name)
    target = Path(output_dir).expanduser().resolve()
    if target == Path(target.anchor):
        raise ValueError("Refusing to create a project in the filesystem root.")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise FileExistsError(f"Output directory already exists and is not empty: {target}")

    description = " ".join((brief or "Starter project generated locally by Deta.").split())
    if len(description) > 2000:
        description = description[:2000]
    metadata = {
        "name": project_name,
        "slug": slug,
        "kind": selected_kind,
        "brief": description,
        "generator": "Deta local project builder",
        "uses_ai_api": False,
    }
    if selected_kind == "browser-game":
        templates = _browser_game()
    elif selected_kind == "social-app":
        templates = _social_app()
    else:
        templates = _python_cli()

    replacements = {
        "__TITLE__": html.escape(project_name, quote=True),
        "__SLUG__": slug,
        "__BRIEF__": description,
    }
    if selected_kind == "python-cli":
        replacements["__TITLE__"] = project_name.replace("\\", "\\\\").replace('"', '\\"')

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="." + target.name + ".deta-", dir=target.parent))
    written = []
    try:
        for relative_path, template in templates.items():
            destination = stage / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if relative_path.endswith(".md"):
                path_replacements = dict(replacements)
                path_replacements["__TITLE__"] = project_name
            else:
                path_replacements = replacements
            content = re.sub(
                r"__(?:TITLE|SLUG|BRIEF)__",
                lambda match: path_replacements[match.group(0)],
                template,
            )
            destination.write_text(content, encoding="utf-8")
            written.append(relative_path)

        (stage / "project.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written.append("project.json")
        if target.exists():
            target.rmdir()
        os.replace(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    return {
        "name": project_name,
        "kind": selected_kind,
        "directory": str(target),
        "files": written,
        "uses_ai_api": False,
    }
