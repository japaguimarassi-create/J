# PS4 14.02 Host Lab — v1.4.0

Site estático para GitHub + Vercel, com interface responsiva, verificações locais do navegador, retry/backoff limitado a falhas transitórias, cancelamento entre testes, logs locais, revisão estruturada de evidências e exportação Markdown/JSON.

## Estado real do firmware 14.02

**Este projeto não é um jailbreak.** Não existe cadeia pública completa para 14.02 independentemente confirmada por este projeto. O site não afirma sucesso, não tenta executar payload e não modifica o console.

O modo Host oferece:
- verificação de que os arquivos do próprio host estão íntegros e acessíveis;
- identificação indicativa do navegador e registro manual da versão do sistema;
- verificações de APIs web comuns, armazenamento e cache;
- repetição limitada de falhas transitórias, com backoff e cancelamento;
- relatório local em Markdown e JSON;
- cache offline após a primeira visita HTTPS, quando suportado pelo navegador.

Não inclui UAF, heap spray, ROP, syscalls, leitura/escrita de memória privilegiada, patch de kernel, execução de ELF/BIN, instalação de PKG, downgrade ou bypass de proteções. O navegador de um site não tem permissões para alterar configurações internas do PS4.

## Publicação no Vercel

- Repositório: https://github.com/japaguimarassi-create/J
- Root Directory: `ps4-1402-lab`
- Framework Preset: Other
- Build Command: vazio
- Output Directory: `.`
- Install Command: vazio
- Sem variáveis de ambiente e sem banco de dados.

O workflow do GitHub executa os testes de integridade a cada push. Com o repositório conectado ao Vercel, cada push na branch de produção publica a versão correspondente.

## Execução local

Abra `index.html` para leitura básica. Para testar o Service Worker e o modo offline, use um servidor HTTP local ou HTTPS; Service Workers não funcionam em `file://`.

## Testes

Requer Node.js 20 ou superior:

```bash
npm test
```

Os testes validam o manifesto, o registro de evidências, o health check, as declarações de escopo e os recursos estáticos essenciais. Eles não testam nem alegam executar jailbreak.

## Fontes primárias e comunitárias

- https://consolemods.org/wiki/PS4:FAQ
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://github.com/well0nez/afterglow-web
- https://github.com/B4411M/all/tree/main/1402
- https://github.com/Jfkkfjzkz/ps4-akatsuki-jailbreak
- https://github.com/GoldHEN/GoldHEN/releases

As alegações de 14.02 encontradas em repositórios não são tratadas como suporte confirmado sem validação independente e reproduzível em hardware.

## Privacidade

Diagnósticos e relatórios são executados localmente no navegador. O site não envia os resultados de diagnóstico para uma API própria e não solicita credenciais PSN.


## Matriz de capacidades (v1.3.0)

O preflight percorre APIs comuns do navegador uma a uma. Os códigos são locais: **1** = teste da API passou, **0** = teste falhou, **N/A** = API indisponível ou fora do escopo. O verificador inclui SharedArrayBuffer/Atomics, quota de armazenamento e BroadcastChannel quando disponíveis. Não tenta syscalls, leitura/escrita do kernel, corrupção de memória ou escalada de privilégios; JavaScript comum não expõe essas interfaces.


## Revisão técnica 14.00 → 14.02 (13 nov 2026)

O painel de delta registra o estado das evidências públicas: AIO/Prolapse é marcado pela PS4 Developer Wiki como corrigido em 14.02; Afterglow é incerto (pode ter sido corrigido); WebKit e BD-J não têm validação pública confirmada para 14.02. A restrição de sockets não AF_UNIX em apps não privilegiados já existe desde 14.00. A nota oficial da Sony é genérica e não identifica módulos/CVEs.

O navegador não pode chamar syscalls nativas nem acessar memória/kernel privilegiado. Uma análise adicional segura pode comparar metadados, manifests e hashes de pacotes oficiais 14.00/14.02, sem executar payloads nem modificar o console.


## Comparação documental 14.00 → 14.02 (v1.4.0)

O painel **Firmware Delta** carrega `firmware-delta.json` e apresenta os dados em interface, sem executar comandos no PS4.

- Nota oficial 14.00: desempenho e estabilidade.
- Nota oficial 14.02: correções de segurança, sem identificação pública dos módulos ou CVEs.
- PS4 Developer Wiki: indica a correção da falha AIO/Prolapse no 14.02; trata o estado do Afterglow como incerto.
- ConsoleMods: não lista uma cadeia pública de userland + kernel para 14.02.

O código distingue correções relatadas, hipóteses e pontos desconhecidos. A ausência de um item nas notas oficiais não é prova de que esse componente permaneceu inalterado.

Fontes usadas no delta:
- https://www.playstation.com/en-us/support/hardware/ps4/system-software/
- https://www.psdevwiki.com/ps4/Vulnerabilities
- https://www.psdevwiki.com/ps4/System_Software
- https://consolemods.org/wiki/PS4:Exploit_Chart
- https://consolemods.org/wiki/PS4:Getting_Started
- https://github.com/siongadev/PS4-14.00-Jailbreak-Research/blob/main/docs/PROGRESS.md
