package app.deta.mobile;

import android.content.Context;
import android.view.View;
import android.view.ViewGroup;
import android.widget.EditText;
import android.widget.TextView;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 28)
public final class MainActivityStartupTest {
    @Test
    public void activityStartsWithoutLoadingTheModelDuringStartup() {
        RuntimeEnvironment.getApplication()
                .getSharedPreferences("deta_creator_v2", Context.MODE_PRIVATE)
                .edit().clear().commit();
        MainActivity activity = Robolectric.buildActivity(MainActivity.class).setup().get();
        View root = activity.getWindow().getDecorView();
        assertNotNull(root);
        assertTrue("The creator heading must be visible.", hasText(root, "O que vamos criar?"));
        assertTrue("The app prompt must be visible.", hasHint(root, "Descreva o app ou jogo que quer criar"));
    }

    private static boolean hasText(View view, String expected) {
        if (view instanceof TextView && expected.contentEquals(((TextView) view).getText())) return true;
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int index = 0; index < group.getChildCount(); index++) {
                if (hasText(group.getChildAt(index), expected)) return true;
            }
        }
        return false;
    }

    private static boolean hasHint(View view, String expected) {
        if (view instanceof EditText) {
            CharSequence hint = ((EditText) view).getHint();
            if (hint != null && expected.contentEquals(hint)) return true;
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int index = 0; index < group.getChildCount(); index++) {
                if (hasHint(group.getChildAt(index), expected)) return true;
            }
        }
        return false;
    }
}
