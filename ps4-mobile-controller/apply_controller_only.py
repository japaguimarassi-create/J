#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

def edit(path, old, new):
    target = root / path
    source = target.read_text(encoding="utf-8")
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"Expected exactly one match in {path}, found {count}")
    target.write_text(source.replace(old, new, 1), encoding="utf-8")

jni = "android/app/src/main/cpp/chiaki-jni.c"
edit(
    jni,
    "#include <chiaki/session.h>\n",
    "#include <chiaki/session.h>\n#include <chiaki/takion.h>\n"
)
edit(
    jni,
    "connect_info.video_profile_auto_downgrade = true;\n",
    "connect_info.video_profile_auto_downgrade = true;\n\tconnect_info.audio_video_disabled = CHIAKI_AUDIO_VIDEO_DISABLED;\n"
)

analog = r'''// SPDX-License-Identifier: LicenseRef-AGPL-3.0-only-OpenSSL

package com.metallic.chiaki.touchcontrols

import android.content.Context
import android.graphics.Canvas
import android.graphics.drawable.Drawable
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import com.metallic.chiaki.R
import kotlin.math.abs

class AnalogStickView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {
    val radius: Float
    private val handleRadius: Float
    private val drawableBase: Drawable?
    private val drawableHandle: Drawable?

    var state = Vector(0f, 0f)
        private set(value) {
            field = value
            stateChangedCallback?.invoke(field)
        }

    var stateChangedCallback: ((Vector) -> Unit)? = null
    var buttonPressedCallback: ((Boolean) -> Unit)? = null

    private var handlePosition = Vector(0f, 0f)
    private var activePointerId = MotionEvent.INVALID_POINTER_ID
    private var centerPressed = false

    private val centerClickRadius: Float
    private val centerMoveThreshold: Float

    init {
        context.theme.obtainStyledAttributes(attrs, R.styleable.AnalogStickView, 0, 0).apply {
            radius = getDimension(R.styleable.AnalogStickView_radius, 0f)
            handleRadius = getDimension(R.styleable.AnalogStickView_handleRadius, 0f)
            drawableBase = getDrawable(R.styleable.AnalogStickView_drawableBase)
            drawableHandle = getDrawable(R.styleable.AnalogStickView_drawableHandle)
            recycle()
        }
        centerClickRadius = handleRadius * 0.68f
        centerMoveThreshold = maxOf(handleRadius * 0.9f, ViewConfiguration.get(context).scaledTouchSlop * 1.5f)
        isClickable = true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val centerX = width * 0.5f
        val centerY = height * 0.5f
        val outerRadius = radius + handleRadius
        drawableBase?.setBounds(
            (centerX - outerRadius).toInt(),
            (centerY - outerRadius).toInt(),
            (centerX + outerRadius).toInt(),
            (centerY + outerRadius).toInt()
        )
        drawableBase?.draw(canvas)

        val handleX = centerX + handlePosition.x * radius
        val handleY = centerY + handlePosition.y * radius
        drawableHandle?.setBounds(
            (handleX - handleRadius).toInt(),
            (handleY - handleRadius).toInt(),
            (handleX + handleRadius).toInt(),
            (handleY + handleRadius).toInt()
        )
        drawableHandle?.draw(canvas)
    }

    private fun updateState(position: Vector?) {
        if (position == null || radius <= 0f) {
            state = Vector(0f, 0f)
            handlePosition = Vector(0f, 0f)
            invalidate()
            return
        }

        val center = Vector(width * 0.5f, height * 0.5f)
        val direction = position - center
        val length = direction.length
        if (length <= 0.001f) {
            state = Vector(0f, 0f)
            handlePosition = Vector(0f, 0f)
            invalidate()
            return
        }

        val strength = (length / radius).coerceAtMost(1f)
        val normalized = direction / length
        handlePosition = normalized * strength
        val dominantAxis = maxOf(abs(normalized.x), abs(normalized.y))
        state = Vector(normalized.x / dominantAxis, normalized.y / dominantAxis) * strength
        invalidate()
    }

    private fun beginPointer(event: MotionEvent, index: Int) {
        activePointerId = event.getPointerId(index)
        val position = Vector(event.getX(index), event.getY(index))
        val center = Vector(width * 0.5f, height * 0.5f)
        centerPressed = (position - center).length <= centerClickRadius
        if (centerPressed) {
            buttonPressedCallback?.invoke(true)
            updateState(null)
        } else {
            updateState(position)
        }
        parent?.requestDisallowInterceptTouchEvent(true)
    }

    private fun finishPointer() {
        if (centerPressed) {
            centerPressed = false
            buttonPressedCallback?.invoke(false)
        }
        activePointerId = MotionEvent.INVALID_POINTER_ID
        updateState(null)
        parent?.requestDisallowInterceptTouchEvent(false)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                if (activePointerId == MotionEvent.INVALID_POINTER_ID) {
                    beginPointer(event, event.actionIndex)
                }
            }
            MotionEvent.ACTION_POINTER_DOWN -> Unit
            MotionEvent.ACTION_MOVE -> {
                if (activePointerId != MotionEvent.INVALID_POINTER_ID) {
                    val index = event.findPointerIndex(activePointerId)
                    if (index >= 0) {
                        val position = Vector(event.getX(index), event.getY(index))
                        if (centerPressed) {
                            val center = Vector(width * 0.5f, height * 0.5f)
                            if ((position - center).length > centerMoveThreshold) {
                                centerPressed = false
                                buttonPressedCallback?.invoke(false)
                                updateState(position)
                            }
                        } else {
                            updateState(position)
                        }
                    }
                }
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP -> {
                if (event.getPointerId(event.actionIndex) == activePointerId) {
                    finishPointer()
                }
            }
            MotionEvent.ACTION_CANCEL -> finishPointer()
        }
        return true
    }
}
'''
(root / "android/app/src/main/java/com/metallic/chiaki/touchcontrols/AnalogStickView.kt").write_text(analog, encoding="utf-8")

controls = r'''<?xml version="1.0" encoding="utf-8"?>
<androidx.constraintlayout.widget.ConstraintLayout
    xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:app="http://schemas.android.com/apk/res-auto"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#0A0F18"
    android:clipChildren="false">

    <androidx.constraintlayout.widget.Guideline
        android:id="@+id/centerGuideline"
        android:layout_width="wrap_content"
        android:layout_height="wrap_content"
        android:orientation="vertical"
        app:layout_constraintGuide_percent="0.5" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/r2ButtonView"
        android:layout_width="88dp"
        android:layout_height="62dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_r2"
        app:drawablePressed="@drawable/control_button_r2_pressed"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/r1ButtonView"
        android:layout_width="76dp"
        android:layout_height="56dp"
        android:layout_marginStart="34dp"
        android:layout_marginTop="34dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_r1"
        app:drawablePressed="@drawable/control_button_r1_pressed"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/l2ButtonView"
        android:layout_width="88dp"
        android:layout_height="62dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_l2"
        app:drawablePressed="@drawable/control_button_l2_pressed"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/l1ButtonView"
        android:layout_width="76dp"
        android:layout_height="56dp"
        android:layout_marginEnd="34dp"
        android:layout_marginTop="34dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_l1"
        app:drawablePressed="@drawable/control_button_l1_pressed"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toTopOf="parent" />

    <com.metallic.chiaki.touchcontrols.DPadView
        android:id="@+id/dpadView"
        android:layout_width="142dp"
        android:layout_height="142dp"
        android:padding="12dp"
        app:layout_constraintBottom_toTopOf="@id/leftAnalogStickView"
        app:layout_constraintStart_toStartOf="parent"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintVertical_bias="0.58" />

    <com.metallic.chiaki.touchcontrols.TouchpadView
        android:id="@+id/touchpadView"
        android:layout_width="236dp"
        android:layout_height="94dp"
        android:layout_marginTop="12dp"
        app:drawableIdle="@drawable/control_touchpad"
        app:drawablePressed="@drawable/control_touchpad_pressed"
        app:layout_constraintEnd_toStartOf="@id/faceButtonsLayout"
        app:layout_constraintStart_toEndOf="@id/dpadView"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintHorizontal_bias="0.5" />

    <androidx.constraintlayout.widget.ConstraintLayout
        android:id="@+id/faceButtonsLayout"
        android:layout_width="@dimen/control_face_button_size_full"
        android:layout_height="@dimen/control_face_button_size_full"
        android:layout_marginEnd="10dp"
        app:layout_constraintBottom_toTopOf="@id/rightAnalogStickView"
        app:layout_constraintEnd_toEndOf="parent"
        app:layout_constraintTop_toTopOf="parent"
        app:layout_constraintVertical_bias="0.58">

        <com.metallic.chiaki.touchcontrols.ButtonView
            android:id="@+id/crossButtonView"
            android:layout_width="@dimen/control_face_button_size_full"
            android:layout_height="@dimen/control_face_button_size_half"
            android:paddingStart="@dimen/control_face_button_padding_to_full"
            android:paddingEnd="@dimen/control_face_button_padding_to_full"
            android:paddingTop="@dimen/control_face_button_padding_to_center"
            android:paddingBottom="@dimen/control_face_button_padding_to_outside"
            app:drawableIdle="@drawable/control_button_cross"
            app:drawablePressed="@drawable/control_button_cross_pressed"
            app:layout_constraintBottom_toBottomOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintStart_toStartOf="parent" />

        <com.metallic.chiaki.touchcontrols.ButtonView
            android:id="@+id/moonButtonView"
            android:layout_width="@dimen/control_face_button_size_half"
            android:layout_height="@dimen/control_face_button_size_full"
            android:paddingTop="@dimen/control_face_button_padding_to_full"
            android:paddingBottom="@dimen/control_face_button_padding_to_full"
            android:paddingStart="@dimen/control_face_button_padding_to_center"
            android:paddingEnd="@dimen/control_face_button_padding_to_outside"
            app:drawableIdle="@drawable/control_button_moon"
            app:drawablePressed="@drawable/control_button_moon_pressed"
            app:layout_constraintBottom_toBottomOf="parent"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintTop_toTopOf="parent" />

        <com.metallic.chiaki.touchcontrols.ButtonView
            android:id="@+id/pyramidButtonView"
            android:layout_width="@dimen/control_face_button_size_full"
            android:layout_height="@dimen/control_face_button_size_half"
            android:paddingStart="@dimen/control_face_button_padding_to_full"
            android:paddingEnd="@dimen/control_face_button_padding_to_full"
            android:paddingBottom="@dimen/control_face_button_padding_to_center"
            android:paddingTop="@dimen/control_face_button_padding_to_outside"
            app:drawableIdle="@drawable/control_button_pyramid"
            app:drawablePressed="@drawable/control_button_pyramid_pressed"
            app:layout_constraintEnd_toEndOf="parent"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintTop_toTopOf="parent" />

        <com.metallic.chiaki.touchcontrols.ButtonView
            android:id="@+id/boxButtonView"
            android:layout_width="@dimen/control_face_button_size_half"
            android:layout_height="@dimen/control_face_button_size_full"
            android:paddingTop="@dimen/control_face_button_padding_to_full"
            android:paddingBottom="@dimen/control_face_button_padding_to_full"
            android:paddingEnd="@dimen/control_face_button_padding_to_center"
            android:paddingStart="@dimen/control_face_button_padding_to_outside"
            app:drawableIdle="@drawable/control_button_box"
            app:drawablePressed="@drawable/control_button_box_pressed"
            app:layout_constraintBottom_toBottomOf="parent"
            app:layout_constraintStart_toStartOf="parent"
            app:layout_constraintTop_toTopOf="parent" />
    </androidx.constraintlayout.widget.ConstraintLayout>

    <com.metallic.chiaki.touchcontrols.AnalogStickView
        android:id="@+id/leftAnalogStickView"
        android:layout_width="140dp"
        android:layout_height="140dp"
        app:radius="@dimen/control_analog_stick_radius"
        app:handleRadius="@dimen/control_analog_stick_handle_radius"
        app:drawableBase="@drawable/control_analog_stick_base"
        app:drawableHandle="@drawable/control_analog_stick_handle"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toStartOf="parent" />

    <com.metallic.chiaki.touchcontrols.AnalogStickView
        android:id="@+id/rightAnalogStickView"
        android:layout_width="140dp"
        android:layout_height="140dp"
        app:radius="@dimen/control_analog_stick_radius"
        app:handleRadius="@dimen/control_analog_stick_handle_radius"
        app:drawableBase="@drawable/control_analog_stick_base"
        app:drawableHandle="@drawable/control_analog_stick_handle"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toEndOf="parent" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/shareButtonView"
        android:layout_width="44dp"
        android:layout_height="44dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_share"
        app:drawablePressed="@drawable/control_button_share_pressed"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toStartOf="@id/psButtonView"
        app:layout_constraintTop_toTopOf="@id/psButtonView" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/psButtonView"
        android:layout_width="54dp"
        android:layout_height="54dp"
        android:padding="9dp"
        app:drawableIdle="@drawable/control_button_home"
        app:drawablePressed="@drawable/control_button_home_pressed"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintEnd_toStartOf="@id/optionsButtonView"
        app:layout_constraintStart_toEndOf="@id/shareButtonView" />

    <com.metallic.chiaki.touchcontrols.ButtonView
        android:id="@+id/optionsButtonView"
        android:layout_width="44dp"
        android:layout_height="44dp"
        android:padding="7dp"
        app:drawableIdle="@drawable/control_button_options"
        app:drawablePressed="@drawable/control_button_options_pressed"
        app:layout_constraintBottom_toBottomOf="parent"
        app:layout_constraintStart_toEndOf="@id/psButtonView"
        app:layout_constraintTop_toTopOf="@id/psButtonView" />

</androidx.constraintlayout.widget.ConstraintLayout>
'''
(root / "android/app/src/main/res/layout/fragment_controls.xml").write_text(controls, encoding="utf-8")

touch_file = "android/app/src/main/java/com/metallic/chiaki/touchcontrols/TouchControlsFragment.kt"
edit(
    touch_file,
    "\t\tbinding.l3ButtonView.buttonPressedCallback = buttonStateChanged(ControllerState.BUTTON_L3)\n\t\tbinding.r3ButtonView.buttonPressedCallback = buttonStateChanged(ControllerState.BUTTON_R3)\n",
    "\t\tbinding.leftAnalogStickView.buttonPressedCallback = buttonStateChanged(ControllerState.BUTTON_L3)\n\t\tbinding.rightAnalogStickView.buttonPressedCallback = buttonStateChanged(ControllerState.BUTTON_R3)\n"
)

stream_layout = "android/app/src/main/res/layout/activity_stream.xml"
edit(
    stream_layout,
    "        android:layout_gravity=\"center\">\n",
    "        android:layout_gravity=\"center\"\n        android:visibility=\"gone\">\n"
)

manifest = "android/app/src/main/AndroidManifest.xml"
edit(
    manifest,
    '            android:configChanges="keyboard|keyboardHidden|orientation|screenSize" />\n\n        <activity\n            android:name=".settings.SettingsActivity"',
    '            android:configChanges="keyboard|keyboardHidden|orientation|screenSize"\n            android:screenOrientation="landscape" />\n\n        <activity\n            android:name=".settings.SettingsActivity"'
)

strings = "android/app/src/main/res/values/strings.xml"
edit(strings, '<string name="app_name">Chiaki</string>', '<string name="app_name">PS4 Mobile Controller</string>')

dimens = "android/app/src/main/res/values/dimens.xml"
edit(dimens, '<dimen name="control_analog_stick_radius">48dp</dimen>', '<dimen name="control_analog_stick_radius">42dp</dimen>')
edit(dimens, '<dimen name="control_analog_stick_handle_radius">32dp</dimen>', '<dimen name="control_analog_stick_handle_radius">25dp</dimen>')

print("Controller-only patch applied successfully.")
