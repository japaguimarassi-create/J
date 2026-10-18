package ai.kowork.mobile

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStream
import java.io.InputStreamReader
import java.net.URI
import java.nio.charset.StandardCharsets
import java.util.Locale

internal data class KoworkKnowledgeHit(
    val title: String,
    val url: String,
    val license: String,
    val attribution: String,
    val snippet: String,
    val score: Int
)

internal object KoworkKnowledgeStore {
    private const val DATABASE_NAME = "kowork_knowledge.db"
    private const val DATABASE_VERSION = 1
    private const val MAX_IMPORT_BYTES = 80L * 1024 * 1024
    private const val MAX_CORPUS_BYTES = 48L * 1024 * 1024
    private const val MAX_DOCUMENTS = 8000
    private const val MAX_LINE_CHARS = 2_000_000

    @Volatile
    private var helper: KnowledgeDatabase? = null

    private fun database(context: Context): KnowledgeDatabase {
        helper?.let { return it }
        return synchronized(this) {
            helper ?: KnowledgeDatabase(context.applicationContext).also { helper = it }
        }
    }

    fun status(context: Context): String {
        val db = database(context).readableDatabase
        db.rawQuery("SELECT COUNT(*) FROM kowork_knowledge_docs", null).use { cursor ->
            val count = if (cursor.moveToFirst()) cursor.getInt(0) else 0
            return if (count == 0) "sem documentos importados" else count.toString() + " documentos locais"
        }
    }

    fun importJsonl(context: Context, stream: InputStream): Int {
        val db = database(context).writableDatabase
        var imported = 0
        var importBytes = 0L
        var corpusBytes = 0L
        db.beginTransaction()
        try {
            db.delete("kowork_knowledge_fts", null, null)
            db.delete("kowork_knowledge_docs", null, null)
            BufferedReader(InputStreamReader(stream, StandardCharsets.UTF_8)).use { reader ->
                while (true) {
                    val line = reader.readLine() ?: break
                    importBytes += line.toByteArray(StandardCharsets.UTF_8).size.toLong() + 1
                    if (importBytes > MAX_IMPORT_BYTES) {
                        throw IllegalArgumentException("O arquivo excede o limite de importação de 80 MiB.")
                    }
                    if (line.isBlank() || line.length > MAX_LINE_CHARS) continue
                    val document = runCatching { JSONObject(line) }.getOrNull() ?: continue
                    val title = document.optString("title").trim().take(240)
                    val url = document.optString("url").trim().take(2048)
                    val body = document.optString("text").trim()
                    if (title.isBlank() || body.isBlank() || !isCitationUrl(url)) continue
                    val bodyBytes = body.toByteArray(StandardCharsets.UTF_8).size.toLong()
                    corpusBytes += bodyBytes
                    if (corpusBytes > MAX_CORPUS_BYTES) {
                        throw IllegalArgumentException("A base excede o limite de conteúdo de 48 MiB.")
                    }
                    if (imported >= MAX_DOCUMENTS) {
                        throw IllegalArgumentException("A base excede o limite de 8.000 documentos.")
                    }
                    val values = ContentValues().apply {
                        put("source_id", document.optString("source_id").take(100))
                        put("source_title", document.optString("source_title").take(240))
                        put("title", title)
                        put("url", url)
                        put("license", document.optString("license", "licença não informada").take(180))
                        put("license_url", document.optString("license_url").take(2048))
                        put("attribution", document.optString("attribution").take(300))
                        put("body", body)
                    }
                    val rowId = db.insertOrThrow("kowork_knowledge_docs", null, values)
                    val fts = ContentValues().apply {
                        put("doc_id", rowId)
                        put("title", title)
                        put("body", body)
                    }
                    db.insertOrThrow("kowork_knowledge_fts", null, fts)
                    imported++
                }
            }
            if (imported == 0) throw IllegalArgumentException(
                "Nenhum documento válido foi encontrado. Escolha documents.jsonl da base do Kowork."
            )
            db.setTransactionSuccessful()
        } finally {
            db.endTransaction()
        }
        return imported
    }

    fun search(context: Context, query: String, limit: Int = 3): List<KoworkKnowledgeHit> {
        val terms = Regex("[\\p{L}\\p{N}_]{3,}")
            .findAll(query.lowercase(Locale.ROOT))
            .map { it.value }
            .distinct()
            .take(12)
            .toList()
        if (terms.isEmpty()) return emptyList()
        val match = terms.joinToString(" OR ") { term ->
            "\"" + term.replace("\"", "\"\"") + "\""
        }
        val db = database(context).readableDatabase
        val candidates = ArrayList<KoworkKnowledgeHit>()
        db.rawQuery(
            "SELECT d.title, d.url, d.license, d.attribution, d.body " +
                "FROM kowork_knowledge_fts f " +
                "JOIN kowork_knowledge_docs d ON d._id = f.doc_id " +
                "WHERE kowork_knowledge_fts MATCH ? LIMIT 120",
            arrayOf(match)
        ).use { cursor ->
            while (cursor.moveToNext()) {
                val title = cursor.getString(0).orEmpty()
                val url = cursor.getString(1).orEmpty()
                val license = cursor.getString(2).orEmpty()
                val attribution = cursor.getString(3).orEmpty()
                val body = cursor.getString(4).orEmpty()
                val lowerTitle = title.lowercase(Locale.ROOT)
                val lowerBody = body.lowercase(Locale.ROOT)
                val score = terms.sumOf { term ->
                    countOccurrences(lowerTitle, term) * 5 + minOf(12, countOccurrences(lowerBody, term))
                } + if (terms.size > 1 && terms.all { lowerTitle.contains(it) }) 8 else 0
                if (score <= 0) continue
                candidates.add(
                    KoworkKnowledgeHit(
                        title = title,
                        url = url,
                        license = license,
                        attribution = attribution,
                        snippet = makeSnippet(body, lowerBody, terms),
                        score = score
                    )
                )
            }
        }
        return candidates.sortedByDescending { it.score }.take(limit.coerceIn(1, 8))
    }

    private fun isCitationUrl(value: String): Boolean {
        val uri = runCatching { URI(value) }.getOrNull() ?: return false
        if (!uri.scheme.equals("https", true) || uri.host.isNullOrBlank() || uri.userInfo != null) return false
        val host = uri.host!!.lowercase(Locale.ROOT).trimEnd('.')
        if (host == "localhost" || host.endsWith(".localhost") || host.endsWith(".local")) return false
        if (host == "127.0.0.1" || host.startsWith("10.") || host.startsWith("192.168.")) return false
        if (host.startsWith("172.")) {
            val second = host.split('.').getOrNull(1)?.toIntOrNull() ?: -1
            if (second in 16..31) return false
        }
        return true
    }

    private fun countOccurrences(text: String, term: String): Int {
        var count = 0
        var offset = 0
        while (offset < text.length) {
            val found = text.indexOf(term, offset)
            if (found < 0) break
            count++
            offset = found + term.length
        }
        return count
    }

    private fun makeSnippet(body: String, lowerBody: String, terms: List<String>): String {
        val first = terms.map { lowerBody.indexOf(it) }.filter { it >= 0 }.minOrNull() ?: 0
        val start = (first - 110).coerceAtLeast(0)
        return body.substring(start, minOf(body.length, start + 420)).trim()
    }

    private class KnowledgeDatabase(context: Context) :
        SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

        override fun onCreate(db: SQLiteDatabase) {
            db.execSQL(
                "CREATE TABLE kowork_knowledge_docs (" +
                    "_id INTEGER PRIMARY KEY AUTOINCREMENT, " +
                    "source_id TEXT, source_title TEXT, title TEXT NOT NULL, url TEXT NOT NULL, " +
                    "license TEXT, license_url TEXT, attribution TEXT, body TEXT NOT NULL)"
            )
            db.execSQL(
                "CREATE VIRTUAL TABLE kowork_knowledge_fts USING fts4(" +
                    "doc_id UNINDEXED, title, body, tokenize=unicode61)"
            )
        }

        override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
            if (oldVersion < 1) onCreate(db)
        }
    }
}
