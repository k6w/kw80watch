// Find the handler for GUI message opcode 0x41c (and 0x4c8), posted by the
// watchface loader FUN_020e593c.
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;
import ghidra.util.task.ConsoleTaskMonitor;

import java.util.*;

public class FindMsgHandler extends GhidraScript {

    private static final long[] OPCODES = {0x41cL, 0x4c8L};
    private static final long LOADER = 0x020e593cL;

    @Override
    public void run() throws Exception {
        // function -> which opcodes it mentions, and how often
        Map<Function, Map<Long, Integer>> hits = new LinkedHashMap<>();

        InstructionIterator ii = currentProgram.getListing().getInstructions(true);
        long scanned = 0;
        while (ii.hasNext()) {
            Instruction ins = ii.next();
            scanned++;
            for (int op = 0; op < ins.getNumOperands(); op++) {
                for (Object o : ins.getOpObjects(op)) {
                    if (!(o instanceof Scalar)) continue;
                    long v = ((Scalar) o).getUnsignedValue();
                    for (long want : OPCODES) {
                        if (v != want) continue;
                        Function f = getFunctionContaining(ins.getAddress());
                        if (f == null) continue;
                        hits.computeIfAbsent(f, k -> new TreeMap<>())
                            .merge(want, 1, Integer::sum);
                    }
                }
            }
        }
        println("instructions scanned: " + scanned);
        println("======================================================================");
        println("FUNCTIONS MENTIONING OPCODE 0x41c / 0x4c8");
        println("======================================================================");

        List<Function> ranked = new ArrayList<>(hits.keySet());
        // Prefer functions that mention both opcodes, then bigger functions (dispatchers).
        ranked.sort((a, b) -> {
            int ca = hits.get(a).size(), cb = hits.get(b).size();
            if (ca != cb) return cb - ca;
            return Long.compare(b.getBody().getNumAddresses(), a.getBody().getNumAddresses());
        });

        for (Function f : ranked) {
            String tag = (f.getEntryPoint().getOffset() == LOADER) ? "   <-- the loader (source)" : "";
            println(String.format("%-12s %-22s size=%-6d opcodes=%s%s",
                    f.getEntryPoint(), f.getName(),
                    f.getBody().getNumAddresses(), hits.get(f), tag));
        }
        println("\ntotal functions: " + ranked.size());

        // Decompile the best non-loader candidates.
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int emitted = 0;
        for (Function f : ranked) {
            if (f.getEntryPoint().getOffset() == LOADER) continue;
            if (emitted >= 3) break;
            println("\n======================================================================");
            println("DECOMPILE " + f.getName() + " @ " + f.getEntryPoint()
                    + "   (size " + f.getBody().getNumAddresses() + ")");
            println("======================================================================");
            DecompileResults r = di.decompileFunction(f, 180, new ConsoleTaskMonitor());
            println(r.decompileCompleted()
                    ? r.getDecompiledFunction().getC()
                    : "    failed: " + r.getErrorMessage());
            emitted++;
        }
        di.dispose();
    }
}
