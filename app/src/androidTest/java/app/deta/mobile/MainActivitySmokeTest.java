package app.deta.mobile;

import androidx.test.core.app.ActivityScenario;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Test;
import org.junit.runner.RunWith;
import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.action.ViewActions.closeSoftKeyboard;
import static androidx.test.espresso.action.ViewActions.typeText;
import static androidx.test.espresso.assertion.ViewAssertions.matches;
import static androidx.test.espresso.matcher.ViewMatchers.isDisplayed;
import static androidx.test.espresso.matcher.ViewMatchers.withContentDescription;
import static androidx.test.espresso.matcher.ViewMatchers.withHint;
import static androidx.test.espresso.matcher.ViewMatchers.withText;

@RunWith(AndroidJUnit4.class)
public final class MainActivitySmokeTest {
    @Test
    public void applicationStartsAndShowsComposer() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withHint("Escreva uma mensagem ou nota")).check(matches(isDisplayed()));
            onView(withContentDescription("Abrir menu")).check(matches(isDisplayed()));
            onView(withContentDescription("Enviar mensagem")).check(matches(isDisplayed()));
        }
    }

    @Test
    public void localMessageCanBeSaved() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withHint("Escreva uma mensagem ou nota"))
                    .perform(typeText("Mensagem local aprovada"), closeSoftKeyboard());
            onView(withContentDescription("Enviar mensagem")).perform(click());
            onView(withText("Mensagem local aprovada")).check(matches(isDisplayed()));
        }
    }

    @Test
    public void drawerOpensAndCreatesConversation() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withContentDescription("Abrir menu")).perform(click());
            onView(withText("Conversas")).check(matches(isDisplayed()));
            onView(withContentDescription("Criar conversa")).perform(click());
            onView(withHint("Escreva uma mensagem ou nota")).check(matches(isDisplayed()));
        }
    }

    @Test
    public void messagePersistsWhenActivityIsRecreated() {
        try (ActivityScenario<MainActivity> scenario = ActivityScenario.launch(MainActivity.class)) {
            onView(withHint("Escreva uma mensagem ou nota"))
                    .perform(typeText("Persistencia aprovada"), closeSoftKeyboard());
            onView(withContentDescription("Enviar mensagem")).perform(click());
            scenario.recreate();
            onView(withText("Persistencia aprovada")).check(matches(isDisplayed()));
        }
    }
}
