package ai.wormwright.pocket;
import android.app.Activity;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.annotation.Config;
import static org.robolectric.Shadows.shadowOf;
import static org.junit.Assert.*;
@RunWith(RobolectricTestRunner.class)
@Config(manifest=Config.NONE,sdk=35,application=android.app.Application.class)
public class NasNetworkAccessTest {
 @Test public void recognizesPerAppNetworkPermission(){Activity a=Robolectric.buildActivity(Activity.class).setup().get();shadowOf(a).denyPermissions(android.Manifest.permission.INTERNET);assertFalse(NasNetworkAccess.allowed(a));shadowOf(a).grantPermissions(android.Manifest.permission.INTERNET);assertTrue(NasNetworkAccess.allowed(a));}
}
