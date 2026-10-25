package br.com.realityengineai;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import cpw.mods.fml.common.Loader;
import cpw.mods.fml.common.ModContainer;
import cpw.mods.fml.common.registry.GameData;
import net.minecraft.block.Block;
import net.minecraft.entity.player.EntityPlayer;
import net.minecraft.item.Item;
import net.minecraft.util.ChatComponentText;

public final class ModKnowledgeBase {
    private ModKnowledgeBase() {
    }

    public static List<ModContainer> loadedMods() {
        try {
            return new ArrayList<ModContainer>(Loader.instance().getModList());
        } catch (RuntimeException exception) {
            return new ArrayList<ModContainer>();
        }
    }

    public static int countBlocks() {
        int count = 0;
        for (Block block : GameData.getBlockRegistry().typeSafeIterable()) {
            if (block != null) {
                count++;
            }
        }
        return count;
    }

    public static int countItems() {
        int count = 0;
        for (Item item : GameData.getItemRegistry().typeSafeIterable()) {
            if (item != null) {
                count++;
            }
        }
        return count;
    }

    public static int countNamespaces() {
        Map<String, Boolean> namespaces = new HashMap<String, Boolean>();
        for (Block block : GameData.getBlockRegistry().typeSafeIterable()) {
            if (block != null) {
                String name = GameData.getBlockRegistry().getNameForObject(block);
                if (name != null && name.indexOf(':') > 0) {
                    namespaces.put(name.substring(0, name.indexOf(':')), Boolean.TRUE);
                }
            }
        }
        for (Item item : GameData.getItemRegistry().typeSafeIterable()) {
            if (item != null) {
                String name = GameData.getItemRegistry().getNameForObject(item);
                if (name != null && name.indexOf(':') > 0) {
                    namespaces.put(name.substring(0, name.indexOf(':')), Boolean.TRUE);
                }
            }
        }
        return namespaces.size();
    }

    public static void sendInstalledMods(EntityPlayer player) {
        List<ModContainer> mods = loadedMods();
        Collections.sort(mods, new Comparator<ModContainer>() {
            @Override
            public int compare(ModContainer first, ModContainer second) {
                return safe(first.getModId()).compareToIgnoreCase(safe(second.getModId()));
            }
        });
        player.addChatMessage(new ChatComponentText("Reality Engine: " + mods.size() + " mods; " + countBlocks() + " blocos; " + countItems() + " itens; " + countNamespaces() + " namespaces."));
        if (mods.isEmpty()) {
            player.addChatMessage(new ChatComponentText("Forge não retornou uma lista de mods."));
            return;
        }
        StringBuilder line = new StringBuilder();
        int onLine = 0;
        for (ModContainer mod : mods) {
            String entry = safe(mod.getModId()) + " (" + safe(mod.getName()) + ", " + safe(mod.getVersion()) + ")";
            if (line.length() > 0) {
                line.append(" | ");
            }
            line.append(entry);
            onLine++;
            if (onLine == 3) {
                player.addChatMessage(new ChatComponentText(line.toString()));
                line.setLength(0);
                onLine = 0;
            }
        }
        if (line.length() > 0) {
            player.addChatMessage(new ChatComponentText(line.toString()));
        }
    }

    public static void sendRegistrySummary(EntityPlayer player) {
        player.addChatMessage(new ChatComponentText("Catálogo ativo do Forge: " + countBlocks() + " blocos e " + countItems() + " itens registrados."));
        player.addChatMessage(new ChatComponentText("O catálogo lê registros reais, inclusive de mods compatíveis carregados."));
        player.addChatMessage(new ChatComponentText("Use: crie lista de mods instalados"));
    }

    public static void sendRegistryMatches(EntityPlayer player, String query) {
        String normalized = normalize(query);
        int matches = 0;
        for (Block block : GameData.getBlockRegistry().typeSafeIterable()) {
            if (block == null) {
                continue;
            }
            String registryName = GameData.getBlockRegistry().getNameForObject(block);
            if (registryName != null && normalize(registryName).contains(normalized) && matches < 8) {
                player.addChatMessage(new ChatComponentText("Bloco: " + registryName));
                matches++;
            }
        }
        for (Item item : GameData.getItemRegistry().typeSafeIterable()) {
            if (item == null) {
                continue;
            }
            String registryName = GameData.getItemRegistry().getNameForObject(item);
            if (registryName != null && normalize(registryName).contains(normalized) && matches < 12) {
                player.addChatMessage(new ChatComponentText("Item: " + registryName));
                matches++;
            }
        }
        if (matches == 0) {
            player.addChatMessage(new ChatComponentText("Nenhum ID de bloco/item correspondeu a '" + query + "'."));
        }
    }

    public static String safe(String value) {
        return value == null || value.isEmpty() ? "desconhecido" : value;
    }

    public static String normalize(String value) {
        return java.text.Normalizer.normalize(value == null ? "" : value.toLowerCase(Locale.ROOT), java.text.Normalizer.Form.NFD).replaceAll("\\p{M}", "");
    }
}
