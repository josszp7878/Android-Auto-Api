package cn.vove7.andro_accessibility_api.demo.view

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.View
import cn.vove7.andro_accessibility_api.demo.R

class CursorView @JvmOverloads constructor(
    context: Context, attrs: AttributeSet? = null, defStyleAttr: Int = 0
) : View(context, attrs, defStyleAttr) {

    private val cursorBitmap: Bitmap = BitmapFactory.decodeResource(resources, R.drawable.cursor_arrow)

    init {
        alpha = 0.5f
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        // 使用实际的位图尺寸
        setMeasuredDimension(cursorBitmap.width, cursorBitmap.height)
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        // 绘制光标图片
        canvas.drawBitmap(cursorBitmap, 0f, 0f, null)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // 返回 false 以确保不拦截事件
        return false
    }

    fun flash() {
        // 实现闪烁效果
        animate().alpha(0f).setDuration(100).withEndAction {
            animate().alpha(0.5f).setDuration(100).start() // 恢复到 50% 透明度
        }.start()
    }

    fun getCursorSize(): Pair<Int, Int> {
        return Pair(cursorBitmap.width, cursorBitmap.height)
    }
} 