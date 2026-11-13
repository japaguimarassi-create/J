# PS4 14.02 Research Lab — v1.2.0

Site estático para GitHub + Vercel, com interface responsiva, diagnóstico do navegador, retry/backoff limitado a falhas transitórias, cancelamento entre testes, logs locais, revisão estruturada de evidências e exportação Markdown/JSON.

## Limite técnico

Este projeto **não é jailbreak e não executa exploits**. Não tenta UAF, heap spray, ROP, syscalls, leitura/escrita de memória privilegiada, patch de kernel, execução de payloads ELF/BIN, instalação de PKG, downgrade ou bypass de proteções. O botão único executa apenas verificações leves no navegador que abriu o site.

A revisão de 12 nov 2026 encontrou um repositório recente que alega 14.02. A alegação não foi confirmada independentemente: a entrada `PS4["14.02"]` em `ps4_offsets.js` é criada copiando `PS4["14.00"]`, com compatibilidade WebKit descrita como “assumed”; o arquivo `afterglow-g.js` identifica os offsets de kernel como 14.00. A página de entrada contém uma condição `true || ...`, que torna ineficaz a tela de senha. Isso mostra que o repositório, por si só, não comprova compatibilidade reproduzível em hardware 14.02.

O registro `evidence.json` é uma revisão manual de fontes; não é um scanner automático de vulnerabilidades.

## Publicar

- Repositório: `japaguimarassi-create/J`
- Root Directory: `ps4-1402-lab`
- Framework: Other
- Build Command: vazio
- Output Directory: `.` (ponto)
- Install Command: vazio
- Sem variáveis de ambiente e sem banco de dados.

Conecte a branch `main` ao Vercel. Cada push atualiza o site.

## Offline

A primeira visita deve ser feita via HTTPS para instalar o Service Worker. Depois, os arquivos estáticos podem abrir do cache se o navegador oferecer suporte. Alguns navegadores antigos do PS4 não suportam PWA/Service Worker.

## Fontes

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/well0nez/afterglow-web
- https://github.com/B4411M/all/tree/main/1402
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://github.com/GoldHEN/GoldHEN/releases

## Privacidade

Testes e relatórios são executados no navegador. Os resultados não são enviados ao servidor.
