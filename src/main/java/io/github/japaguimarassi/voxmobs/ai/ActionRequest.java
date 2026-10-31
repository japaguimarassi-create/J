package io.github.japaguimarassi.voxmobs.ai;

public record ActionRequest(MobAction action, String argument) {
    public ActionRequest {
        action = action == null ? MobAction.NONE : action;
        argument = argument == null ? "" : argument.trim();
        if (argument.length() > 128) {
            argument = argument.substring(0, 128);
        }
    }
}
