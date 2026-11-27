package com.japa.ps4controller

import android.app.Activity
import android.os.Bundle
import android.view.View
import android.view.Window
import android.view.WindowManager
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Color
import android.graphics.RectF
import android.view.MotionEvent
import kotlin.math.min
import kotlin.math.max
import kotlin.math.sqrt

class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestWindowFeature(Window.FEATURE_NO_TITLE)
        window.setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN)
        window.decorView.systemUiVisibility = (View.SYSTEM_UI_FLAG_FULLSCREEN or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY or View.SYSTEM_UI_FLAG_LAYOUT_STABLE or View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION or View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN)
        setContentView(ControllerView())
    }
}

private class ControllerView : View(thisContextHack()) {
    companion object {
        private lateinit var appContext: android.content.Context
        fun thisContextHack(): android.content.Context = appContext
    }
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val active = mutableSetOf<String>()
    private val pointers = mutableMapOf<Int, String>()
    private var w = 1f
    private var h = 1f
    private var scale = 1f
    private var cx = 0f
    private var cy = 0f
    private var leftX = 0f
    private var leftY = 0f
    private var rightX = 0f
    private var rightY = 0f
    private var leftTouch = false
    private var rightTouch = false

    init {
        isFocusable = true
    }

    constructor(context: android.content.Context, marker: Unit = Unit) : this() {
        appContext = context
    }

    override fun onDraw(c: Canvas) {
        super.onDraw(c)
        w = width.toFloat()
        h = height.toFloat()
        scale = min(w / 900f, h / 420f)
        cx = w / 2f
        cy = h / 2f
        c.drawColor(Color.rgb(10, 14, 22))
        drawText(c, "PS4 MOBILE CONTROLLER", cx, 24f * scale, 11f * scale, Color.rgb(130, 155, 190))
        drawTrigger(c, "R2", 38f * scale, 48f * scale, 130f * scale, 38f * scale)
        drawTrigger(c, "L2", w - 168f * scale, 48f * scale, 130f * scale, 38f * scale)
        drawButton(c, "R1", 188f * scale, 48f * scale, 52f * scale, 34f * scale, "R1")
        drawButton(c, "L1", w - 240f * scale, 48f * scale, 52f * scale, 34f * scale, "L1")

        drawDpad(c, 125f * scale, h * .43f)
        drawStick(c, 135f * scale, h * .79f, "L3", leftTouch, leftX, leftY)
        drawTouchpad(c, cx, h * .43f, 190f * scale, 82f * scale)
        drawButton(c, "SHARE", cx - 115f * scale, h * .72f, 76f * scale, 34f * scale, "SHARE")
        drawButton(c, "OPTIONS", cx + 39f * scale, h * .72f, 76f * scale, 34f * scale, "OPTIONS")
        drawButton(c, "PS", cx - 25f * scale, h * .86f, 50f * scale, 38f * scale, "PS")
        drawStick(c, w - 135f * scale, h * .79f, "R3", rightTouch, rightX, rightY)
        drawFace(c, w - 125f * scale, h * .43f)
        drawText(c, "L3 / PRESS", 135f * scale, h * .96f, 9f * scale, Color.GRAY)
        drawText(c, "R3 / PRESS", w - 135f * scale, h * .96f, 9f * scale, Color.GRAY)
        drawText(c, "CONTROLE VISUAL • CONEXÃO PS4 AINDA NÃO INTEGRADA", cx, h - 8f * scale, 8f * scale, Color.rgb(190, 145, 95))
    }

    private fun drawText(c: Canvas, s: String, x: Float, y: Float, size: Float, color: Int) {
        p.color = color; p.textSize = size; p.textAlign = Paint.Align.CENTER; p.style = Paint.Style.FILL
        c.drawText(s, x, y, p)
    }

    private fun rounded(c: Canvas, x: Float, y: Float, bw: Float, bh: Float, label: String, key: String, color: Int = Color.rgb(35, 47, 66)) {
        p.color = if (active.contains(key)) Color.rgb(65, 115, 185) else color
        p.style = Paint.Style.FILL
        c.drawRoundRect(RectF(x, y, x + bw, y + bh), 12f * scale, 12f * scale, p)
        p.color = Color.rgb(230, 238, 250); p.textSize = 13f * scale; p.textAlign = Paint.Align.CENTER
        c.drawText(label, x + bw / 2, y + bh / 2 + 5f * scale, p)
    }

    private fun drawButton(c: Canvas, label: String, x: Float, y: Float, bw: Float, bh: Float, key: String) = rounded(c, x, y, bw, bh, label, key)
    private fun drawTrigger(c: Canvas, label: String, x: Float, y: Float, bw: Float, bh: Float) = rounded(c, x, y, bw, bh, label, label, Color.rgb(27, 39, 57))

    private fun drawDpad(c: Canvas, x: Float, y: Float) {
        val s = 39f * scale
        rounded(c, x - s/2, y - s*1.45f, s, s, "↑", "UP")
        rounded(c, x - s*1.45f, y - s/2, s, s, "←", "LEFT")
        rounded(c, x + s*.45f, y - s/2, s, s, "→", "RIGHT")
        rounded(c, x - s/2, y + s*.45f, s, s, "↓", "DOWN")
    }

    private fun drawFace(c: Canvas, x: Float, y: Float) {
        val r = 23f * scale
        val points = listOf(Triple("△","TRIANGLE",0f,-1.35f), Triple("○","CIRCLE",1.35f,0f), Triple("×","CROSS",0f,1.35f), Triple("□","SQUARE",-1.35f,0f))
        for ((label,key,dx,dy) in points) {
            p.color = if (active.contains(key)) Color.rgb(70, 115, 185) else Color.rgb(36, 49, 69)
            c.drawCircle(x + dx*r, y + dy*r, r*.72f, p)
            p.color = Color.WHITE; p.textAlign = Paint.Align.CENTER; p.textSize = 22f * scale
            c.drawText(label, x + dx*r, y + dy*r + 7f*scale, p)
        }
    }

    private fun drawStick(c: Canvas, x: Float, y: Float, key: String, pressed: Boolean, dx: Float, dy: Float) {
        val r = 48f * scale
        p.color = Color.rgb(28, 39, 56); c.drawCircle(x, y, r, p)
        p.color = Color.rgb(75, 91, 113); p.style = Paint.Style.STROKE; p.strokeWidth = 2f*scale; c.drawCircle(x, y, r*.76f, p); p.style = Paint.Style.FILL
        p.color = if (pressed) Color.rgb(72, 122, 190) else Color.rgb(51, 66, 88)
        c.drawCircle(x + dx, y + dy, r*.46f, p)
        drawText(c, key, x, y + 4f*scale, 12f*scale, Color.WHITE)
    }

    private fun drawTouchpad(c: Canvas, x: Float, y: Float, bw: Float, bh: Float) {
        p.color = if (active.contains("TOUCHPAD")) Color.rgb(58, 91, 137) else Color.rgb(27, 38, 55)
        c.drawRoundRect(RectF(x-bw/2, y-bh/2, x+bw/2, y+bh/2), 14f*scale, 14f*scale, p)
        p.color = Color.rgb(174, 190, 210); p.style = Paint.Style.STROKE; p.strokeWidth = 2f*scale
        c.drawRoundRect(RectF(x-bw/2, y-bh/2, x+bw/2, y+bh/2), 14f*scale, 14f*scale, p); p.style = Paint.Style.FILL
        drawText(c, "TOUCHPAD", x, y+5f*scale, 12f*scale, Color.WHITE)
    }

    private fun hit(x: Float, y: Float): String {
        fun near(px: Float, py: Float, rx: Float, ry: Float) = kotlin.math.abs(px-rx) < 30f*scale && kotlin.math.abs(py-ry) < 30f*scale
        if (y < 100f*scale && x < w*.3f) return if (x < w*.22f) "R2" else "R1"
        if (y < 100f*scale && x > w*.7f) return if (x > w*.78f) "L2" else "L1"
        val lx = 125f*scale; val ly = h*.43f; val s=39f*scale
        if (near(x,y,lx,ly-s*1.45f)) return "UP"
        if (near(x,y,lx-s*1.45f,ly)) return "LEFT"
        if (near(x,y,lx+s*1.45f,ly)) return "RIGHT"
        if (near(x,y,lx,ly+s*1.45f)) return "DOWN"
        if (x < 220f*scale && y > h*.62f) return "L3"
        if (x > w-220f*scale && y > h*.62f) return "R3"
        if (x > w-205f*scale && y < h*.62f) {
            val fx=w-125f*scale; val fy=h*.43f; val r=31f*scale
            if (near(x,y,fx,fy-r*1.35f)) return "TRIANGLE"
            if (near(x,y,fx+r*1.35f,fy)) return "CIRCLE"
            if (near(x,y,fx,fy+r*1.35f)) return "CROSS"
            if (near(x,y,fx-r*1.35f,fy)) return "SQUARE"
        }
        if (x in (cx-100f*scale)..(cx+100f*scale) && y in (h*.30f)..(h*.56f)) return "TOUCHPAD"
        if (x in (cx-35f*scale)..(cx+35f*scale) && y > h*.79f) return "PS"
        if (x in (cx-145f*scale)..(cx-40f*scale) && y > h*.62f) return "SHARE"
        if (x in (cx+40f*scale)..(cx+145f*scale) && y > h*.62f) return "OPTIONS"
        return "NONE"
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val i=e.actionIndex; val id=e.getPointerId(i); val x=e.getX(i); val y=e.getY(i)
                val key=hit(x,y); pointers[id]=key
                if (key!="NONE") active.add(key)
                if (key=="L3") leftTouch=true
                if (key=="R3") rightTouch=true
                invalidate()
            }
            MotionEvent.ACTION_MOVE -> {
                for (i in 0 until e.pointerCount) {
                    val id=e.getPointerId(i); val old=pointers[id] ?: continue
                    if (old=="L3" || old=="R3") {
                        val bx=if(old=="L3") 135f*scale else w-135f*scale
                        val by=h*.79f
                        val dx=e.getX(i)-bx; val dy=e.getY(i)-by
                        val limit=48f*scale; val d=sqrt(dx*dx+dy*dy).coerceAtLeast(1f)
                        if(old=="L3"){ leftX=dx*min(1f,limit/d); leftY=dy*min(1f,limit/d) }
                        else { rightX=dx*min(1f,limit/d); rightY=dy*min(1f,limit/d) }
                    }
                }
                invalidate()
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP, MotionEvent.ACTION_CANCEL -> {
                val i=if(e.actionMasked==MotionEvent.ACTION_CANCEL) 0 else e.actionIndex
                val id=e.getPointerId(i); val key=pointers.remove(id)
                if(key!=null){ active.remove(key); if(key=="L3"){leftTouch=false;leftX=0f;leftY=0f}; if(key=="R3"){rightTouch=false;rightX=0f;rightY=0f} }
                invalidate()
            }
        }
        return true
    }
}
