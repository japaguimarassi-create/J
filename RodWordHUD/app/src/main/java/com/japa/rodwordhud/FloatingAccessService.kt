package com.japa.rodwordhud

import android.accessibilityservice.AccessibilityService
import android.content.BroadcastReceiver
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.util.ArrayDeque

class FloatingAccessService : AccessibilityService() {
    companion object {
        const val ACTION_SHOW_HUD = "com.japa.rodwordhud.SHOW_HUD"
    }

    private var windowManager: WindowManager? = null
    private var hudView: View? = null
    private var receiverRegistered = false

    private val showReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            showHud()
        }
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        windowManager = getSystemService(WINDOW_SERVICE) as WindowManager
        val filter = IntentFilter(ACTION_SHOW_HUD)
        if (Build.VERSION.SDK_INT >= 33) {
            registerReceiver(showReceiver, filter, Context.RECEIVER_NOT_EXPORTED)
        } else {
            @Suppress("DEPRECATION")
            registerReceiver(showReceiver, filter)
        }
        receiverRegistered = true
        showHud()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
    }

    override fun onInterrupt() {
    }

    override fun onUnbind(intent: Intent?): Boolean {
        removeHud()
        if (receiverRegistered) {
            try {
                unregisterReceiver(showReceiver)
            } catch (_: Exception) {
            }
            receiverRegistered = false
        }
        return super.onUnbind(intent)
    }

    private fun showHud() {
        if (!Settings.canDrawOverlays(this) || hudView != null) return
        val wm = windowManager ?: return
        val density = resources.displayMetrics.density
        fun dp(value: Int) = (value * density).toInt()

        val shell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), dp(8), dp(10), dp(9))
            background = GradientDrawable().apply {
                setColor(Color.rgb(16, 24, 46))
                cornerRadius = dp(16).toFloat()
                setStroke(dp(1), Color.rgb(130, 148, 255))
            }
            elevation = dp(10).toFloat()
        }

        val header = TextView(this).apply {
            text = "RW  ·  HUD     arraste"
            textSize = 11f
            setTextColor(Color.rgb(188, 198, 255))
            typeface = Typeface.DEFAULT_BOLD
            gravity = Gravity.CENTER
            setPadding(dp(7), dp(3), dp(7), dp(7))
        }
        val insert = TextView(this).apply {
            text = "INSERIR PALPITE"
            textSize = 12f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.rgb(11, 16, 32))
            gravity = Gravity.CENTER
            setPadding(dp(13), dp(11), dp(13), dp(11))
            background = GradientDrawable().apply {
                setColor(Color.rgb(130, 148, 255))
                cornerRadius = dp(11).toFloat()
            }
            setOnClickListener { fillFocusedInput() }
        }
        val close = TextView(this).apply {
            text = "Ocultar HUD"
            textSize = 10f
            setTextColor(Color.rgb(169, 179, 205))
            gravity = Gravity.CENTER
            setPadding(dp(5), dp(7), dp(5), dp(1))
            setOnClickListener { removeHud() }
        }

        shell.addView(header)
        shell.addView(insert)
        shell.addView(close)

        val params = WindowManager.LayoutParams(
            dp(190),
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = dp(14)
            y = dp(170)
        }

        var startX = 0
        var startY = 0
        var touchX = 0f
        var touchY = 0f
        header.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    startX = params.x
                    startY = params.y
                    touchX = event.rawX
                    touchY = event.rawY
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    params.x = startX + (event.rawX - touchX).toInt()
                    params.y = startY + (event.rawY - touchY).toInt()
                    try {
                        wm.updateViewLayout(shell, params)
                    } catch (_: Exception) {
                    }
                    true
                }
                MotionEvent.ACTION_UP -> true
                else -> false
            }
        }

        try {
            wm.addView(shell, params)
            hudView = shell
        } catch (_: Exception) {
            hudView = null
        }
    }

    private fun fillFocusedInput() {
        val guess = getSharedPreferences("rodwordhud", MODE_PRIVATE)
            .getString("guess", "banana")?.trim().orEmpty()
        if (guess.isBlank()) {
            Toast.makeText(this, "Escolha um palpite primeiro.", Toast.LENGTH_SHORT).show()
            return
        }

        val root = rootInActiveWindow
        val target = root?.let { findEditable(it) }
        if (target != null) {
            val args = Bundle().apply {
                putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, guess)
            }
            if (target.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)) {
                Toast.makeText(this, "Palpite inserido. Revise antes de enviar.", Toast.LENGTH_SHORT).show()
                return
            }
        }

        val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        clipboard.setPrimaryClip(ClipData.newPlainText("Palpite", guess))
        Toast.makeText(this, "Campo não acessível; palpite copiado para colar manualmente.", Toast.LENGTH_LONG).show()
    }

    private fun findEditable(root: AccessibilityNodeInfo): AccessibilityNodeInfo? {
        val input = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        if (input != null && input.isEditable && input.isEnabled) return input

        val queue = ArrayDeque<AccessibilityNodeInfo>()
        queue.add(root)
        var inspected = 0
        while (queue.isNotEmpty() && inspected < 220) {
            val node = queue.removeFirst()
            inspected += 1
            if (node.isEditable && node.isEnabled && node.isFocused) return node
            for (index in 0 until node.childCount) {
                val child = node.getChild(index)
                if (child != null) queue.add(child)
            }
        }
        return null
    }

    private fun removeHud() {
        val view = hudView ?: return
        try {
            windowManager?.removeView(view)
        } catch (_: Exception) {
        }
        hudView = null
    }
}
