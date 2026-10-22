package com.japa.rodwordhud

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.inputmethod.EditorInfo
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.util.Locale

class MainActivity : Activity() {
    private lateinit var videoInput: EditText
    private lateinit var contextInput: EditText
    private lateinit var guessList: LinearLayout
    private lateinit var statusLabel: TextView
    private lateinit var model: MiniGuessModel
    private var selectedGuess = "banana"
    @Volatile private var modelReady = false

    private val backgroundColor = Color.rgb(11, 16, 32)
    private val panelColor = Color.rgb(20, 28, 50)
    private val accentColor = Color.rgb(130, 148, 255)
    private val mutedColor = Color.rgb(169, 179, 205)
    private val prefs by lazy { getSharedPreferences("rodwordhud", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor = backgroundColor
        window.navigationBarColor = backgroundColor
        model = MiniGuessModel()
        selectedGuess = prefs.getString("guess", "banana") ?: "banana"
        buildUi()
        Thread({
            try {
                model.trainModel()
                runOnUiThread {
                    if (!isFinishing) {
                        modelReady = true
                        generateGuesses()
                    }
                }
            } catch (_: Throwable) {
                runOnUiThread {
                    if (!isFinishing) statusLabel.text = "A mini-IA não conseguiu concluir o treinamento."
                }
            }
        }, "rodword-model-training").start()
    }

    override fun onResume() {
        super.onResume()
        if (Settings.canDrawOverlays(this)) {
            sendBroadcast(Intent(FloatingAccessService.ACTION_SHOW_HUD).setPackage(packageName))
        }
    }

    private fun buildUi() {
        val page = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(26), dp(20), dp(28))
            setBackgroundColor(backgroundColor)
        }

        page.addView(label("ROD PRIMATA  /  WORD HUNTER", 12, accentColor, true))
        page.addView(space(10))
        page.addView(label("Caçador de\npalavras.", 31, Color.WHITE, true))
        page.addView(space(8))
        page.addView(label("Palpites locais, HUD flutuante e preenchimento manual do comentário.", 15, mutedColor, false))
        page.addView(space(24))

        page.addView(sectionTitle("1 · VÍDEO"))
        videoInput = editField("Cole o link exato do vídeo do Rod Primata")
        page.addView(videoInput)
        page.addView(space(10))
        page.addView(actionButton("ABRIR NO YOUTUBE", accentColor, Color.rgb(11, 16, 32)) {
            val raw = videoInput.text.toString().trim()
            val url = if (raw.startsWith("http://") || raw.startsWith("https://")) raw
                else "https://www.youtube.com/@rodprimata/videos"
            openExternal(url)
        })
        page.addView(space(8))
        page.addView(actionButton("PESQUISAR O CONTEXTO NA WEB", panelColor, Color.WHITE) {
            val hints = contextInput.text.toString().trim()
            val query = if (hints.isBlank()) "Rod Primata palavra secreta vídeo recente"
                else "Rod Primata palavra secreta " + hints
            val encoded = URLEncoder.encode(query, StandardCharsets.UTF_8.name())
            openExternal("https://www.google.com/search?q=" + encoded)
        })

        page.addView(space(24))
        page.addView(sectionTitle("2 · PISTAS PARA A MINI-IA"))
        page.addView(label("Cole título, transcrição curta ou pistas visíveis. A busca atual não identificou com segurança o vídeo específico publicado hoje, então a IA não recebe contexto inventado.", 13, mutedColor, false))
        page.addView(space(10))
        contextInput = editField("Ex.: objetos mostrados, dicas, frases do vídeo…", true)
        contextInput.imeOptions = EditorInfo.IME_ACTION_DONE
        page.addView(contextInput)
        page.addView(space(10))
        page.addView(actionButton("GERAR 5 PALPITES", accentColor, Color.rgb(11, 16, 32)) {
            generateGuesses()
        })
        page.addView(space(7))
        page.addView(label("Modelo local: " + model.parameterCount() + " pesos treináveis · 100 palavras candidatas. A pontuação é relativa, não uma probabilidade real de acerto.", 12, mutedColor, false))
        page.addView(space(12))
        guessList = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        page.addView(guessList)

        page.addView(space(18))
        page.addView(sectionTitle("3 · HUD FLUTUANTE"))
        statusLabel = label("Palpite escolhido: " + selectedGuess, 14, Color.WHITE, true)
        page.addView(statusLabel)
        page.addView(space(10))
        page.addView(actionButton("ATIVAR / CONFIGURAR HUD", panelColor, Color.WHITE) {
            configureHud()
        })
        page.addView(space(10))
        page.addView(label("Como usar: abra o vídeo no YouTube, toque no campo de comentário e toque em “INSERIR PALPITE” no HUD. O app apenas preenche o campo focado; você revisa e envia manualmente. Não há envio automático nem repetição a cada 10 segundos.", 13, mutedColor, false))
        page.addView(space(20))
        page.addView(label("Privacidade: a mini-IA roda no aparelho. O app não solicita sua senha do Google nem lê o conteúdo da conta; o YouTube mantém sua própria sessão.", 12, mutedColor, false))

        val scroll = ScrollView(this).apply {
            isFillViewport = true
            clipToPadding = false
            addView(page, ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ))
        }
        setContentView(scroll)
        guessList.addView(label("Preparando a mini-IA em segundo plano…", 14, mutedColor, false))
    }

    private fun generateGuesses() {
        if (!modelReady) {
            statusLabel.text = "A mini-IA ainda está treinando. Tente novamente em instantes."
            return
        }
        val context = contextInput.text.toString().trim()
        val link = videoInput.text.toString().trim()
        val usableContext = buildString {
            append("Rod Primata palavra secreta desafio ")
            if (link.isNotBlank()) append(' ').append(link)
            if (context.isNotBlank()) append(' ').append(context)
        }
        renderGuesses(model.predict(usableContext, 5))
    }

    private fun renderGuesses(guesses: List<Guess>) {
        guessList.removeAllViews()
        guesses.forEachIndexed { index, guess ->
            val selected = guess.word == selectedGuess
            val row = TextView(this).apply {
                text = String.format(Locale("pt", "BR"), "%02d   %s     %.1f%%", index + 1, guess.word, guess.score * 100f)
                textSize = 16f
                typeface = if (selected) Typeface.DEFAULT_BOLD else Typeface.DEFAULT
                setTextColor(if (selected) Color.WHITE else mutedColor)
                setPadding(dp(14), dp(14), dp(14), dp(14))
                background = rounded(if (selected) Color.rgb(43, 57, 103) else panelColor, 14)
                isClickable = true
                isFocusable = true
                setOnClickListener {
                    selectedGuess = guess.word
                    prefs.edit().putString("guess", selectedGuess).apply()
                    statusLabel.text = "Palpite escolhido: " + selectedGuess
                    renderGuesses(guesses)
                }
            }
            val params = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            )
            params.bottomMargin = dp(7)
            guessList.addView(row, params)
        }
        prefs.edit().putString("guess", selectedGuess).apply()
    }

    private fun configureHud() {
        prefs.edit().putString("guess", selectedGuess).apply()
        if (!Settings.canDrawOverlays(this)) {
            val intent = Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:" + packageName))
            startActivityForResult(intent, 3101)
        } else {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
    }

    @Deprecated("Deprecated in Android API; kept for compatibility with API 26+")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 3101 && Settings.canDrawOverlays(this)) {
            startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
        }
    }

    private fun openExternal(url: String) {
        try {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
        } catch (_: Exception) {
            statusLabelOrToast("Não foi possível abrir o link.")
        }
    }

    private fun statusLabelOrToast(message: String) {
        android.widget.Toast.makeText(this, message, android.widget.Toast.LENGTH_SHORT).show()
    }

    private fun sectionTitle(text: String) = label(text, 12, accentColor, true).apply {
        letterSpacing = 0.08f
    }

    private fun label(text: String, size: Int, color: Int, bold: Boolean): TextView =
        TextView(this).apply {
            this.text = text
            textSize = size.toFloat()
            setTextColor(color)
            if (bold) setTypeface(typeface, Typeface.BOLD)
            setLineSpacing(dp(3).toFloat(), 1f)
        }

    private fun editField(hintText: String, multiline: Boolean = false): EditText =
        EditText(this).apply {
            hint = hintText
            textSize = 15f
            setTextColor(Color.WHITE)
            setHintTextColor(Color.rgb(117, 130, 160))
            setPadding(dp(14), dp(13), dp(14), dp(13))
            background = rounded(panelColor, 14)
            minHeight = dp(if (multiline) 120 else 52)
            if (multiline) {
                gravity = Gravity.TOP or Gravity.START
                setSingleLine(false)
                inputType = android.text.InputType.TYPE_CLASS_TEXT or
                    android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or
                    android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            } else {
                setSingleLine(true)
                inputType = android.text.InputType.TYPE_CLASS_TEXT or
                    android.text.InputType.TYPE_TEXT_VARIATION_URI
            }
        }

    private fun actionButton(text: String, color: Int, textColor: Int, action: () -> Unit): Button =
        Button(this).apply {
            this.text = text
            textSize = 13f
            letterSpacing = 0.04f
            setTextColor(textColor)
            isAllCaps = false
            background = rounded(color, 14)
            minHeight = dp(52)
            setPadding(dp(12), dp(8), dp(12), dp(8))
            setOnClickListener { action() }
            stateListAnimator = null
        }

    private fun rounded(color: Int, radius: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(radius).toFloat()
    }

    private fun space(height: Int) = View(this).apply {
        layoutParams = LinearLayout.LayoutParams(1, dp(height))
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
