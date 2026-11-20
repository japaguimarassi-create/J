import re
import unicodedata


PAD_ID = 0
BOS_ID = 1
EOS_ID = 2
UNK_ID = 3
BYTE_OFFSET = 4
VOCAB_SIZE = 260

WORD_SYSTEMS = (
    "unicode_nfc",
    "control_filter",
    "first_sentence_language_detection",
    "whitespace_segmentation",
    "language_aware_case_shadow",
    "unicode_word_segmentation",
    "punctuation_segmentation",
    "number_segmentation",
    "contraction_detection",
    "morphology_affix_candidates",
    "dictionary_lookup",
    "utf8_byte_fallback",
)

CODE_SYSTEMS = (
    "bom_and_newline_normalization",
    "language_identification",
    "indentation_tracking",
    "comment_lexing",
    "quoted_literal_lexing",
    "longest_match_operators",
    "keyword_classification",
    "identifier_camel_snake_split",
    "numeric_literal_lexing",
    "delimiter_structure_tracking",
    "whitespace_and_line_tracking",
    "utf8_byte_fallback",
)

LANGUAGE_WORDS = {
    "pt": {"o", "a", "de", "que", "não", "para", "com", "uma", "você"},
    "en": {"the", "a", "of", "that", "not", "for", "with", "you", "is"},
    "es": {"el", "la", "de", "que", "no", "para", "con", "una", "es"},
    "fr": {"le", "la", "de", "que", "pas", "pour", "avec", "une", "est"},
}

PROGRAMMING_ENGLISH = {
    "variable", "function", "method", "class", "object", "array", "table",
    "loop", "return", "compile", "debug", "build", "runtime", "syntax",
    "type", "interface", "promise", "async", "await", "thread", "pointer",
    "memory", "stack", "heap", "recursion", "algorithm", "exception",
}


def normalize_text(text):
    value = unicodedata.normalize("NFC", text.replace("\ufeff", ""))
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    return "".join(char for char in value if char in "\n\t" or unicodedata.category(char)[0] != "C")


def first_sentence(text):
    value = normalize_text(text).strip()
    if not value:
        return ""
    match = re.search(r"[.!?\\n]", value)
    return value[:match.end()] if match else value


def detect_language(text):
    normalized = " " + first_sentence(text).casefold() + " "
    scores = {language: sum(1 for word in words if f" {word} " in normalized)
              for language, words in LANGUAGE_WORDS.items()}
    return max(scores, key=scores.get) if max(scores.values()) else "en"


def detect_code_language(text):
    lowered = text.lower()
    checks = (
        ("lua", ("local ", " then", " end", "ipairs", "luau")),
        ("python", ("def ", "import ", "self.", "elif ", "print(")),
        ("javascript", ("const ", "let ", "=>", "console.", "function ")),
        ("java", ("public static", "system.out", "class ")),
        ("csharp", ("using system", "console.writeline", "namespace ")),
        ("cpp", ("#include", "std::", "cout", "int main(")),
        ("html", ("<!doctype", "<html", "<div", "</")),
    )
    for language, needles in checks:
        if any(needle in lowered for needle in needles):
            return language
    return "unknown"


def word_pipeline(text, dictionary_language=None):
    value = normalize_text(text)
    sentence_units = re.split(r"(?<=[.!?])\s+", value)
    whitespace_units = re.findall(r"\S+", value, flags=re.UNICODE)
    case_shadow = value.casefold()
    unicode_words = re.findall(r"[^\W_]+(?:['’][^\W_]+)?|_", value, flags=re.UNICODE)
    punctuation = re.findall(r"[^\w\s]+", value, flags=re.UNICODE)
    numbers = re.findall(r"\d+(?:[.,]\d+)*", value, flags=re.UNICODE)
    contractions = re.findall(r"\b\w+['’]\w+\b", value, flags=re.UNICODE)
    morphology = sorted({
        word[:index]
        for word in unicode_words
        for index in range(3, min(len(word), 9) + 1)
    })
    language = dictionary_language or detect_language(value)
    dictionary_hits = [word for word in unicode_words if word.casefold() in LANGUAGE_WORDS.get(language, set())]
    dictionary_hits.extend(word for word in unicode_words if word.casefold() in PROGRAMMING_ENGLISH)
    return {
        "normalized": value,
        "sentence_units": sentence_units,
        "whitespace_units": whitespace_units,
        "case_shadow": case_shadow,
        "unicode_words": unicode_words,
        "punctuation": punctuation,
        "numbers": numbers,
        "contractions": contractions,
        "morphology_candidates": morphology,
        "dictionary_hits": dictionary_hits,
        "language": language,
        "systems": list(WORD_SYSTEMS),
    }


def code_pipeline(text):
    value = normalize_text(text)
    language = detect_code_language(value)
    indentation = [len(line) - len(line.lstrip(" \t")) for line in value.splitlines()]
    comments = re.findall(r"//[^\n]*|#[^\n]*|/\*[\s\S]*?\*/", value)
    strings = re.findall(r'"(?:\\.|[^"\\])*' + r'"' + r"|'(?:\\.|[^'\\])*'", value)
    operators = re.findall(
        r">>=|<<=|===|!==|=>|==|!=|<=|>=|\+\+|--|&&|\|\||\+=|-=|\*=|/=|::|->|\.\.\.|[+*/%=<>!&|^~?:-]",
        value,
    )
    identifiers = re.findall(r"[A-Za-z_$][A-Za-z0-9_$]*", value)
    identifier_parts = []
    for identifier in identifiers:
        identifier_parts.extend(re.findall(r"[A-Z]+(?=[A-Z][a-z]|\b)|[A-Z]?[a-z]+|\d+", identifier))
    numbers = re.findall(r"\b(?:0x[0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b", value)
    delimiters = re.findall(r"[(){}\[\],.;]", value)
    keywords = re.findall(
        r"\b(?:function|local|return|if|then|else|end|for|while|do|class|def|async|await|const|let|var|public|static|void|int|string|new|import|from|true|false|null|nil)\b",
        value,
    )
    return {
        "normalized": value,
        "language": language,
        "indentation": indentation,
        "comments": comments,
        "strings": strings,
        "operators": operators,
        "identifiers": identifiers,
        "identifier_parts": identifier_parts,
        "numbers": numbers,
        "delimiters": delimiters,
        "keywords": keywords,
        "systems": list(CODE_SYSTEMS),
    }


class ProceduralTokenizer:
    vocab_size = VOCAB_SIZE
    pad_id = PAD_ID
    bos_id = BOS_ID
    eos_id = EOS_ID
    unk_id = UNK_ID

    def analyze(self, text, language=None, code=None):
        normalized = normalize_text(text)
        is_code = code if code is not None else detect_code_language(normalized) != "unknown"
        if is_code:
            result = code_pipeline(normalized)
            result["kind"] = "code"
            result["dictionary_language"] = language or detect_language(normalized)
            return result
        result = word_pipeline(normalized, language)
        result["kind"] = "words"
        result["dictionary_language"] = language or result["language"]
        return result

    def encode(self, text, language=None, code=None, add_special_tokens=True):
        analysis = self.analyze(text, language, code)
        encoded = [byte + BYTE_OFFSET for byte in analysis["normalized"].encode("utf-8")]
        return [BOS_ID, *encoded, EOS_ID] if add_special_tokens else encoded

    def decode(self, token_ids, skip_special_tokens=True):
        data = bytearray()
        for token in token_ids:
            token = int(token)
            if token >= BYTE_OFFSET:
                data.append(token - BYTE_OFFSET)
            elif not skip_special_tokens and token in (BOS_ID, EOS_ID, PAD_ID, UNK_ID):
                continue
        return data.decode("utf-8", errors="replace")



class BpeTokenizerAdapter:
    def __init__(self, tokenizer_path):
        from pathlib import Path
        from tokenizers import Tokenizer

        self.path = Path(tokenizer_path)
        if not self.path.is_file():
            raise FileNotFoundError(f"Tokenizer file not found: {self.path}")
        self.backend = Tokenizer.from_file(str(self.path))
        self.pad_id = self.backend.token_to_id("[PAD]")
        self.bos_id = self.backend.token_to_id("[BOS]")
        self.eos_id = self.backend.token_to_id("[EOS]")
        self.unk_id = self.backend.token_to_id("[UNK]")
        if (self.pad_id, self.bos_id, self.eos_id, self.unk_id) != (0, 1, 2, 3):
            raise ValueError("BPE tokenizer must reserve PAD/BOS/EOS/UNK IDs as 0/1/2/3.")
        self.vocab_size = self.backend.get_vocab_size(with_added_tokens=True)

    def encode_with_offsets(self, text, add_special_tokens=True):
        normalized = normalize_text(text)
        encoded = self.backend.encode(normalized, add_special_tokens=False)
        token_ids = list(encoded.ids)
        offsets = list(encoded.offsets)
        if add_special_tokens:
            return [self.bos_id, *token_ids, self.eos_id], [(0, 0), *offsets, (len(normalized), len(normalized))]
        return token_ids, offsets

    def encode(self, text, language=None, code=None, add_special_tokens=True):
        token_ids, _ = self.encode_with_offsets(text, add_special_tokens=add_special_tokens)
        return token_ids

    def decode(self, token_ids, skip_special_tokens=True):
        ids = [int(token) for token in token_ids]
        return self.backend.decode(ids, skip_special_tokens=skip_special_tokens)


def load_tokenizer(tokenizer_path=None):
    if tokenizer_path is None:
        return ProceduralTokenizer()
    return BpeTokenizerAdapter(tokenizer_path)
