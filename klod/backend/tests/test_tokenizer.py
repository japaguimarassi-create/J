from klod.tokenizer import BytePairTokenizer


def test_exact_round_trip() -> None:
    corpus = ["Olá, mundo! ação e inteligência.", "Hello, world! next token.", "def soma(a, b):\n    return a + b\n", "12345 + 3.14159", "Emoji 🧠🚀✨ <>/{[]}"]
    tokenizer = BytePairTokenizer().train(corpus * 3, vocab_size=512)
    for text in corpus + ["texto desconhecido 東京 🧪", "", "\u0000\n\t"]:
        assert tokenizer.decode(tokenizer.encode(text)) == text


def test_save_load(tmp_path) -> None:
    tokenizer = BytePairTokenizer().train(["banana banana", "bananas"], vocab_size=300)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    restored = BytePairTokenizer.load(path)
    text = "banana 🍌"
    assert restored.encode(text) == tokenizer.encode(text)
    assert restored.decode(restored.encode(text)) == text


def test_invalid_id_fails() -> None:
    try:
        BytePairTokenizer().decode([999])
    except ValueError:
        return
    raise AssertionError("Invalid token ID must fail")
