//package cn.vove7.andro_accessibility_api.demo.utils
//
//import android.app.Activity
//import android.app.ActivityManager
//import android.content.Context
//import android.content.Intent
//import android.net.Uri
//import android.os.Build
//import android.provider.Settings
//import android.text.TextUtils
//import android.util.Log
//import android.widget.Toast
//import java.util.*
//
///**
// * @功能: 工具类
// * @User Lmy
// * @Creat 4/16/21 8:33 AM
// * @Compony 永远相信美好的事情即将发生
// */
//object Utils {
//    const val REQUEST_FLOAT_CODE=1001
//    /**
//     * 跳转到设置页面申请打开无障碍辅助功能
//     */
//   private fun accessibilityToSettingPage(context: Context) {
//        //开启辅助功能页面
//        try {
//            val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
//            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
//            context.startActivity(intent)
//        } catch (e: Exception) {
//            val intent = Intent(Settings.ACTION_SETTINGS)
//            intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
//            context.startActivity(intent)
//            e.printStackTrace()
//        }
//    }
//
//    /**
//     * 判断Service是否开启
//     *
//     */
//    fun isServiceRunning(context: Context, ServiceName: String): Boolean {
//        if (TextUtils.isEmpty(ServiceName)) {
//            return false
//        }
//        val myManager = context.getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
//        val runningService =
//            myManager.getRunningServices(1000) as ArrayList<ActivityManager.RunningServiceInfo>
//        for (i in runningService.indices) {
//            if (runningService[i].service.className == ServiceName) {
//                return true
//            }
//        }
//        return false
//    }
//
//
//
////    /**
////     * 检查无障碍服务权限是否开启
////     */
////    fun checkAccessibilityPermission(context: Activity, block: () -> Unit) {
////        if (isServiceRunning(context, WorkAccessibilityService::class.java.canonicalName)) {
////            block()
////        } else {
////            accessibilityToSettingPage(context)
////        }
////    }
//
//    fun isNull(any: Any?): Boolean = any == null
//
//}