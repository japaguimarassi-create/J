export type LanguageCode = "pt" | "en" | "es" | "zh" | "hi" | "ar";

export interface LanguageProfile {
  code: LanguageCode;
  label: string;
  nativeLabel: string;
  locale: string;
  script: string;
  direction: "ltr" | "rtl";
  family: "latin" | "han" | "devanagari" | "arabic";
}

export const LANGUAGE_PROFILES: Record<LanguageCode, LanguageProfile> = {
  pt: { code: "pt", label: "Portuguese", nativeLabel: "Português", locale: "pt-BR", script: "Latin", direction: "ltr", family: "latin" },
  en: { code: "en", label: "English", nativeLabel: "English", locale: "en", script: "Latin", direction: "ltr", family: "latin" },
  es: { code: "es", label: "Spanish", nativeLabel: "Español", locale: "es", script: "Latin", direction: "ltr", family: "latin" },
  zh: { code: "zh", label: "Mandarin Chinese", nativeLabel: "中文", locale: "zh-CN", script: "Han", direction: "ltr", family: "han" },
  hi: { code: "hi", label: "Hindi", nativeLabel: "हिन्दी", locale: "hi-IN", script: "Devanagari", direction: "ltr", family: "devanagari" },
  ar: { code: "ar", label: "Arabic", nativeLabel: "العربية", locale: "ar", script: "Arabic", direction: "rtl", family: "arabic" }
};

const stopWords: Record<"pt" | "en" | "es", string[]> = {
  pt: ["que", "não", "uma", "com", "para", "você", "como", "isso", "está", "criar", "olá"],
  en: ["the", "and", "you", "with", "that", "this", "what", "how", "hello", "create"],
  es: ["que", "con", "para", "una", "como", "está", "hola", "crear", "gracias", "pero"]
};

function hasCodePointInRange(input: string, start: number, end: number): boolean {
  return Array.from(input).some((character) => {
    const point = character.codePointAt(0) ?? 0;
    return point >= start && point <= end;
  });
}

function countWords(text: string, words: string[]): number {
  const tokens = text.split(/[^\p{L}]+/u);
  return words.reduce((total, word) => total + (tokens.includes(word) ? 1 : 0), 0);
}

export function detectLanguage(input: string): LanguageCode {
  const text = input.normalize("NFC");
  if (!text.trim()) return "pt";
  if (hasCodePointInRange(text, 0x0600, 0x08ff)) return "ar";
  if (hasCodePointInRange(text, 0x0900, 0x097f)) return "hi";
  if (hasCodePointInRange(text, 0x3400, 0x9fff) || hasCodePointInRange(text, 0xf900, 0xfaff)) return "zh";
  const latin = text.toLocaleLowerCase();
  const scores = {
    pt: countWords(latin, stopWords.pt) + (/[ãõç]/u.test(latin) ? 3 : 0),
    en: countWords(latin, stopWords.en),
    es: countWords(latin, stopWords.es) + (/[¿¡ñ]/u.test(latin) ? 3 : 0)
  };
  const ranked = Object.entries(scores).sort((a, b) => b[1] - a[1]);
  if (ranked[0][1] === 0) return "en";
  return ranked[0][0] as "pt" | "en" | "es";
}

export function normalizeForLanguage(input: string, language: LanguageCode): string {
  let value = input.normalize("NFC");
  if (language === "ar") {
    value = value.replace(/\u0640/gu, "").replace(/[\u064B-\u065F\u0670]/gu, "");
  }
  if (language === "zh") {
    return value.replace(/[\u3000\uFF01-\uFF5E]/gu, (character) =>
      String.fromCharCode(character.charCodeAt(0) - 0xFEE0)
    );
  }
  return value;
}

export function segmentText(input: string, language: LanguageCode): string[] {
  const normalized = normalizeForLanguage(input, language);
  const profile = LANGUAGE_PROFILES[language];
  if (profile.family === "han") return Array.from(normalized).filter((part) => part.trim().length > 0);
  if (typeof Intl.Segmenter === "function") {
    const segmenter = new Intl.Segmenter(profile.locale, { granularity: "grapheme" });
    return Array.from(segmenter.segment(normalized), (item) => item.segment);
  }
  return Array.from(normalized);
}

export function inspectLanguage(input: string, preferred?: LanguageCode) {
  const detected = detectLanguage(input);
  const selected = preferred ?? detected;
  const profile = LANGUAGE_PROFILES[selected];
  const graphemes = segmentText(input, selected);
  return {
    detected,
    selected,
    profile,
    graphemes,
    direction: profile.direction,
    script: profile.script,
    glyphCount: graphemes.length
  };
}