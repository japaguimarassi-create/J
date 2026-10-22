# Deta — mapa mental da reconstrução

## Escopo
- Aplicativo Android refeito com fonte nova
- Nenhuma implementação de IA, modelo neural ou motor de resposta
- Nenhum acesso à internet ou permissão de rede
- Histórico guardado localmente
- Menu antigo arquivado fora de app/src/main

## Interface
- Barra superior, menu lateral e nova conversa
- Área de conversa vazia claramente identificada como base local
- Mensagens próprias em balões
- Campo multilinha e enviar
- Histórico recente com busca
- Apagar conversa atual pelo menu
- Apagar conversa individual com toque prolongado
- Sobre explica o escopo da versão

## Dados
- SharedPreferences + JSON
- IDs únicos por conversa
- Título a partir da primeira mensagem
- Histórico ordenado pela atividade recente
- Limites de 80 conversas e 120 mensagens por conversa
- JSON danificado é descartado sem impedir a tela de abrir
- Conversa ativa restaurada após recriação da Activity

## Removido do APK
- WebSearch.java
- Permissão INTERNET
- Modelo, prompts e respostas automáticas de IA
- Reconhecimento de voz e chamadas HTTP
- Classe Canvas do ícone antigo

## Arquivo histórico
- MainActivity antiga, menu, WebSearch, ícone, manifest, tema, testes e workflow preservados em archive/menu-v1
- Arquivos arquivados não são compilados pelo Android

## Testes de lançamento
- Teste unitário
- Inicialização real em emulador
- Envio e exibição de uma mensagem local
- Abertura do menu e criação de conversa
- Persistência ao recriar a Activity
- Compilação limpa, zipalign, assinatura e package ID
- APK publicado somente depois que o teste de emulador passar

## Versão
- Deta rebuilt base 1.1.0
- versionCode 110
- Pacote de teste app.deta.mobile.debug
