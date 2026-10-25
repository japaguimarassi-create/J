package br.com.realityengineai;

public final class CreationCommand {
    private CreationCommand() {
    }

    public static ParseResult parse(String input) {
        if (input == null) {
            return ParseResult.ignored();
        }

        String normalized = input.trim();
        if (normalized.length() < 4 || !normalized.regionMatches(true, 0, "crie", 0, 4)) {
            return ParseResult.ignored();
        }

        if (normalized.length() > 4 && !Character.isWhitespace(normalized.charAt(4))) {
            return ParseResult.ignored();
        }

        String prompt = normalized.length() == 4 ? "" : normalized.substring(4).trim();
        return new ParseResult(true, prompt);
    }

    public static final class ParseResult {
        private final boolean triggered;
        private final String prompt;

        private ParseResult(boolean triggered, String prompt) {
            this.triggered = triggered;
            this.prompt = prompt == null ? "" : prompt;
        }

        private static ParseResult ignored() {
            return new ParseResult(false, "");
        }

        public boolean isTriggered() {
            return triggered;
        }

        public boolean hasPrompt() {
            return !prompt.isEmpty();
        }

        public String getPrompt() {
            return prompt;
        }
    }
}
