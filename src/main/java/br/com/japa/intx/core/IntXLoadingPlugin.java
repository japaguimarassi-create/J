package br.com.japa.intx.core;

import cpw.mods.fml.relauncher.IFMLLoadingPlugin;
import java.util.Map;

@IFMLLoadingPlugin.MCVersion("1.7.10")
@IFMLLoadingPlugin.Name("IntX Core")
@IFMLLoadingPlugin.SortingIndex(1001)
@IFMLLoadingPlugin.TransformerExclusions({"br.com.japa.intx.core"})
public final class IntXLoadingPlugin implements IFMLLoadingPlugin {
    @Override public String[] getASMTransformerClass() {
        return new String[] {"br.com.japa.intx.core.IntXTransformer"};
    }
    @Override public String getModContainerClass() { return null; }
    @Override public String getSetupClass() { return null; }
    @Override public void injectData(Map<String, Object> data) { }
    @Override public String getAccessTransformerClass() { return null; }
}
