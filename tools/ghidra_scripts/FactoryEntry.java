// Find how the factory test menu is entered: locate the page-name strings and
// decompile whatever references them.
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.util.task.ConsoleTaskMonitor;

import java.util.*;

public class FactoryEntry extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] want = {"FactoryTest", "FactoryCodeTest", "FactoryInputQcNum",
                         "FactoryMainBoardTest", "DeviceInfo"};
        Map<String, Set<Function>> hits = new LinkedHashMap<>();
        Map<String, ghidra.program.model.address.Address> at = new LinkedHashMap<>();

        DataIterator it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            Data d = it.next();
            if (!d.hasStringValue()) continue;
            String s = StringDataInstance.getStringDataInstance(d).getStringValue();
            if (s == null) continue;
            s = s.trim();
            for (String w : want) {
                if (!s.equals(w)) continue;
                at.put(w, d.getAddress());
                Set<Function> fs = hits.computeIfAbsent(w, k -> new LinkedHashSet<>());
                for (Reference r : getReferencesTo(d.getAddress())) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    if (f != null) fs.add(f);
                }
            }
        }

        println("======================================================================");
        println("FACTORY PAGE NAME STRINGS AND REFERRERS");
        println("======================================================================");
        for (String w : want) {
            println(String.format("%-22s %s   referrers=%s", w,
                    at.getOrDefault(w, null),
                    hits.containsKey(w) ? hits.get(w).size() : "n/a"));
            if (hits.containsKey(w)) {
                for (Function f : hits.get(w)) {
                    println("      " + f.getEntryPoint() + "  " + f.getName()
                            + "  size=" + f.getBody().getNumAddresses());
                }
            }
        }

        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int n = 0;
        for (Map.Entry<String, Set<Function>> e : hits.entrySet()) {
            if (!e.getKey().startsWith("Factory")) continue;
            for (Function f : e.getValue()) {
                if (n++ >= 4) break;
                println("\n==================================================");
                println("DECOMPILE " + f.getName() + " @ " + f.getEntryPoint()
                        + "   (references \"" + e.getKey() + "\")");
                println("==================================================");
                DecompileResults r = di.decompileFunction(f, 120, new ConsoleTaskMonitor());
                println(r.decompileCompleted()
                        ? r.getDecompiledFunction().getC()
                        : "  failed: " + r.getErrorMessage());
            }
        }
        di.dispose();
    }
}
