# Notas de pesquisa e referências

Consultado em 25 de outubro de 2026; verifique novamente tamanhos e tags antes de baixar modelos, pois catálogos e releases mudam.

## Modelos-professores locais

- Qwen3 no Ollama: https://ollama.com/library/qwen3 — a tag qwen3:8b é o professor padrão para programação e instruções.
- Gemma 4 no Ollama: https://ollama.com/library/gemma4 — a tag gemma4:e4b oferece opção multimodal de menor porte dentro dessa família.
- gpt-oss no Ollama: https://ollama.com/library/gpt-oss — gpt-oss:20b é o professor de raciocínio, com grande exigência de memória comparado a um celular.

Esses são modelos abertos baixados e executados separadamente. A integração usa Ollama local; não é uma chamada à API paga. Os tamanhos exatos dependem da quantização e do pacote baixado.

## Motor gráfico

- Three.js docs: https://threejs.org/docs/
- Sistema de animação Three.js: https://threejs.org/manual/pages/animation-system.html

Three.js fornece renderização 3D e primitives. FORGE é a camada de script própria; não é uma cópia do formato de outro editor.

## Destilação e cautelas

- ICLR 2026, pesquisa sobre geração de exemplos de destilação: https://proceedings.iclr.cc/paper_files/paper/2026/hash/b693a240cf1009bff9fa4422141c9392-Abstract-Conference.html
- ACL 2026, SmartAD e exemplos alinhados à capacidade do aluno: https://aclanthology.org/2026.findings-acl.1349/
- Documentação oficial Gemma: https://ai.google.dev/gemma/docs/core
- OpenAI gpt-oss: https://openai.com/index/introducing-gpt-oss/

A arquitetura do pequeno aluno prioriza o tamanho e o escopo estreito, não paridade com professores de bilhões de parâmetros. Um consenso automático é um filtro de qualidade, não prova de verdade; preserve auditoria e revisão humana.
