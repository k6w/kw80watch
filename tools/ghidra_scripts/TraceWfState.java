// Find every function that touches the watchface header fields parsed by
// FUN_020e593c, by decompiling all users of the global state pointer and
// grepping for the known struct offsets.
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.util.task.ConsoleTaskMonitor;

import java.util.*;

public class TraceWfState extends GhidraScript {

    // Offsets written by FUN_020e593c: off1, off2, cnt, off3, len3 (and the copies).
    private static final String[] OFFSETS = {
        "0x697", "0x69b", "0x69f", "0x6a3", "0x6a7",
        "0x214", "0x218", "0x21c", "0x220", "0x224", "0x228"
    };

    @Override
    public void run() throws Exception {
        Address holder = toAddr(0x020e5bc0L);   // DAT_020e5bc0 — holds the state pointer
        println("state-pointer holder: " + holder);

        Set<Function> users = new LinkedHashSet<>();
        for (Reference ref : getReferencesTo(holder)) {
            Function f = getFunctionContaining(ref.getFromAddress());
            if (f != null) users.add(f);
        }
        println("functions referencing it: " + users.size());

        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        ConsoleTaskMonitor mon = new ConsoleTaskMonitor();

        List<String> hits = new ArrayList<>();
        Map<Function, String> bodies = new LinkedHashMap<>();
        for (Function f : users) {
            DecompileResults r = di.decompileFunction(f, 90, mon);
            if (!r.decompileCompleted()) continue;
            String c = r.getDecompiledFunction().getC();
            StringBuilder found = new StringBuilder();
            for (String o : OFFSETS) if (c.contains(o)) found.append(o).append(" ");
            if (found.length() > 0) {
                hits.add(String.format("%-12s %-22s touches: %s",
                        f.getEntryPoint().toString(), f.getName(), found));
                bodies.put(f, c);
            }
        }

        println("======================================================================");
        println("FUNCTIONS TOUCHING WATCHFACE HEADER FIELDS");
        println("======================================================================");
        for (String h : hits) println(h);
        println("\ntotal: " + hits.size());

        int n = 0;
        for (Map.Entry<Function, String> e : bodies.entrySet()) {
            if (e.getKey().getEntryPoint().getOffset() == 0x020e593cL) continue; // already have it
            if (n++ >= 3) break;
            println("\n======================================================================");
            println("DECOMPILE " + e.getKey().getName() + " @ " + e.getKey().getEntryPoint());
            println("======================================================================");
            println(e.getValue());
        }
        di.dispose();
    }
}
