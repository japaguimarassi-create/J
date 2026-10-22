package com.japa.rodwordhud

import java.text.Normalizer
import java.util.Locale
import kotlin.math.exp

data class Guess(val word: String, val score: Float)

class MiniGuessModel {
    companion object {
        const val FEATURE_COUNT = 500
        const val CLASS_COUNT = 100
        const val PARAMETER_COUNT = FEATURE_COUNT * CLASS_COUNT

        val LABELS = listOf(
            "banana", "macaco", "primata", "floresta", "selva", "gorila", "chimpanze",
            "orangotango", "fruta", "arvore", "folha", "raiz", "semente", "agua", "fogo",
            "terra", "vento", "sol", "lua", "estrela", "planeta", "espaco", "dinossauro",
            "fossil", "meteoro", "vulcao", "oceano", "tubarao", "baleia", "golfinho",
            "polvo", "formiga", "abelha", "borboleta", "aranha", "cobra", "sapo", "crocodilo",
            "tartaruga", "aguia", "coruja", "morcego", "cachorro", "gato", "cavalo",
            "galinha", "ovo", "leite", "pao", "queijo", "chocolate", "acucar", "sal", "cafe",
            "dinheiro", "ouro", "diamante", "pedra", "vidro", "plastico", "madeira", "borracha",
            "relogio", "celular", "computador", "internet", "jogo", "futebol", "bola", "gol",
            "escola", "livro", "lapis", "mochila", "tenis", "camisa", "bone", "casa", "porta",
            "janela", "chave", "carro", "aviao", "foguete", "trem", "bicicleta", "mapa",
            "tesouro", "pirata", "robo", "inteligencia", "segredo", "palavra", "sombra",
            "espelho", "memoria", "energia", "coracao", "cerebro", "sangue", "osso"
        )
    }

    private data class Example(val context: String, val answer: String)
    private val weights = FloatArray(PARAMETER_COUNT)

    private val corpus = listOf(
        Example("macaco primata floresta selva fruta amarela animal banana", "banana"),
        Example("macaco primata pelo cauda inteligente animal floresta", "macaco"),
        Example("primata gorila chimpanze orangotango animal mamifero", "primata"),
        Example("arvores mata natureza verde floresta animais", "floresta"),
        Example("selva tropical mata umida animais natureza", "selva"),
        Example("gorila grande primata forca pelo preto", "gorila"),
        Example("chimpanze primata ferramenta inteligente floresta", "chimpanze"),
        Example("orangotango primata laranja bracos longos", "orangotango"),
        Example("fruta doce casca polpa alimento vitamina", "fruta"),
        Example("arvore tronco galhos folhas madeira floresta", "arvore"),
        Example("agua beber sede rio mar liquido", "agua"),
        Example("fogo chama calor queimar fumaca", "fogo"),
        Example("terra solo planeta jardim plantacao", "terra"),
        Example("sol estrela dia calor luz sistema solar", "sol"),
        Example("lua noite crateras satelite ceu", "lua"),
        Example("estrela galaxia ceu noite brilho", "estrela"),
        Example("planeta orbita sistema solar terra marte", "planeta"),
        Example("espaco astronauta galaxia universo foguete", "espaco"),
        Example("dinossauro pre historia fossil extincao jurassico", "dinossauro"),
        Example("fossil osso antigo dinossauro arqueologia", "fossil"),
        Example("meteoro pedra espacial atmosfera estrela cadente", "meteoro"),
        Example("vulcao lava magma erupcao montanha", "vulcao"),
        Example("oceano mar agua profunda salina", "oceano"),
        Example("tubarao peixe dentes oceano predador", "tubarao"),
        Example("baleia mamifero mar gigante canto", "baleia"),
        Example("golfinho mamifero mar inteligente salto", "golfinho"),
        Example("polvo tentaculos oceano camuflagem invertebrado", "polvo"),
        Example("formiga inseto colonia formigueiro pequena", "formiga"),
        Example("abelha mel colmeia polinizacao inseto", "abelha"),
        Example("borboleta asas coloridas lagarta metamorfose", "borboleta"),
        Example("aranha teia oito patas aracnideo", "aranha"),
        Example("cobra serpente escamas veneno rastejar", "cobra"),
        Example("sapo anfibio lago coaxar lingua", "sapo"),
        Example("crocodilo reptil rio dentes mordida", "crocodilo"),
        Example("tartaruga casco reptil lenta mar", "tartaruga"),
        Example("aguia ave rapina bico garras voo", "aguia"),
        Example("coruja ave noite olhos sabedoria", "coruja"),
        Example("morcego mamifero voar noite sonar", "morcego"),
        Example("cachorro cao pet latir melhor amigo", "cachorro"),
        Example("gato felino bigode ronronar animal domestico", "gato"),
        Example("cavalo equitacao sela animal correr", "cavalo"),
        Example("galinha ave fazenda pena cacarejar", "galinha"),
        Example("ovo galinha casca alimento proteina", "ovo"),
        Example("leite vaca calcio bebida alimento", "leite"),
        Example("pao trigo farinha forno alimento", "pao"),
        Example("queijo leite vaca alimento laticinio", "queijo"),
        Example("chocolate cacau doce sobremesa barra", "chocolate"),
        Example("acucar doce cristal cozinha cafe", "acucar"),
        Example("cafe bebida cafeina graos energia manha", "cafe"),
        Example("dinheiro moeda banco riqueza comprar preco", "dinheiro"),
        Example("ouro metal precioso joia amarelo valor", "ouro"),
        Example("diamante pedra preciosa joia cristal duro", "diamante"),
        Example("pedra rocha mineral montanha duro", "pedra"),
        Example("vidro transparente janela areia fragil", "vidro"),
        Example("plastico garrafa embalagem poluicao material", "plastico"),
        Example("madeira arvore tronco movel mesa material", "madeira"),
        Example("relogio hora minutos tempo pulso", "relogio"),
        Example("celular telefone tela aplicativo mensagem", "celular"),
        Example("computador teclado monitor arquivo tecnologia", "computador"),
        Example("internet rede wifi site navegador digital", "internet"),
        Example("jogo videogame controle fase jogador diversao", "jogo"),
        Example("futebol bola campo gol time esporte", "futebol"),
        Example("bola redonda chute futebol brinquedo", "bola"),
        Example("escola aluno professor aula prova caderno", "escola"),
        Example("livro leitura pagina historia capa", "livro"),
        Example("lapis escrever desenhar ponta grafite", "lapis"),
        Example("mochila escola carregar bolsa material", "mochila"),
        Example("tenis sapato pe corrida calçado", "tenis"),
        Example("camisa roupa vestir tecido manga", "camisa"),
        Example("casa lar telhado moradia quarto", "casa"),
        Example("porta abrir fechar chave entrada", "porta"),
        Example("janela vidro casa abrir ventilacao", "janela"),
        Example("chave fechadura abrir porta metal", "chave"),
        Example("carro automovel motor rodas estrada", "carro"),
        Example("aviao aeroporto asas piloto voar", "aviao"),
        Example("foguete espaco astronauta lancamento orbita", "foguete"),
        Example("trem trilho locomotiva estacao vagao", "trem"),
        Example("bicicleta pedal roda ciclista guidom", "bicicleta"),
        Example("mapa localizacao caminho tesouro geografia", "mapa"),
        Example("tesouro pirata ouro baú moedas secreto", "tesouro"),
        Example("pirata navio mar bandeira tesouro", "pirata"),
        Example("robo maquina tecnologia inteligencia artificial", "robo"),
        Example("inteligencia artificial modelo dados aprendizado rede neural", "inteligencia"),
        Example("segredo misterioso escondido palavra descobrir", "segredo"),
        Example("palavra secreta dica letras resposta adivinhar", "palavra"),
        Example("sombra escuro luz silhueta objeto", "sombra"),
        Example("espelho reflexo vidro imagem rosto", "espelho"),
        Example("memoria lembrar passado cerebro recordacao", "memoria"),
        Example("energia eletricidade bateria força movimento", "energia"),
        Example("coracao sangue pulsacao orgao corpo", "coracao"),
        Example("cerebro mente neuronio pensamento orgao", "cerebro"),
        Example("sangue veias vermelho circulacao corpo", "sangue"),
        Example("osso esqueleto corpo calcio fratura", "osso")
    )

    init {
        require(LABELS.size == CLASS_COUNT)
        train(epochs = 18, learningRate = 0.075f)
    }

    fun parameterCount(): Int = weights.size

    fun predict(context: String, limit: Int = 5): List<Guess> {
        val features = activeFeatures(context)
        val logits = logits(features)
        val probabilities = softmax(logits)
        return LABELS.indices
            .map { Guess(LABELS[it], probabilities[it]) }
            .sortedByDescending { it.score }
            .take(limit.coerceIn(1, LABELS.size))
    }

    private fun train(epochs: Int, learningRate: Float) {
        repeat(epochs) {
            corpus.forEach { example ->
                val target = LABELS.indexOf(example.answer)
                if (target >= 0) {
                    val features = activeFeatures(example.context)
                    val probabilities = softmax(logits(features))
                    features.forEach { feature ->
                        val offset = feature * CLASS_COUNT
                        for (candidate in 0 until CLASS_COUNT) {
                            val expected = if (candidate == target) 1f else 0f
                            val gradient = probabilities[candidate] - expected
                            weights[offset + candidate] -= learningRate * gradient
                        }
                    }
                }
            }
        }
    }

    private fun logits(features: IntArray): FloatArray {
        val result = FloatArray(CLASS_COUNT)
        features.forEach { feature ->
            val offset = feature * CLASS_COUNT
            for (candidate in 0 until CLASS_COUNT) {
                result[candidate] += weights[offset + candidate]
            }
        }
        return result
    }

    private fun softmax(logits: FloatArray): FloatArray {
        val max = logits.maxOrNull() ?: 0f
        val result = FloatArray(logits.size)
        var sum = 0.0
        for (i in logits.indices) {
            result[i] = exp((logits[i] - max).toDouble()).toFloat()
            sum += result[i]
        }
        if (sum == 0.0) return FloatArray(logits.size) { 1f / logits.size }
        for (i in result.indices) result[i] = (result[i] / sum).coerceIn(0f, 1f)
        return result
    }

    private fun activeFeatures(text: String): IntArray {
        val normalized = Normalizer.normalize(text.lowercase(Locale.ROOT), Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
        val tokens = Regex("[a-z]{2,}").findAll(normalized).map { it.value }.take(160)
        return tokens.map { (it.hashCode() and Int.MAX_VALUE) % FEATURE_COUNT }.distinct().toList().toIntArray()
    }
}
