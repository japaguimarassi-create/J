from klod.tokenizer import BytePairTokenizer


def test_round_trip_many_writing_systems_and_unicode_categories() -> None:
    corpus = [
        "English: The quick brown fox jumps over the lazy dog.",
        "Português: Olá, ação, coração, informação e ç.",
        "Español: ¡Hola! ¿Cómo estás? Niño, pingüino.",
        "Français: déjà vu, cœur, où, français.",
        "Deutsch: Straße, Grüße, Mädchen.",
        "Русский: Привет, мир! Ёжик.",
        "Ελληνικά: Γειά σου κόσμε.",
        "עברית: שלום עולם.",
        "العربية: مرحباً بالعالم! العربية ١٢٣",
        "हिन्दी: नमस्ते दुनिया।",
        "বাংলা: স্বাগতম পৃথিবী।",
        "தமிழ்: வணக்கம் உலகம்.",
        "ไทย: สวัสดีชาวโลก",
        "中文：你好，世界。繁體中文。",
        "日本語：こんにちは、世界。カタカナ・ひらがな。",
        "한국어: 안녕하세요, 세계!",
        "ქართული: გამარჯობა, მსოფლიო!",
        "Հայերեն: Բարեւ աշխարհ։",
        "አማርኛ: ሰላም ዓለም",
        "မြန်မာ: မင်္ဂလာပါ ကမ္ဘာ",
        "ខ្មែរ: សួស្តី ពិភពលោក",
        "Emoji: 🧠🚀✨👩🏽‍💻🏳️‍🌈",
        "Combining: e\u0301 != é; ZWJ: 👨‍👩‍👧‍👦; RTL mark: \u200f",
    ]
    punctuation = "! ? ¡ ¿ . , ; : … ' \" “ ” ‘ ’ " + chr(96) + " ~ @ # $ % ^ & * - _ + = / \\\\ // /* */ ( ) [ ] { } < > <= >= != == === => -> :: ... | || && \n\t\r"
    corpus.append(punctuation)
    tokenizer = BytePairTokenizer().train(corpus * 3, vocab_size=900, min_frequency=2)
    unseen = [
        "Unicode não visto no treino: 𐓏 𑀅 𞓐 🫨",
        "Matemática: ∀x∈ℝ, x²≥0; ∑∞; √−1; ⊗",
        "Código: const path = \"a/b\\\\c\"; fn(x) => x != null;",
        "Full-width: ／ ＼ （ ） ［ ］ ｛ ｝ ＜ ＞",
        "",
        "\u0000\n\t\r",
    ]
    for sample in corpus + unseen:
        assert tokenizer.decode(tokenizer.encode(sample)) == sample
    report = tokenizer.inspect_text("A العربية ١٢٣! 🧠")
    assert report["codepoints"] > 0
    assert report["utf8_bytes"] >= report["codepoints"]


def test_tokenizer_save_load_and_special_ids(tmp_path) -> None:
    tokenizer = BytePairTokenizer().train(["banana banana", "bananas"], vocab_size=300)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    restored = BytePairTokenizer.load(path)
    value = "banana 🍌"
    assert restored.encode(value) == tokenizer.encode(value)
    assert restored.decode(restored.encode(value)) == value
    assert restored.special_token_ids == tokenizer.special_token_ids


def test_incremental_expansion_is_append_only(tmp_path) -> None:
    tokenizer = BytePairTokenizer().train(["banana banana", "banana"], vocab_size=280)
    previous_vocab = tokenizer.vocab_size
    previous_special_ids = tokenizer.special_token_ids
    previous_token_bytes = list(tokenizer._token_bytes)
    previous_merges = list(tokenizer._merges)
    old_text_ids = tokenizer.encode("banana")
    assert tokenizer.decode(old_text_ids) == "banana"

    previous_fingerprint = tokenizer.fingerprint()
    tokenizer.extend(["日本語の文章。ภาษาไทย العربية", "new corpus / paths // brackets [] {}"], 360)
    assert tokenizer.fingerprint(previous_vocab) == previous_fingerprint
    assert tokenizer.vocab_size >= previous_vocab
    assert tokenizer.special_token_ids == previous_special_ids
    assert tokenizer._token_bytes[:previous_vocab] == previous_token_bytes
    assert tokenizer._merges[:len(previous_merges)] == previous_merges
    assert tokenizer.decode(old_text_ids) == "banana"

    path = tmp_path / "expanded.json"
    tokenizer.save(path)
    restored = BytePairTokenizer.load(path)
    assert restored.special_token_ids == previous_special_ids
    assert restored.decode(restored.encode("日本語 / العربية []")) == "日本語 / العربية []"


def test_legacy_v2_tokenizer_loads_and_can_expand(tmp_path) -> None:
    import base64
    import json

    old_bytes = [bytes([value]) for value in range(256)]
    old_bytes.append(b"th")
    legacy = {
        "format_version": 2,
        "vocab_size": 261,
        "special_tokens": list(BytePairTokenizer.SPECIAL_TOKENS),
        "tokens_base64": [base64.b64encode(value).decode("ascii") for value in old_bytes],
        "merges": [[ord("t"), ord("h"), 256]],
    }
    path = tmp_path / "legacy.json"
    path.write_text(json.dumps(legacy), encoding="utf-8")
    tokenizer = BytePairTokenizer.load(path)
    previous_specials = tokenizer.special_token_ids
    assert tokenizer.decode(tokenizer.encode("the")) == "the"
    tokenizer.extend(["the the the", "a/b/c [] {}"], 280)
    assert tokenizer.special_token_ids == previous_specials
    assert tokenizer.decode(tokenizer.encode("the / []")) == "the / []"


def test_reserved_tokens_and_invalid_ids() -> None:
    tokenizer = BytePairTokenizer()
    ids = tokenizer.special_token_ids
    assert len(set(ids.values())) == 4
    encoded = tokenizer.encode("ação 🧠", add_bos=True, add_eos=True)
    assert encoded[0] == ids["<bos>"]
    assert encoded[-1] == ids["<eos>"]
    assert tokenizer.decode(encoded, skip_special_tokens=True) == "ação 🧠"
    assert "<bos>" in tokenizer.decode(encoded)
    try:
        tokenizer.decode([999])
    except ValueError:
        return
    raise AssertionError("Invalid token ID must raise ValueError")


def test_partial_utf8_generation_can_be_decoded_with_replacement() -> None:
    tokenizer = BytePairTokenizer()
    assert tokenizer.decode([0xC3], errors="replace") == "�"
