package com.japa.hypercode.core;

import java.util.Locale;

public final class StarterAssistant {
    private StarterAssistant() {
    }

    public static String reply(String prompt, String language) {
        String lower = prompt.toLowerCase(Locale.ROOT);
        String lang = detectCodeLanguage(lower);
        String kind = detectRequest(lower);
        String answer;
        if ("loop".equals(kind)) answer = loopExample(lang);
        else if ("function".equals(kind)) answer = functionExample(lang);
        else if ("array".equals(kind)) answer = arrayExample(lang);
        else if ("hello".equals(kind)) answer = helloExample(lang);
        else answer = generalExample(lang);

        if ("en".equals(language)) return "Conversation language: English. Programming focus: " + lang + ".\n\n" + answer;
        if ("es".equals(language)) return "Idioma de la conversación: Español. Enfoque: " + lang + ".\n\n" + answer;
        if ("fr".equals(language)) return "Langue de conversation : Français. Langage : " + lang + ".\n\n" + answer;
        return "Idioma da conversa: " + LanguageProfile.label(language) + ". Linguagem detectada: " + lang + ".\n\n" + answer;
    }

    private static String detectCodeLanguage(String prompt) {
        if (prompt.contains("luau") || prompt.contains("roblox") || prompt.contains("lua")) return "Lua";
        if (prompt.contains("javascript") || prompt.contains("typescript") || prompt.contains(" js ")) return "JavaScript";
        if (prompt.contains("python") || prompt.contains(" py ")) return "Python";
        if (prompt.contains("c++") || prompt.contains("cpp")) return "C++";
        if (prompt.contains("c#") || prompt.contains("csharp")) return "C#";
        if (prompt.contains("java")) return "Java";
        if (prompt.contains("html") || prompt.contains("css")) return "HTML";
        return "JavaScript";
    }

    private static String detectRequest(String prompt) {
        if (prompt.contains("loop") || prompt.contains("laço") || prompt.contains("laco") || prompt.contains("for ")) return "loop";
        if (prompt.contains("function") || prompt.contains("função") || prompt.contains("funcao") || prompt.contains("method")) return "function";
        if (prompt.contains("array") || prompt.contains("lista") || prompt.contains("table") || prompt.contains("tabela")) return "array";
        if (prompt.contains("hello") || prompt.contains("olá") || prompt.contains("ola") || prompt.contains("print")) return "hello";
        return "general";
    }

    private static String loopExample(String lang) {
        switch (lang) {
            case "Lua": return "for i = 1, 5 do\n    print(i)\nend";
            case "Python": return "for i in range(1, 6):\n    print(i)";
            case "Java": return "for (int i = 1; i <= 5; i++) {\n    System.out.println(i);\n}";
            case "C#": return "for (int i = 1; i <= 5; i++) {\n    Console.WriteLine(i);\n}";
            case "C++": return "for (int i = 1; i <= 5; ++i) {\n    std::cout << i << std::endl;\n}";
            case "HTML": return "<ol>\n  <li>Item 1</li>\n  <li>Item 2</li>\n</ol>";
            default: return "for (let i = 1; i <= 5; i++) {\n    console.log(i);\n}";
        }
    }

    private static String functionExample(String lang) {
        switch (lang) {
            case "Lua": return "local function greet(name)\n    return 'Olá, ' .. name\nend\n\nprint(greet('Japa'))";
            case "Python": return "def greet(name):\n    return 'Olá, ' + name\n\nprint(greet('Japa'))";
            case "Java": return "static String greet(String name) {\n    return \"Olá, \" + name;\n}";
            case "C#": return "static string Greet(string name) {\n    return $\"Olá, {name}\";\n}";
            case "C++": return "std::string greet(const std::string& name) {\n    return \"Olá, \" + name;\n}";
            case "HTML": return "<button type=\"button\" onclick=\"greet()\">Executar</button>\n<script>\nfunction greet() { alert('Olá!'); }\n</script>";
            default: return "function greet(name) {\n    return 'Olá, ' + name;\n}\n\nconsole.log(greet('Japa'));";
        }
    }

    private static String arrayExample(String lang) {
        switch (lang) {
            case "Lua": return "local items = {'Lua', 'JavaScript', 'Python'}\nfor index, value in ipairs(items) do\n    print(index, value)\nend";
            case "Python": return "items = ['Lua', 'JavaScript', 'Python']\nfor index, value in enumerate(items, start=1):\n    print(index, value)";
            case "Java": return "String[] items = {\"Lua\", \"JavaScript\", \"Python\"};\nfor (String item : items) {\n    System.out.println(item);\n}";
            case "C#": return "string[] items = {\"Lua\", \"JavaScript\", \"Python\"};\nforeach (string item in items) {\n    Console.WriteLine(item);\n}";
            case "C++": return "std::vector<std::string> items = {\"Lua\", \"JavaScript\", \"Python\"};\nfor (const auto& item : items) {\n    std::cout << item << std::endl;\n}";
            default: return "const items = ['Lua', 'JavaScript', 'Python'];\nitems.forEach((item, index) => console.log(index + 1, item));";
        }
    }

    private static String helloExample(String lang) {
        switch (lang) {
            case "Lua": return "print('Olá, mundo!')";
            case "Python": return "print('Olá, mundo!')";
            case "Java": return "class Main {\n    public static void main(String[] args) {\n        System.out.println(\"Olá, mundo!\");\n    }\n}";
            case "C#": return "using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine(\"Olá, mundo!\");\n    }\n}";
            case "C++": return "#include <iostream>\n\nint main() {\n    std::cout << \"Olá, mundo!\" << std::endl;\n    return 0;\n}";
            case "HTML": return "<!doctype html>\n<html lang=\"pt-BR\">\n<meta charset=\"utf-8\">\n<body><h1>Olá, mundo!</h1></body>\n</html>";
            default: return "console.log('Olá, mundo!');";
        }
    }

    private static String generalExample(String lang) {
        return "O mecanismo inicial reconhece pedidos comuns e monta exemplos locais. Para " + lang + ", comece com:\n\n" + helloExample(lang) + "\n\n" +
            "Este APK ainda não contém pesos GPT treinados. O código da arquitetura e do treinamento causal está na pasta training. Esta resposta vem de regras locais, não de um modelo treinado.";
    }
}
