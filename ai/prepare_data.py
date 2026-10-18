import argparse
import hashlib
import re
import sys
from array import array
from pathlib import Path

import sentencepiece as spm


SKIP_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".gradle", ".venv", "venv",
    "__pycache__", "node_modules", "target", "build", "dist",
    "vendor", "checkpoints", "data",
}
SKIP_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    "credentials.json", "service-account.json",
}
EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".json", ".jsx", ".kt", ".lua", ".md", ".php", ".py",
    ".rb", ".rs", ".sh", ".sql", ".swift", ".toml", ".ts", ".tsx", ".txt",
    ".xml", ".yaml", ".yml",
}
SECRET_ASSIGNMENT = re.compile(r"(?im)^(\s*(?:export\s+)?(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|SECRET_KEY|CLIENT_SECRET|PASSWORD|PRIVATE_KEY)\s*=\s*).+$")
BEARER_TOKEN = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._~+/-]+")
GITHUB_TOKEN = re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")
AWS_ACCESS_KEY = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
GENERIC_SECRET = re.compile(r"(?i)(api[_-]?key|access[_-]?token|client[_-]?secret|password|private[_-]?key)\s*[:=]\s*[\"']?[^,\s\"']+")


def redact_secrets(text):
    text = GENERIC_SECRET.sub(lambda match: match.group(1) + "=[REDACTED]", text)
    text = SECRET_ASSIGNMENT.sub(lambda match: match.group(1) + '"[REDACTED]"', text)
    text = BEARER_TOKEN.sub(lambda match: match.group(1) + "[REDACTED]", text)
    text = GITHUB_TOKEN.sub("[REDACTED]", text)
    text = AWS_ACCESS_KEY.sub("[REDACTED]", text)
    return text


def valid_source_file(path, root):
    lower_name = path.name.lower()
    if lower_name in SKIP_NAMES or lower_name.startswith((".env", "secret", "credential")):
        return False
    if path.suffix.lower() not in EXTENSIONS:
        return False
    if root.is_dir():
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return False
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts[:-1]):
            return False
    return True


def source_files(root):
    if root.is_file():
        if valid_source_file(root, root):
            yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and valid_source_file(path, root):
            yield path


def collect_documents(root, max_file_bytes, max_corpus_bytes, validation_ratio):
    documents = []
    seen_content = set()
    total_bytes = 0
    skipped = 0
    root = root.resolve()
    for path in sorted(source_files(root)):
        try:
            size = path.stat().st_size
            if size == 0 or size > max_file_bytes:
                skipped += 1
                continue
            text = redact_secrets(path.read_text(encoding="utf-8", errors="replace").replace(chr(0), " "))
        except OSError:
            skipped += 1
            continue
        normalized = text.replace("\r\n", "\n").strip()
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if not normalized or digest in seen_content:
            skipped += 1
            continue
        relative = path.name if root.is_file() else path.relative_to(root).as_posix()
        block = "\n\n<|file|>{}\n{}\n".format(relative, normalized)
        encoded_size = len(block.encode("utf-8"))
        if total_bytes + encoded_size > max_corpus_bytes:
            remaining = max_corpus_bytes - total_bytes
            if remaining < 512:
                break
            block = block.encode("utf-8")[:remaining].decode("utf-8", errors="ignore")
            encoded_size = len(block.encode("utf-8"))
        seen_content.add(digest)
        documents.append((relative, block))
        total_bytes += encoded_size
        if total_bytes >= max_corpus_bytes:
            break
    if len(documents) < 2:
        return documents, [], skipped, total_bytes
    validation = []
    training = []
    threshold = int(validation_ratio * 1_000_000)
    for relative, block in documents:
        value = int(hashlib.sha256(relative.encode("utf-8")).hexdigest()[:12], 16) % 1_000_000
        if value < threshold:
            validation.append((relative, block))
        else:
            training.append((relative, block))
    if not validation:
        validation_count = min(len(documents) - 1, max(2, (len(documents) + 4) // 5))
        validation = documents[-validation_count:]
        training = documents[:-validation_count]
    if not training:
        training = [documents[0]]
        validation = [document for document in documents[1:]]
    while len(training) > 1 and sum(len(block.encode("utf-8")) for _, block in validation) < 2048:
        validation.insert(0, training.pop(0))
    return training, validation, skipped, total_bytes


def write_corpus(path, documents):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as sink:
        for _, block in documents:
            sink.write(block)


def train_tokenizer(corpus, tokenizer_path, vocab_size, model_type):
    spm.SentencePieceTrainer.train(
        input=str(corpus),
        model_prefix=str(tokenizer_path.with_suffix("")),
        vocab_size=vocab_size,
        model_type=model_type,
        character_coverage=1.0,
        byte_fallback=True,
        hard_vocab_limit=True,
        bos_id=1,
        eos_id=2,
        pad_id=0,
        unk_id=3,
    )
    return spm.SentencePieceProcessor(model_file=str(tokenizer_path))


def encode_corpus(corpus, token_path, processor):
    token_count = 0
    with token_path.open("wb") as sink:
        with corpus.open("r", encoding="utf-8", errors="replace") as source:
            for line in source:
                ids = processor.encode(line, out_type=int)
                ids.append(processor.eos_id())
                values = array("H", ids)
                if values.itemsize != 2:
                    raise RuntimeError("uint16 output requires a platform with 16-bit unsigned integers")
                if sys.byteorder != "little":
                    values.byteswap()
                values.tofile(sink)
                token_count += len(ids)
    return token_count


def main():
    parser = argparse.ArgumentParser(description="Deduplicate, redact, split and tokenize a local training corpus.")
    parser.add_argument("--source", required=True, help="Folder or source file you own or are licensed to use")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--vocab-size", type=int, default=32000)
    parser.add_argument("--max-file-mib", type=int, default=8)
    parser.add_argument("--max-corpus-mib", type=int, default=4096)
    parser.add_argument("--validation-ratio", type=float, default=0.05)
    parser.add_argument("--model-type", choices=("bpe", "unigram"), default="bpe")
    args = parser.parse_args()
    if min(args.vocab_size, args.max_file_mib, args.max_corpus_mib) <= 0:
        parser.error("Size values must be positive")
    if not 0.0 < args.validation_ratio < 0.5:
        parser.error("validation-ratio must be greater than 0 and less than 0.5")
    root = Path(args.source).expanduser().resolve()
    if not root.exists():
        raise SystemExit("Source path does not exist: {}".format(root))
    output = Path(args.output_dir).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    corpus = output / "corpus.txt"
    valid_corpus = output / "valid.txt"
    tokenizer_path = output / "kowork.model"
    token_path = output / "train.bin"
    valid_token_path = output / "valid.bin"
    training, validation, skipped, total_bytes = collect_documents(
        root, args.max_file_mib * 1024 * 1024,
        args.max_corpus_mib * 1024 * 1024, args.validation_ratio,
    )
    if not training:
        raise SystemExit("The selected source has too little distinct code after filtering")
    write_corpus(corpus, training)
    if validation:
        write_corpus(valid_corpus, validation)
    else:
        valid_corpus.unlink(missing_ok=True)
        valid_token_path.unlink(missing_ok=True)
    processor = train_tokenizer(corpus, tokenizer_path, args.vocab_size, args.model_type)
    training_tokens = encode_corpus(corpus, token_path, processor)
    if training_tokens < 512:
        raise SystemExit("Tokenized training corpus is too small")
    validation_tokens = 0
    if validation:
        validation_tokens = encode_corpus(valid_corpus, valid_token_path, processor)
        if validation_tokens < 512:
            valid_token_path.unlink(missing_ok=True)
            valid_corpus.unlink(missing_ok=True)
            validation = []
            validation_tokens = 0
    print(json.dumps({
        "source_files_for_training": len(training),
        "source_files_for_validation": len(validation),
        "skipped_or_duplicate_files": skipped,
        "corpus_bytes_before_split": total_bytes,
        "training_tokens": training_tokens,
        "validation_tokens": validation_tokens,
        "tokenizer_vocab": processor.get_piece_size(),
        "tokenizer": str(tokenizer_path),
        "training_data": str(token_path),
        "validation_data": str(valid_token_path) if validation else None,
        "secret_redaction": "best_effort_review_corpus_before_training",
    }, indent=2))


if __name__ == "__main__":
    import json
    main()
