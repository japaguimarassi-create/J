import argparse
from pathlib import Path

from deta.data import write_jsonl


LICENSE_SOURCE = (
    "https://github.com/japaguimarassi-create/J/blob/deta-ai-foundation/"
    "data/FIRST_PARTY_DATA_LICENSE.md"
)

KINDS = [
    ("jogo", "jogo", "controles, regras da rodada, pontuação e condição de término",
     "entrada do jogador, estado do jogo e regras de conclusão"),
    ("rede social", "app social", "publicações, busca, reações, comentários e persistência",
     "estrutura das publicações, feed, filtros e operações sobre cada publicação"),
    ("lista de tarefas", "app utilitário", "criação, conclusão, edição, exclusão e persistência",
     "modelo dos itens, validação da entrada e atualização dos estados"),
    ("agenda", "app utilitário", "criação, consulta, edição, exclusão e ordenação de eventos",
     "modelo dos eventos, ordenação cronológica e validação de data"),
    ("editor de notas", "app utilitário", "criar, editar, pesquisar e excluir notas",
     "armazenamento das notas, pesquisa por texto e edição segura"),
    ("catálogo", "app utilitário", "cadastro de itens, busca, filtros e visualização de detalhes",
     "modelo do item, filtros, ordenação e tela de detalhes"),
]
FEATURES = [
    "interface adaptável para celular",
    "validação de dados vazios",
    "estado vazio e mensagens de erro úteis",
    "navegação clara entre as funções principais",
    "persistência local e tratamento de dados inválidos",
    "testes das ações principais e dos casos de erro",
    "separação entre interface, dados e lógica",
    "documentação dos arquivos e instruções de execução",
]
PLAN_PREFIX = (
    "User: Prepare a concise implementation plan for this app request.\n"
    "Request: "
)


def instruction(content: str, path: str) -> dict[str, str]:
    return {
        "content": content.strip() + "\n",
        "source_url": LICENSE_SOURCE,
        "license_id": "CC0-1.0",
        "source_type": "text",
        "source_name": "Deta original programming instruction examples",
        "path": path,
    }


def build_records() -> list[dict[str, str]]:
    records = []
    verbs = ["Crie", "Desenvolva", "Construa", "Implemente", "Gere"]
    names = [
        "Projeto Aurora", "Painel Simples", "Nova Rotina", "Espaço Pessoal",
        "Organizador", "Central Mobile", "Meu Projeto", "Ideia Digital",
    ]
    for kind_index, (kind_prompt, kind_label, requirements, architecture) in enumerate(KINDS):
        for verb_index, verb in enumerate(verbs):
            for name_index, name in enumerate(names):
                feature = FEATURES[(kind_index * 3 + verb_index + name_index) % len(FEATURES)]
                prompt = f"{verb} um {kind_prompt} chamado {name} com {feature}."
                plan = (
                    "Plano:\n"
                    f"1. Confirmar o objetivo: {kind_label} chamado {name}.\n"
                    f"2. Especificar o comportamento: {requirements}.\n"
                    f"3. Definir os componentes: {architecture}.\n"
                    f"4. Incluir qualidade: {feature}.\n"
                    "5. Implementar primeiro a função central e separar interface, estado e persistência.\n"
                    "6. Testar o fluxo principal, entradas inválidas, estados vazios e persistência.\n"
                    "7. Empacotar os arquivos e validar que o projeto abre no ambiente-alvo."
                )
                content = PLAN_PREFIX + prompt + "\nAssistant:" + plan
                records.append(instruction(content, f"planning/{kind_index}-{verb_index}-{name_index}"))

    debugging_inputs = [
        "A tela fecha ao abrir.",
        "O botão não faz nada.",
        "A lista não salva depois de fechar o app.",
        "O formulário aceita campos vazios.",
        "O preview mostra uma tela em branco.",
        "O arquivo ZIP não abre.",
        "O build falha ao resolver uma dependência.",
        "A pesquisa retorna resultados duplicados.",
        "Um erro aparece apenas depois de reiniciar.",
        "O aplicativo cria um projeto mesmo quando a mensagem é só uma saudação.",
        "A interface congela durante uma operação de rede.",
        "O código gerado contém recursos que não foram solicitados.",
    ]
    debugging_plans = [
        "Reproduzir o problema com a menor entrada possível; capturar o erro completo; localizar a primeira causa, não apenas a última exceção; escrever um teste que falhe antes da correção; corrigir a origem; executar novamente a suíte de testes e comparar o comportamento anterior e posterior.",
        "Verificar primeiro a classificação do pedido e os estados da interface; separar conversa, pesquisa e criação; confirmar que a execução assíncrona retorna ao estado correto; adicionar um teste para a entrada que falhou; validar persistência e navegação após reinício.",
        "Inspecionar o caminho de dados, validar entradas e saídas em cada etapa, limitar a alteração ao módulo responsável, cobrir o caso de sucesso e os casos de erro, e não declarar a correção concluída até os testes passarem.",
        "Reproduzir em um ambiente limpo, conferir dependências e versões compatíveis, registrar o erro original, aplicar a menor correção que resolva a causa e testar o build completo, não só a compilação isolada.",
    ]
    for input_index, problem in enumerate(debugging_inputs):
        for plan_index, plan in enumerate(debugging_plans):
            content = (
                f"User: Planeje como depurar este problema: {problem}\n"
                f"Assistant: {plan}\n"
            )
            records.append(instruction(content, f"debugging/{input_index}-{plan_index}"))

    code_review_prompts = [
        "Revise o código antes de gerar o ZIP.",
        "Como reduzir bugs no app?",
        "Planeje os testes de um formulário.",
        "Como decidir se a mensagem pede um app?",
        "O que verificar antes de exportar?",
        "Como lidar com uma pesquisa sem resultados?",
        "Como impedir que o preview acesse sites externos?",
        "Como evitar perder conversas antigas?",
        "Como gerar um projeto sem sobrescrever arquivos?",
        "Como diferenciar uma pergunta de um comando para criar?",
    ]
    code_review_answers = [
        "Separar o pedido em requisitos verificáveis; revisar dependências e dados de entrada; validar sintaxe e arquivos obrigatórios; testar o fluxo principal e as falhas; inspecionar o pacote resultante antes de disponibilizar a exportação.",
        "Criar testes pequenos por requisito, validar valores de limite, estado vazio, erros de rede e persistência, rodar os testes depois de cada mudança e evitar anunciar sucesso se alguma etapa falhar.",
        "Classificar a intenção antes de executar ações: conversa não deve criar projeto; pesquisa deve consultar fontes; criação deve montar plano, listar requisitos, gerar arquivos e só então validar o pacote.",
        "Construir um plano curto antes da implementação, ligar cada requisito a um arquivo e teste, identificar dependências e limitações, implementar em etapas e verificar o resultado produzido.",
    ]
    for prompt_index, prompt in enumerate(code_review_prompts):
        for answer_index, answer in enumerate(code_review_answers):
            records.append(instruction(
                f"User: {prompt}\nAssistant: {answer}",
                f"review/{prompt_index}-{answer_index}",
            ))

    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Create first-party CC0 app-programming instruction examples.")
    parser.add_argument("--output", type=Path, default=Path("data/instruction.jsonl"))
    args = parser.parse_args()
    records = build_records()
    written = write_jsonl(iter(records), args.output)
    if written < 500:
        raise SystemExit(f"Only {written} unique instruction records were generated; expected at least 500.")
    print(f"Wrote {written} unique CC0 instruction records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
