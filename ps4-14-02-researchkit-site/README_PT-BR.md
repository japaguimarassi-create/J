# PS4 14.02 ResearchKit Web — v1.1.0

Site estático para Vercel, com interface responsiva, diagnóstico local do navegador, repetição limitada de testes seguros, logs de sessão e exportação Markdown/JSON.

## Escopo

- Diagnóstico do host e health.json.
- Detecção informativa do firmware via User-Agent e campo manual.
- Testes de APIs comuns: ArrayBuffer/DataView, WebAssembly, Local/Session Storage, Cache API, IndexedDB, WebGL, Service Worker, conectividade e Application Cache legado.
- Retry limitado, cancelamento e logs locais.
- Relatórios .md e .json.
- PWA e cache offline após a primeira visita bem-sucedida em HTTPS e suporte do navegador.
- Referências públicas sobre compatibilidade e análise da pasta 14.02 do B41M.

## Limite explícito

Este site NÃO é jailbreak e não afirma desbloquear o PS4 14.02. Não inclui nem executa exploits, payloads HEN/GoldHEN, ROP, syscalls, heap spray, UAF, escrita de kernel, downgrade, bypass de atualização ou flash de hardware. O botão executa apenas testes comuns e de baixa intensidade no navegador que abriu o site.

A detecção de firmware por User-Agent é apenas uma pista: confirme a versão em Configurações do PS4. Um teste positivo de API não prova vulnerabilidade nem acesso privilegiado.

## Publicação no GitHub + Vercel

- Repositório: japaguimarassi-create/J
- Diretório de projeto: ps4-14-02-researchkit-site/
- Framework: Other / Static
- Build command: vazio
- Output directory: .
- Install command: vazio

O projeto Vercel deve apontar seu Root Directory para ps4-14-02-researchkit-site.

## Offline

A primeira visita deve ocorrer online via HTTPS para que o Service Worker possa instalar e armazenar os arquivos estáticos. Depois disso, o painel pode abrir do cache quando o navegador permitir. Nem todo navegador do PS4 oferece Service Worker/PWA; o próprio diagnóstico mostra essa limitação. O diagnóstico não precisa de uma API backend e não envia dados.

## Fontes

- https://github.com/B4411M/all/tree/main/1402
- https://github.com/well0nez/afterglow-web
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://consolemods.org/wiki/PS4:FAQ
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/GoldHEN/GoldHEN/releases

## Licença

Arquivos deste site são licenciados sob MIT. Marcas, nomes, projetos e materiais de terceiros permanecem com seus respectivos titulares.