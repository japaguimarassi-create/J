from klod.tokenizer import BytePairTokenizer


def test_exact_round_trip_supported_text() -> None:
    corpus = [
        "Olá, mundo! A inteligência artificial está em treinamento.",
        "Hello, world! Language models predict the next token.",
        "def soma(a, b):\n    return a + b\n",
        "1234567890 + 3.14159 = números",
        "Emoji: 🧠🚀✨ e símbolos: <>/{[]}\n",
    ]
    tokenizer = BytePairTokenizer().train(corpus * 3, vocab_size=512, min_frequency=2)
    samples = corpus + ["Texto nunca visto: ação, ç, 東京, 🧪", "", "\u0000\n\t"]
    for sample in samples:
        assert tokenizer.decode(tokenizer.encode(sample)) == sample


def test_tokenizer_save_load(tmp_path) -> None:
    tokenizer = BytePairTokenizer().train(["banana banana", "bananas"], vocab_size=300)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    restored = BytePairTokenizer.load(path)
    value = "banana 🍌"
    assert restored.encode(value) == tokenizer.encode(value)
    assert restored.decode(restored.encode(value)) == value


def test_special_tokens_are_reserved_and_round_trip_when_skipped() -> None:
    tokenizer = BytePairTokenizer().train(["Klod aprende. " * 4], vocab_size=300)
    ids = tokenizer.special_token_ids
    assert len(set(ids.values())) == 4
    encoded = tokenizer.encode("ação 🧠", add_bos=True, add_eos=True)
    assert encoded[0] == ids["<bos>"]
    assert encoded[-1] == ids["<eos>"]
    assert tokenizer.decode(encoded, skip_special_tokens=True) == "ação 🧠"
    assert "<bos>" in tokenizer.decode(encoded)


def test_partial_utf8_generation_can_be_decoded_with_replacement() -> None:
    tokenizer = BytePairTokenizer()
    assert tokenizer.decode([0xC3], errors="replace") == "�"


def test_invalid_token_id_fails() -> None:
    tokenizer = BytePairTokenizer()
    try:
        tokenizer.decode([999])
    except ValueError:
        return
    raise AssertionError("Invalid token ID must raise ValueError")
