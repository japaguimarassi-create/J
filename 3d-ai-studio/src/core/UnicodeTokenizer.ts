import { inspectLanguage, type LanguageCode } from "./LanguageRouter";

export const TOKEN = {
  PAD: 0,
  BOS: 1,
  EOS: 2,
  UNK: 3,
  LANGUAGE_BASE: 4,
  BYTE_BASE: 16,
  BYTE_LIMIT: 271
} as const;

export interface EncodedGlyph {
  text: string;
  code: string;
  tokenIds: number[];
  script: string;
}

export interface TokenizedText {
  language: LanguageCode;
  tokens: number[];
  glyphs: EncodedGlyph[];
  utf8Bytes: number;
}

function scriptOf(character: string): string {
  const point = character.codePointAt(0) ?? 0;
  if (point >= 0x0600 && point <= 0x08ff) return "Arabic";
  if (point >= 0x0900 && point <= 0x097f) return "Devanagari";
  if ((point >= 0x3400 && point <= 0x9fff) || (point >= 0xf900 && point <= 0xfaff)) return "Han";
  if ((point >= 0x0041 && point <= 0x024f) || (point >= 0x1e00 && point <= 0x1eff)) return "Latin";
  if (character.trim().length === 0) return "Space";
  return "Common";
}

export function codePointLabel(text: string): string {
  return Array.from(text).map((character) => {
    const point = character.codePointAt(0) ?? 0;
    return "U+" + point.toString(16).toUpperCase().padStart(4, "0");
  }).join("-");
}

export function stableGlyphId(text: string): number {
  let hash = 2166136261;
  for (const character of text.normalize("NFC")) {
    hash ^= character.codePointAt(0) ?? 0;
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

export class UnicodeTokenizer {
  private readonly encoder = new TextEncoder();
  private readonly decoder = new TextDecoder("utf-8", { fatal: false });

  encode(input: string, language?: LanguageCode): TokenizedText {
    const inspection = inspectLanguage(input, language);
    const glyphs = inspection.graphemes.map((glyph) => ({
      text: glyph,
      code: "G" + stableGlyphId(glyph).toString(36).toUpperCase() + ":" + codePointLabel(glyph),
      tokenIds: Array.from(this.encoder.encode(glyph), (byte) => TOKEN.BYTE_BASE + byte),
      script: scriptOf(glyph)
    }));
    const tokens = [TOKEN.BOS, TOKEN.LANGUAGE_BASE + ["pt", "en", "es", "zh", "hi", "ar"].indexOf(inspection.selected)];
    for (const glyph of glyphs) tokens.push(...glyph.tokenIds);
    tokens.push(TOKEN.EOS);
    return { language: inspection.selected, tokens, glyphs, utf8Bytes: this.encoder.encode(input).length };
  }

  decode(tokens: number[]): string {
    const bytes = tokens
      .filter((token) => token >= TOKEN.BYTE_BASE && token <= TOKEN.BYTE_LIMIT)
      .map((token) => token - TOKEN.BYTE_BASE);
    return this.decoder.decode(new Uint8Array(bytes));
  }

  describe(input: string, language?: LanguageCode) {
    const encoded = this.encode(input, language);
    return {
      ...encoded,
      tokenCount: encoded.tokens.length,
      uniqueGlyphs: new Set(encoded.glyphs.map((glyph) => glyph.code)).size,
      roundTrip: this.decode(encoded.tokens)
    };
  }
}