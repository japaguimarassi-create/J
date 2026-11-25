package br.com.japa.dmzdbc.compat;

public final class DbcCompatibility {
    private static final String DBC_CLASS = "JinRyuu.DragonBC.common.DBCClient";
    private static final String JRMCORE_CLASS = "JinRyuu.JRMCore.JRMCoreH";

    private DbcCompatibility() {
    }

    public static boolean isPresent() {
        return classExists(DBC_CLASS) && classExists(JRMCORE_CLASS);
    }

    private static boolean classExists(String className) {
        try {
            Class.forName(className, false, DbcCompatibility.class.getClassLoader());
            return true;
        } catch (ClassNotFoundException exception) {
            return false;
        } catch (LinkageError error) {
            return false;
        }
    }
}
