package com.changanhe.kexinglu

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * 直接用系统 LocationManager 取定位，绕开 Google 融合定位（部分国产 ROM 不可用）。
 * 只接受“新鲜”的定位（2 分钟内），避免把上次在别的城市的位置当成当前位置；
 * 同时向 FUSED / NETWORK / GPS 并行请求，谁先给出新鲜结果就用谁。
 */
class MainActivity : FlutterActivity() {
    private val channelName = "kexinglu/weather_location"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName)
            .setMethodCallHandler { call, result ->
                if (call.method == "getLocation") {
                    getLocation(result)
                } else {
                    result.notImplemented()
                }
            }
    }

    private fun hasPermission(): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return true
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
    }

    private fun isFresh(location: Location): Boolean {
        return System.currentTimeMillis() - location.time <= 2 * 60 * 1000
    }

    private fun getLocation(result: MethodChannel.Result) {
        if (!hasPermission()) { result.success(null); return }
        val manager = getSystemService(LOCATION_SERVICE) as? LocationManager
        if (manager == null) { result.success(null); return }

        // 1) 只在“最近 2 分钟”的 lastKnown 中挑选，避免旧城市。
        var recent: Location? = null
        try {
            for (provider in manager.getProviders(true)) {
                val location = try { manager.getLastKnownLocation(provider) } catch (_: Exception) { null } ?: continue
                if (!isFresh(location)) continue
                if (recent == null || location.time > recent!!.time) recent = location
            }
        } catch (_: Exception) {}
        if (recent != null) { result.success(toMap(recent)); return }

        // 2) 并行向 FUSED / NETWORK / GPS 请求一次实时定位，谁先到用谁。
        val providers = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            manager.isProviderEnabled(LocationManager.FUSED_PROVIDER)) {
            providers.add(LocationManager.FUSED_PROVIDER)
        }
        if (manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
            providers.add(LocationManager.NETWORK_PROVIDER)
        }
        if (manager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
            providers.add(LocationManager.GPS_PROVIDER)
        }
        if (providers.isEmpty()) { result.success(null); return }

        val handler = Handler(Looper.getMainLooper())
        var finished = false
        val listeners = mutableListOf<LocationListener>()

        fun cleanup() {
            for (listener in listeners) {
                try { manager.removeUpdates(listener) } catch (_: Exception) {}
            }
            listeners.clear()
            handler.removeCallbacksAndMessages(null)
        }

        fun finish(location: Location?) {
            if (finished) return
            finished = true
            cleanup()
            result.success(toMap(location))
        }

        for (provider in providers) {
            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    // 忽略 provider 立即回放的旧缓存，只接受新鲜定位。
                    if (isFresh(location)) finish(location)
                }
                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {}
            }
            listeners.add(listener)
            try {
                manager.requestLocationUpdates(provider, 0L, 0f, listener, Looper.getMainLooper())
            } catch (_: Exception) {
                try { manager.removeUpdates(listener) } catch (_: Exception) {}
                listeners.remove(listener)
            }
        }
        if (listeners.isEmpty()) { finish(null); return }
        handler.postDelayed({ finish(null) }, 15000)
    }

    private fun toMap(location: Location?): Map<String, Any>? {
        if (location == null) return null
        return mapOf(
            "lat" to location.latitude,
            "lon" to location.longitude,
            "accuracy" to location.accuracy.toDouble(),
            "time" to location.time
        )
    }
}
