# PS4 14.02 Research Lab

Site estático para GitHub + Vercel. Interface mobile, diagnóstico web com tentativas benignas limitadas, logs e exportação Markdown/JSON. Cache offline via Service Worker após a primeira visita online.

## Limite técnico
Este projeto **não é um jailbreak**. Ele não executa exploits, kernel patches, payloads ELF/BIN, instalação de PKG, downgrade ou acesso interno ao sistema. As APIs web não concedem esses privilégios. O resultado do diagnóstico não comprova vulnerabilidade nem compatibilidade com jailbreak.

## Publicar
1. Abra o repositório GitHub.
2. Importe o projeto no Vercel, usando a pasta raiz `ps4-1402-lab` como Root Directory, ou importe o repositório e defina essa pasta.
3. Framework: Other; Build Command vazio; Output Directory `.`.
4. Faça o primeiro deploy conectado à branch `main`.
5. Abra a URL no PS4. A primeira visita precisa carregar os arquivos; depois o Service Worker pode servir a interface em cache.

## Arquivos
- `index.html`: aplicação e diagnóstico.
- `sw.js`: cache offline.
- `manifest.webmanifest`: metadados PWA.

## Privacidade
Os testes são executados no navegador. Relatórios são gerados localmente e não enviados a um servidor.
