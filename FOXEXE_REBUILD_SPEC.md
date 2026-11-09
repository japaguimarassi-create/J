# Foxexe — reconstrução integral

Esta branch é a reconstrução limpa do aplicativo. A fonte funcional original deve ser recuperada do arquivo de origem versionado em `foxexe-unified` (fragmentos `Foxexe-source-part01.b64` a `part09.b64`). Não substituir a implementação original por demonstrações, respostas fixas ou menus simulados.

## Requisitos obrigatórios

### 1. Opções criptografadas Foxexe
- Preservar todos os registros, identificadores, rótulos, ordem, metadados e payloads criptografados das opções originais.
- Antes de alterar qualquer formato, identificar no código-fonte original o algoritmo, modo, derivação/armazenamento de chave, IV/nonce, padding, codificação e fluxo de descriptografia.
- Não tratar Base64, hexadecimal ou ofuscação como criptografia.
- Não inventar chaves nem substituir payloads originais por opções de demonstração.
- Manter os payloads cifrados no armazenamento interno do app; descriptografar apenas em memória quando necessário.
- Não registrar plaintext, chaves, tokens ou conteúdo sensível em logs.
- Proteger chaves locais com Android Keystore quando a implementação original permitir migração segura. Se o formato antigo depender de segredo embutido, documentar a limitação e manter compatibilidade até haver migração explícita.
- Cada opção deve ser testada: leitura, autenticação/integridade, descriptografia, renderização, ativação/desativação e execução real da ação correspondente. Falha de autenticação deve impedir a execução.

### 2. Qwen offline
- Integrar um modelo Qwen local, com pesos incluídos no pacote de distribuição ou instalados como recurso local do app.
- Inferência 100% no dispositivo, sem endpoint de inferência remoto.
- Google pode ser usado apenas como runtime/biblioteca de execução Android, não como serviço de IA nem como backend.
- Mostrar claramente indisponibilidade de memória/armazenamento ou incompatibilidade do dispositivo; nunca substituir o modelo por respostas predefinidas.
- Separar o runtime/modelo da interface do painel Foxexe.

### 3. Contexto privado
- O contexto é um arquivo interno, não uma tela nem uma opção visível ao usuário.
- O conteúdo inicial deve ensinar progressivamente: representação binária/bytes, leitura e codificação, português, fundamentos de programação nas linguagens pedidas e outras áreas.
- O Qwen pode ler, propor acréscimos e consolidar conhecimento. Registrar origem, data, versão e validação de cada entrada.
- Contexto não é treinamento dos pesos do modelo. Não alegar que o modelo foi retreinado se apenas o arquivo foi atualizado.
- Ciclo de 40 minutos: executar consolidação local apenas quando o app estiver em condições seguras (carregando/ocioso, bateria e espaço disponíveis); pausar em segundo plano conforme limites do Android. Nunca executar fine-tuning de pesos automaticamente no celular sem um procedimento explícito, conjunto de dados validado e orçamento de recursos.

### 4. Interface e comportamento
- Remover o laboratório de respostas premeditadas e todos os fluxos que apenas simulam geração.
- O prompt deve ser encaminhado ao modelo local.
- Opções novas só podem ser criadas quando o modelo produzir uma definição estruturada validável; a opção deve ter estado persistente e ação funcional, não apenas aparência alternável.
- Separar claramente: conversa/modelo, painel de opções e serviços do sistema.

## Auditoria e critérios de aceite

1. Reconstituir e listar todos os arquivos do projeto original.
2. Localizar o código e os dados das opções criptografadas; gerar inventário com hashes, sem publicar segredos.
3. Documentar algoritmo e ciclo criptográfico com base no código encontrado.
4. Criar testes de compatibilidade para todos os payloads originais.
5. Validar cada opção individualmente e em conjunto.
6. Validar inferência Qwen sem rede (bloquear tráfego de saída durante o teste).
7. Validar persistência e isolamento do contexto interno.
8. Validar o ciclo de 40 minutos, pausa, retomada e proteção de bateria.
9. Compilar, verificar assinatura, instalar e testar em Android real.
10. Não declarar concluído nem distribuir APK até todos os critérios aplicáveis passarem.

## Estado
Esta branch é apenas o ponto de partida limpo. O APK anterior de 33 KB não contém pesos Qwen nem prova que as opções criptografadas originais estejam integradas. O código e os dados originais precisam ser extraídos e auditados antes de afirmar compatibilidade.
