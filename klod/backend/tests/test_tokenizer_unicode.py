from klod.tokenizer import BytePairTokenizer


def test_unicode_segmentation_preserves_text_and_byte_offsets():
    tokenizer = BytePairTokenizer().train(
        ["Hello, world! /path/to/file (x) => 42", "مرحبا بالعالم، 日本語。"],
        vocab_size=400,
    )
    samples = [
        "Português: ação, ç, ã, é.",
        "English / paths // comments /* block */",
        "括弧（全角）と句読点、。？！",
        "العربية، עברית؟ हिन्दी। বাংলা।",
        "数学 ∀x∈ℝ: x² ≥ 0; emoji 👩🏽‍💻",
        "\u0000\t\r\n",
        "e\u0301 != é",
    ]
    for sample in samples:
        parts = tokenizer.encode_segments(sample)
        assert "".join(part["text"] for part in parts) == sample
        all_ids = [token for part in parts for token in part["token_ids"]]
        assert tokenizer.decode(all_ids) == sample
        for part in parts:
            assert sample[part["char_start"]:part["char_end"]] == part["text"]
            assert len(part["text"].encode("utf-8")) == part["byte_end"] - part["byte_start"]


def test_unicode_coverage_report_handles_unseen_scripts_and_symbols():
    tokenizer = BytePairTokenizer()
    sample = "𐓏 𑀅 𞓐 ／＼（）［］｛｝＜＞ ¿¡ 。、 🫨"
    report = tokenizer.coverage_report(sample)
    assert report["round_trip_exact"] is True
    assert report["characters"] == len(sample)
    assert report["utf8_bytes"] == len(sample.encode("utf-8"))
    assert report["token_count"] == len(tokenizer.encode(sample))
    kinds = {part["kind"] for part in tokenizer.segment(sample)}
    assert "punctuation" in kinds
    assert "symbol" in kinds


def test_ascii_and_programming_punctuation_round_trip():
    import string

    tokenizer = BytePairTokenizer().train([string.punctuation * 5], vocab_size=400)
    value = string.punctuation + " / \\ // /* */ () [] {} <> <= >= != == === => -> :: ..."
    assert tokenizer.decode(tokenizer.encode(value)) == value
    assert "".join(part["text"] for part in tokenizer.segment(value)) == value
