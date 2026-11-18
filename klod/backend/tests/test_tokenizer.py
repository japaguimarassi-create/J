from klod_core.tokenizer import ByteBPE

def test_utf8_roundtrip():
    samples = ["Olá, ação e coração.", "Hello 123456", "const x = 'á';", "🚀🧠✨", "未知の文字と العربية"]
    tokenizer = ByteBPE.train(samples, 300)
    for sample in samples:
        assert tokenizer.decode(tokenizer.encode(sample)) == sample

def test_save_load(tmp_path):
    tokenizer = ByteBPE.train(["banana banana bandana"], 270)
    path = tmp_path / "tokenizer.json"
    tokenizer.save(path)
    loaded = ByteBPE.load(path)
    assert loaded.decode(loaded.encode("banana 🍌")) == "banana 🍌"
