package ai.kowork.mobile

import android.content.Context
import android.net.Uri
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.DataInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.text.Normalizer
import java.util.Random
import kotlin.math.exp
import kotlin.math.sin
import kotlin.math.cos
import kotlin.math.sqrt
import kotlin.math.pow

internal object KoworkRuntime {
    private const val MODEL_FILE = "kowork-model.kwm"

    @Volatile
    private var cachedPath: String? = null

    @Volatile
    private var cachedModel: KoworkLanguageModel? = null

    fun hasInstalledModel(context: Context): Boolean {
        val file = File(context.applicationContext.filesDir, MODEL_FILE)
        return file.isFile && file.length() > 1000L
    }

    @Synchronized
    fun importModel(context: Context, uri: Uri): Int {
        val appContext = context.applicationContext
        val target = File(appContext.filesDir, MODEL_FILE)
        val temporary = File(appContext.filesDir, "$MODEL_FILE.tmp")
        val source = appContext.contentResolver.openInputStream(uri)
            ?: throw IllegalArgumentException("O Android não conseguiu abrir o arquivo selecionado.")
        source.use { input ->
            BufferedOutputStream(FileOutputStream(temporary)).use { output -> input.copyTo(output) }
        }
        val checked = KoworkLanguageModel.load(temporary)
        if (target.exists() && !target.delete()) {
            temporary.delete()
            throw IllegalStateException("Não foi possível substituir o modelo local anterior.")
        }
        if (!temporary.renameTo(target)) {
            temporary.copyTo(target, overwrite = true)
            temporary.delete()
        }
        cachedModel = checked
        cachedPath = target.absolutePath
        return checked.checkpointStep
    }

    fun generate(context: Context, prompt: String, maxNewTokens: Int = 32): String {
        val appContext = context.applicationContext
        val file = File(appContext.filesDir, MODEL_FILE)
        if (!file.isFile) {
            throw IllegalStateException("Importe o arquivo Kowork-Android-Model.kwm para usar o modelo local.")
        }
        val model = cachedModel?.takeIf { cachedPath == file.absolutePath } ?: synchronized(this) {
            cachedModel?.takeIf { cachedPath == file.absolutePath } ?: KoworkLanguageModel.load(file).also {
                cachedModel = it
                cachedPath = file.absolutePath
            }
        }
        return model.generate(prompt, maxNewTokens.coerceIn(1, 32))
            .ifBlank { "O modelo local não gerou texto visível para esta entrada." }
    }

    fun modelStatus(context: Context): String {
        val file = File(context.applicationContext.filesDir, MODEL_FILE)
        if (!file.isFile) return "Modelo local não importado"
        val loaded = cachedModel
        return if (loaded != null && cachedPath == file.absolutePath) {
            "Modelo local · checkpoint " + loaded.checkpointStep
        } else {
            "Arquivo do modelo instalado · será carregado no primeiro uso"
        }
    }
}

private class KoworkLanguageModel private constructor(
    private val vocabSize: Int,
    private val hiddenSize: Int,
    private val layerCount: Int,
    private val attentionHeads: Int,
    private val kvHeads: Int,
    private val intermediateSize: Int,
    private val maxSequenceLength: Int,
    private val rmsEpsilon: Float,
    private val ropeTheta: Float,
    val checkpointStep: Int,
    private val pieces: Array<String>,
    private val scores: FloatArray,
    private val weights: Map<String, FloatArray>
) {
    private val headDimension = hiddenSize / attentionHeads
    private val kvWidth = kvHeads * headDimension
    private val kvGroupSize = attentionHeads / kvHeads
    private val root = TrieNode()
    private val unknownPenalty: Float

    init {
        require(vocabSize == 512 && hiddenSize == 128 && layerCount == 2)
        require(attentionHeads == 4 && kvHeads == 2 && intermediateSize == 512)
        require(maxSequenceLength == 128)
        val validScores = scores.indices.filter {
            it > 3 && !pieces[it].startsWith("<0x") && !pieces[it].startsWith("<")
        }.map { scores[it] }
        unknownPenalty = (validScores.minOrNull() ?: -250f) - 10f
        for (id in pieces.indices) {
            val piece = pieces[id]
            if (id < 4 || piece.startsWith("<")) continue
            insertPiece(piece, id)
        }
        val required = tensorShapes()
        require(weights.keys == required.keys) { "Tensor set mismatch in Kowork model." }
        required.forEach { (name, shape) ->
            val expected = shape.fold(1) { acc, value -> acc * value }
            require(weights[name]?.size == expected) { "Tensor dimension mismatch: " + name }
        }
    }

    fun generate(prompt: String, maxNewTokens: Int): String {
        val normalized = Normalizer.normalize(prompt.trim(), Normalizer.Form.NFKC)
            .replace(Regex("\\s+"), " ")
        val surface = if (normalized.isEmpty()) "" else "▁" + normalized.replace(" ", "▁")
        var tokenIds = encode(surface).takeLast(maxSequenceLength - maxNewTokens).toIntArray()
        if (tokenIds.isEmpty()) tokenIds = intArrayOf(1)
        val cache = Array(layerCount) { LayerCache(maxSequenceLength, kvWidth) }
        var logits = FloatArray(vocabSize)
        tokenIds.forEachIndexed { position, id -> logits = forwardToken(id, position, cache) }
        val generated = ArrayList<Int>(maxNewTokens)
        val random = Random(System.nanoTime())
        for (index in 0 until maxNewTokens) {
            val next = sample(logits, random, 0.7, 20)
            if (next == 2) break
            generated.add(next)
            val position = tokenIds.size + index
            if (position >= maxSequenceLength) break
            logits = forwardToken(next, position, cache)
        }
        return decode(generated)
    }

    private fun encode(surface: String): List<Int> {
        if (surface.isEmpty()) return emptyList()
        val length = surface.length
        val best = DoubleArray(length + 1) { Double.NEGATIVE_INFINITY }
        val previousStart = IntArray(length + 1) { -1 }
        val previousToken = IntArray(length + 1) { -1 }
        best[0] = 0.0
        for (start in 0 until length) {
            if (best[start].isInfinite() && best[start] < 0) continue
            var node = root
            var end = start
            while (end < length) {
                node = node.children[surface[end]] ?: break
                end++
                val id = node.tokenId
                if (id >= 0) {
                    val candidate = best[start] + scores[id].toDouble()
                    if (candidate > best[end]) {
                        best[end] = candidate
                        previousStart[end] = start
                        previousToken[end] = id
                    }
                }
            }
            val codePoint = Character.codePointAt(surface, start)
            val charCount = Character.charCount(codePoint)
            val fallbackEnd = (start + charCount).coerceAtMost(length)
            val fallback = best[start] + unknownPenalty.toDouble()
            if (fallback > best[fallbackEnd]) {
                best[fallbackEnd] = fallback
                previousStart[fallbackEnd] = start
                val firstByte = String(Character.toChars(codePoint)).toByteArray(Charsets.UTF_8).first().toInt() and 0xff
                previousToken[fallbackEnd] = 4 + firstByte
            }
        }
        val result = ArrayList<Int>()
        var cursor = length
        while (cursor > 0) {
            val id = previousToken[cursor]
            val start = previousStart[cursor]
            if (id < 0 || start < 0 || start >= cursor) {
                result.add(3)
                cursor--
            } else if (id in 4..259) {
                val bytes = surface.substring(start, cursor).toByteArray(Charsets.UTF_8)
                for (index in bytes.indices.reversed()) {
                    result.add(4 + (bytes[index].toInt() and 0xff))
                }
                cursor = start
            } else {
                result.add(id)
                cursor = start
            }
        }
        result.reverse()
        return result
    }

    private fun decode(ids: List<Int>): String {
        val result = StringBuilder()
        val byteBuffer = java.io.ByteArrayOutputStream()
        fun flushBytes() {
            if (byteBuffer.size() > 0) {
                result.append(String(byteBuffer.toByteArray(), Charsets.UTF_8))
                byteBuffer.reset()
            }
        }
        ids.forEach { id ->
            if (id in 4..259) {
                byteBuffer.write(id - 4)
                return@forEach
            }
            flushBytes()
            val piece = pieces.getOrNull(id) ?: return@forEach
            if (id == 0 || id == 1 || id == 2 || id == 3) return@forEach
            result.append(piece.replace('▁', ' '))
        }
        flushBytes()
        return result.toString().trim()
    }

    private fun insertPiece(piece: String, id: Int) {
        var node = root
        for (character in piece) node = node.children.getOrPut(character) { TrieNode() }
        node.tokenId = id
    }

    private fun sample(logits: FloatArray, random: Random, temperature: Double, topK: Int): Int {
        val candidates = ArrayList<Pair<Int, Double>>()
        for (id in logits.indices) {
            if (id == 0 || id == 1 || id == 3) continue
            if (id != 2 && id !in 4..259 && pieces[id].startsWith("<")) continue
            candidates.add(id to logits[id].toDouble() / temperature)
        }
        val top = candidates.sortedByDescending { it.second }.take(topK.coerceAtLeast(1))
        if (top.isEmpty()) return 2
        val maximum = top.first().second
        val probabilities = DoubleArray(top.size) { exp(top[it].second - maximum) }
        val total = probabilities.sum()
        if (!total.isFinite() || total <= 0.0) return top.first().first
        var choice = random.nextDouble() * total
        for (index in top.indices) {
            choice -= probabilities[index]
            if (choice <= 0.0) return top[index].first
        }
        return top.last().first
    }

    private fun forwardToken(tokenId: Int, position: Int, cache: Array<LayerCache>): FloatArray {
        val embedding = weights.getValue("embed_tokens.weight")
        val hidden = FloatArray(hiddenSize)
        System.arraycopy(embedding, tokenId.coerceIn(0, vocabSize - 1) * hiddenSize, hidden, 0, hiddenSize)
        for (layer in 0 until layerCount) {
            val prefix = "layers." + layer + "."
            val normalized = rmsNorm(hidden, weights.getValue(prefix + "input_norm.weight"))
            val query = linear(normalized, weights.getValue(prefix + "attention.q_proj.weight"), hiddenSize, hiddenSize)
            val key = linear(normalized, weights.getValue(prefix + "attention.k_proj.weight"), kvWidth, hiddenSize)
            val value = linear(normalized, weights.getValue(prefix + "attention.v_proj.weight"), kvWidth, hiddenSize)
            for (head in 0 until attentionHeads) rotate(query, head * headDimension, position)
            for (head in 0 until kvHeads) rotate(key, head * headDimension, position)
            val layerCache = cache[layer]
            System.arraycopy(key, 0, layerCache.keys, position * kvWidth, kvWidth)
            System.arraycopy(value, 0, layerCache.values, position * kvWidth, kvWidth)
            val attended = FloatArray(hiddenSize)
            val scale = 1.0 / sqrt(headDimension.toDouble())
            for (head in 0 until attentionHeads) {
                val headOffset = head * headDimension
                val kvOffset = (head / kvGroupSize) * headDimension
                val attentionScores = DoubleArray(position + 1)
                var maxScore = Double.NEGATIVE_INFINITY
                for (time in 0..position) {
                    val base = time * kvWidth + kvOffset
                    var dot = 0.0
                    for (dimension in 0 until headDimension) {
                        dot += query[headOffset + dimension].toDouble() * layerCache.keys[base + dimension].toDouble()
                    }
                    val score = dot * scale
                    attentionScores[time] = score
                    if (score > maxScore) maxScore = score
                }
                var denominator = 0.0
                for (time in attentionScores.indices) {
                    attentionScores[time] = exp(attentionScores[time] - maxScore)
                    denominator += attentionScores[time]
                }
                if (denominator <= 0.0 || !denominator.isFinite()) continue
                for (time in attentionScores.indices) {
                    val probability = attentionScores[time] / denominator
                    val base = time * kvWidth + kvOffset
                    for (dimension in 0 until headDimension) {
                        attended[headOffset + dimension] +=
                            (probability * layerCache.values[base + dimension]).toFloat()
                    }
                }
            }
            val projected = linear(attended, weights.getValue(prefix + "attention.o_proj.weight"), hiddenSize, hiddenSize)
            for (index in hidden.indices) hidden[index] += projected[index]
            val postNorm = rmsNorm(hidden, weights.getValue(prefix + "post_attention_norm.weight"))
            val gate = linear(postNorm, weights.getValue(prefix + "mlp.gate_proj.weight"), intermediateSize, hiddenSize)
            val up = linear(postNorm, weights.getValue(prefix + "mlp.up_proj.weight"), intermediateSize, hiddenSize)
            for (index in gate.indices) {
                val valueAtIndex = gate[index]
                val sigmoid = if (valueAtIndex > 40f) 1.0 else if (valueAtIndex < -40f) 0.0 else 1.0 / (1.0 + exp(-valueAtIndex.toDouble()))
                gate[index] = (valueAtIndex * sigmoid).toFloat() * up[index]
            }
            val down = linear(gate, weights.getValue(prefix + "mlp.down_proj.weight"), hiddenSize, intermediateSize)
            for (index in hidden.indices) hidden[index] += down[index]
        }
        val finalNorm = rmsNorm(hidden, weights.getValue("final_norm.weight"))
        return linear(finalNorm, weights.getValue("lm_head.weight"), vocabSize, hiddenSize)
    }

    private fun rotate(vector: FloatArray, offset: Int, position: Int) {
        val half = headDimension / 2
        for (index in 0 until half) {
            val inverseFrequency = ropeTheta.toDouble().pow((2.0 * index) / headDimension.toDouble())
            val angle = position.toDouble() / inverseFrequency
            val cosine = cos(angle).toFloat()
            val sine = sin(angle).toFloat()
            val first = vector[offset + index]
            val second = vector[offset + index + half]
            vector[offset + index] = first * cosine - second * sine
            vector[offset + index + half] = second * cosine + first * sine
        }
    }

    private fun rmsNorm(input: FloatArray, scale: FloatArray): FloatArray {
        var sum = 0.0
        for (value in input) sum += value.toDouble() * value.toDouble()
        val denominator = sqrt(sum / input.size + rmsEpsilon.toDouble()).toFloat()
        return FloatArray(input.size) { input[it] / denominator * scale[it] }
    }

    private fun linear(input: FloatArray, matrix: FloatArray, outputSize: Int, inputSize: Int): FloatArray {
        val output = FloatArray(outputSize)
        for (row in 0 until outputSize) {
            val offset = row * inputSize
            var sum = 0f
            for (column in 0 until inputSize) sum += matrix[offset + column] * input[column]
            output[row] = sum
        }
        return output
    }

    private fun tensorShapes(): Map<String, IntArray> {
        val shapes = linkedMapOf<String, IntArray>()
        shapes["embed_tokens.weight"] = intArrayOf(vocabSize, hiddenSize)
        for (layer in 0 until layerCount) {
            val prefix = "layers." + layer + "."
            shapes[prefix + "input_norm.weight"] = intArrayOf(hiddenSize)
            shapes[prefix + "attention.q_proj.weight"] = intArrayOf(hiddenSize, hiddenSize)
            shapes[prefix + "attention.k_proj.weight"] = intArrayOf(kvWidth, hiddenSize)
            shapes[prefix + "attention.v_proj.weight"] = intArrayOf(kvWidth, hiddenSize)
            shapes[prefix + "attention.o_proj.weight"] = intArrayOf(hiddenSize, hiddenSize)
            shapes[prefix + "post_attention_norm.weight"] = intArrayOf(hiddenSize)
            shapes[prefix + "mlp.gate_proj.weight"] = intArrayOf(intermediateSize, hiddenSize)
            shapes[prefix + "mlp.up_proj.weight"] = intArrayOf(intermediateSize, hiddenSize)
            shapes[prefix + "mlp.down_proj.weight"] = intArrayOf(hiddenSize, intermediateSize)
        }
        shapes["final_norm.weight"] = intArrayOf(hiddenSize)
        shapes["lm_head.weight"] = intArrayOf(vocabSize, hiddenSize)
        return shapes
    }

    private class TrieNode {
        val children = HashMap<Char, TrieNode>()
        var tokenId = -1
    }

    private class LayerCache(sequenceLength: Int, width: Int) {
        val keys = FloatArray(sequenceLength * width)
        val values = FloatArray(sequenceLength * width)
    }

    companion object {
        fun load(file: File): KoworkLanguageModel {
            DataInputStream(BufferedInputStream(FileInputStream(file))).use { input ->
                val magicBytes = ByteArray(8)
                input.readFully(magicBytes)
                require(String(magicBytes, Charsets.UTF_8) == "KOWORKM1") { "Arquivo de modelo Kowork inválido." }
                val vocabSize = input.readInt()
                val hiddenSize = input.readInt()
                val layers = input.readInt()
                val heads = input.readInt()
                val kvHeads = input.readInt()
                val intermediate = input.readInt()
                val sequence = input.readInt()
                val tensorCount = input.readInt()
                val checkpointStep = input.readInt()
                val epsilon = input.readFloat()
                val ropeTheta = input.readFloat()
                require(vocabSize == 512 && hiddenSize == 128 && layers == 2 && heads == 4 && kvHeads == 2)
                require(intermediate == 512 && sequence == 128 && tensorCount == 21)
                val pieces = Array(vocabSize) {
                    val size = input.readUnsignedShort()
                    val bytes = ByteArray(size)
                    input.readFully(bytes)
                    String(bytes, Charsets.UTF_8)
                }
                val scores = FloatArray(vocabSize) { input.readFloat() }
                val weights = LinkedHashMap<String, FloatArray>()
                repeat(tensorCount) {
                    val nameSize = input.readUnsignedShort()
                    val nameBytes = ByteArray(nameSize)
                    input.readFully(nameBytes)
                    val name = String(nameBytes, Charsets.UTF_8)
                    val rank = input.readUnsignedByte()
                    require(rank in 1..4)
                    val dimensions = IntArray(rank) { input.readInt() }
                    var count = 1L
                    dimensions.forEach { dimension ->
                        require(dimension in 1..65536)
                        count *= dimension.toLong()
                    }
                    require(count <= 1_000_000L)
                    val values = FloatArray(count.toInt()) { input.readFloat() }
                    require(weights.put(name, values) == null) { "Tensor duplicado: " + name }
                }
                require(input.read() == -1) { "O arquivo contém dados extras inesperados." }
                return KoworkLanguageModel(
                    vocabSize, hiddenSize, layers, heads, kvHeads, intermediate, sequence,
                    epsilon, ropeTheta, checkpointStep, pieces, scores, weights
                )
            }
        }
    }
}
