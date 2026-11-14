package br.com.japa.intx.core;

import net.minecraft.launchwrapper.IClassTransformer;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.FieldNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.IntInsnNode;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.TableSwitchInsnNode;
import org.objectweb.asm.tree.VarInsnNode;

public final class IntXTransformer implements IClassTransformer, Opcodes {
    private static final Logger LOGGER = LogManager.getLogger("IntX-Core");
    private static final String TARGET = "net.minecraft.entity.DataWatcher";
    private static final String HOOKS = "br/com/japa/intx/core/LongDataWatcherHooks";

    @Override
    public byte[] transform(String name, String transformedName, byte[] basicClass) {
        String candidate = transformedName == null ? name : transformedName;
        if (basicClass == null || candidate == null
            || !TARGET.equals(candidate.replace('/', '.'))) return basicClass;

        try {
            ClassReader reader = new ClassReader(basicClass);
            ClassNode node = new ClassNode();
            reader.accept(node, ClassReader.EXPAND_FRAMES);

            FieldNode types = findDataTypesField(node);
            MethodNode initializer = findInitializer(node);
            MethodNode writer = findWriter(node);
            MethodNode decoder = findDecoder(node);
            if (types == null || initializer == null || writer == null || decoder == null) {
                throw new IllegalStateException("DataWatcher structure differs from audited 1.7.10 layout");
            }

            TableSwitchInsnNode writeSwitch = findSwitch(writer);
            TableSwitchInsnNode readSwitch = findSwitch(decoder);
            if (writeSwitch == null || readSwitch == null || decoder.maxLocals < 6) {
                throw new IllegalStateException("Expected type switch 0..6 or decoder local layout not found");
            }

            registerTypeSeven(node, types, initializer);
            addWriterCase(writer, writeSwitch);
            addReaderCase(node, decoder, readSwitch);

            ClassWriter output = new SafeClassWriter(
                reader, ClassWriter.COMPUTE_FRAMES | ClassWriter.COMPUTE_MAXS
            );
            node.accept(output);
            IntXRuntime.dataWatcherLongSupported = true;
            LOGGER.info("Patched DataWatcher: java.lang.Long registered as type 7");
            return output.toByteArray();
        } catch (Throwable error) {
            IntXRuntime.dataWatcherLongSupported = false;
            LOGGER.error("DataWatcher patch rejected safely; BigInteger API remains enabled", error);
            return basicClass;
        }
    }

    private static FieldNode findDataTypesField(ClassNode node) {
        FieldNode found = null;
        for (Object raw : node.fields) {
            FieldNode field = (FieldNode) raw;
            if ((field.access & ACC_STATIC) != 0 && "Ljava/util/HashMap;".equals(field.desc)) {
                if (found != null) throw new IllegalStateException("Ambiguous static HashMap in DataWatcher");
                found = field;
            }
        }
        return found;
    }

    private static MethodNode findInitializer(ClassNode node) {
        for (Object raw : node.methods) {
            MethodNode method = (MethodNode) raw;
            if ("<clinit>".equals(method.name) && "()V".equals(method.desc)) return method;
        }
        return null;
    }

    private static MethodNode findWriter(ClassNode node) {
        MethodNode found = null;
        for (Object raw : node.methods) {
            MethodNode method = (MethodNode) raw;
            if ((method.access & ACC_STATIC) == 0 || findSwitch(method) == null) continue;
            Type[] args = Type.getArgumentTypes(method.desc);
            if (args.length == 2 && Type.getReturnType(method.desc).getSort() == Type.VOID) {
                if (found != null) throw new IllegalStateException("Ambiguous DataWatcher writer");
                found = method;
            }
        }
        return found;
    }

    private static MethodNode findDecoder(ClassNode node) {
        MethodNode found = null;
        for (Object raw : node.methods) {
            MethodNode method = (MethodNode) raw;
            if ((method.access & ACC_STATIC) == 0 || findSwitch(method) == null) continue;
            Type[] args = Type.getArgumentTypes(method.desc);
            Type result = Type.getReturnType(method.desc);
            if (args.length == 1 && result.getSort() == Type.OBJECT
                && "java/util/List".equals(result.getInternalName())) {
                if (found != null) throw new IllegalStateException("Ambiguous DataWatcher decoder");
                found = method;
            }
        }
        return found;
    }

    private static TableSwitchInsnNode findSwitch(MethodNode method) {
        for (AbstractInsnNode instruction : method.instructions.toArray()) {
            if (instruction instanceof TableSwitchInsnNode) {
                TableSwitchInsnNode table = (TableSwitchInsnNode) instruction;
                if (table.min == 0 && table.max == 6 && table.labels.size() == 7) return table;
            }
        }
        return null;
    }

    private static void registerTypeSeven(ClassNode node, FieldNode field, MethodNode initializer) {
        AbstractInsnNode lastReturn = null;
        for (AbstractInsnNode instruction : initializer.instructions.toArray()) {
            if (instruction.getOpcode() == RETURN) lastReturn = instruction;
        }
        if (lastReturn == null) throw new IllegalStateException("DataWatcher <clinit> has no RETURN");

        InsnList code = new InsnList();
        code.add(new FieldInsnNode(GETSTATIC, node.name, field.name, field.desc));
        code.add(new LdcInsnNode(Type.getType(Long.class)));
        code.add(new IntInsnNode(BIPUSH, 7));
        code.add(new MethodInsnNode(INVOKESTATIC, "java/lang/Integer", "valueOf",
            "(I)Ljava/lang/Integer;", false));
        code.add(new MethodInsnNode(INVOKEVIRTUAL, "java/util/HashMap", "put",
            "(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;", false));
        code.add(new InsnNode(POP));
        initializer.instructions.insertBefore(lastReturn, code);
    }

    private static void addWriterCase(MethodNode method, TableSwitchInsnNode table) {
        Type[] args = Type.getArgumentTypes(method.desc);
        String descriptor = Type.getMethodDescriptor(Type.VOID_TYPE, args[0], args[1]);
        org.objectweb.asm.tree.LabelNode longCase = new org.objectweb.asm.tree.LabelNode();

        InsnList code = new InsnList();
        code.add(longCase);
        code.add(new VarInsnNode(ALOAD, 0));
        code.add(new VarInsnNode(ALOAD, 1));
        code.add(new MethodInsnNode(INVOKESTATIC, HOOKS, "writeLong", descriptor, false));
        code.add(new JumpInsnNode(GOTO, table.dflt));

        table.max = 7;
        table.labels.add(longCase);
        method.instructions.insertBefore(table.dflt, code);
    }

    private static void addReaderCase(ClassNode node, MethodNode method, TableSwitchInsnNode table) {
        Type[] args = Type.getArgumentTypes(method.desc);
        Type watchable = Type.getObjectType(node.name + "$WatchableObject");
        String descriptor = Type.getMethodDescriptor(
            watchable, args[0], Type.INT_TYPE, Type.INT_TYPE
        );
        org.objectweb.asm.tree.LabelNode longCase = new org.objectweb.asm.tree.LabelNode();

        InsnList code = new InsnList();
        code.add(longCase);
        code.add(new VarInsnNode(ALOAD, 0));
        code.add(new VarInsnNode(ILOAD, 3));
        code.add(new VarInsnNode(ILOAD, 4));
        code.add(new MethodInsnNode(INVOKESTATIC, HOOKS, "readLong", descriptor, false));
        code.add(new VarInsnNode(ASTORE, 5));
        code.add(new JumpInsnNode(GOTO, table.dflt));

        table.max = 7;
        table.labels.add(longCase);
        method.instructions.insertBefore(table.dflt, code);
    }

    private static final class SafeClassWriter extends ClassWriter {
        SafeClassWriter(ClassReader reader, int flags) { super(reader, flags); }
        @Override
        protected String getCommonSuperClass(String first, String second) {
            try { return super.getCommonSuperClass(first, second); }
            catch (Throwable ignored) { return "java/lang/Object"; }
        }
    }
}
