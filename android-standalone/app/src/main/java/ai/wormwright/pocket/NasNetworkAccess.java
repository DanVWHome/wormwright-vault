package ai.wormwright.pocket;
import android.Manifest;
import android.content.Context;
import android.content.pm.PackageManager;
final class NasNetworkAccess {
    static boolean allowed(Context context){return context.checkSelfPermission(Manifest.permission.INTERNET)==PackageManager.PERMISSION_GRANTED;}
    private NasNetworkAccess() { }
}
