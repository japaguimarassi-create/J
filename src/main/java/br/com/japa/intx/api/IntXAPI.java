package br.com.japa.intx.api;

import br.com.japa.intx.data.PlayerNumbers;
import br.com.japa.intx.network.IntXNetwork;
import br.com.japa.intx.numeric.NumberLimits;
import net.minecraft.entity.player.EntityPlayer;
import java.math.BigInteger;
import java.util.Map;

public final class IntXAPI {
    private IntXAPI() {
    }

    public static BigInteger get(EntityPlayer player, String key) {
        return PlayerNumbers.get(player).get(key);
    }

    public static Map<String, BigInteger> snapshot(EntityPlayer player) {
        return PlayerNumbers.get(player).snapshot();
    }

    public static void set(EntityPlayer player, String key, BigInteger value) {
        requireServer(player);
        NumberLimits.validate(value);
        PlayerNumbers.get(player).set(key, value);
        IntXNetwork.sync(player);
    }

    public static BigInteger add(EntityPlayer player, String key, BigInteger amount) {
        requireServer(player);
        BigInteger result = PlayerNumbers.get(player).add(key, amount);
        IntXNetwork.sync(player);
        return result;
    }

    public static void remove(EntityPlayer player, String key) {
        requireServer(player);
        PlayerNumbers.get(player).remove(key);
        IntXNetwork.sync(player);
    }

    private static void requireServer(EntityPlayer player) {
        if (player == null || player.worldObj == null || player.worldObj.isRemote) {
            throw new IllegalStateException("IntX values must be modified on the logical server");
        }
    }
}
