# Deta v1.0 — mapa mental

## Aplicativo Android
- Interface escura e vetorial
- Conversas, nova conversa, menu lateral e busca no histórico
- Persistência local
- Ditado de voz quando disponível no Android
- Tela de recuperação se a interface falhar na inicialização

## Internet sem API de IA
- Pesquisa pública via HTTPS
- Títulos, resumos e links das fontes
- Pesquisa em segundo plano
- Limites de resposta e validação básica de URLs
- Falhas de rede comunicadas na conversa

## Núcleo de IA experimental
- Modelo Python de 400.000 parâmetros
- Cinco grupos de treinamento sequencial
- Checkpoints como artefatos de CI
- Qualidade generativa ainda requer benchmark independente
- Não integrado ao APK atual até a inferência local ser comprovada

## Criação de projetos
- Jogo de navegador
- Aplicativo social
- Ferramenta CLI Python
- Testes sintáticos dos projetos gerados

## Qualidade
- Testes unitários
- Checagem de dependências e compilação
- Teste de inicialização no emulador Android
- Verificação de identidade, alinhamento, assinatura e integridade do APK

## Regras da IA
- Nenhuma personalidade ou conjunto de diretrizes personalizadas é imposto nesta versão
- O proprietário define as regras futuras
- Restrições técnicas do Android, rede e dependências permanecem aplicáveis

## Próximas prioridades
1. Capturar log de falha do aparelho para determinar a causa original.
2. Confirmar inicialização no emulador e em aparelho físico.
3. Medir qualidade e memória antes de integrar o modelo local.
4. Testar persistência, pesquisa e criação de projetos de ponta a ponta.
