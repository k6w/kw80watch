// Attribute functions to source files via embedded __FILE__ strings,
// then decompile the image-decoder candidates.
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.util.task.ConsoleTaskMonitor;

import java.util.*;

public class ModuleMap extends GhidraScript {

    private void banner(String s) {
        println("======================================================================");
        println(s);
        println("======================================================================");
    }

    @Override
    public void run() throws Exception {
        // source-path string -> functions that reference it
        Map<String, Set<Function>> byFile = new TreeMap<>();
        Map<String, Address> fileAddr = new TreeMap<>();

        DataIterator it = currentProgram.getListing().getDefinedData(true);
        int scanned = 0;
        while (it.hasNext()) {
            Data d = it.next();
            scanned++;
            if (!d.hasStringValue()) continue;
            StringDataInstance sdi = StringDataInstance.getStringDataInstance(d);
            String s = sdi.getStringValue();
            if (s == null || !s.contains("src\\app\\watch")) continue;

            String shortName = s.substring(s.lastIndexOf('\\') + 1);
            // keep the last two path components for context
            String path = s.replace("..\\", "");
            fileAddr.put(path, d.getAddress());

            Set<Function> fs = byFile.computeIfAbsent(path, k -> new LinkedHashSet<>());
            for (Reference ref : getReferencesTo(d.getAddress())) {
                Function f = getFunctionContaining(ref.getFromAddress());
                if (f != null) fs.add(f);
            }
        }

        banner("MODULE MAP  (source file -> functions referencing its __FILE__ string)\n"
                + "defined data scanned: " + scanned);
        int totalFuncs = 0;
        for (Map.Entry<String, Set<Function>> e : byFile.entrySet()) {
            println(String.format("%-62s %s  (%d fn)",
                    e.getKey(), fileAddr.get(e.getKey()), e.getValue().size()));
            for (Function f : e.getValue()) {
                println("        " + f.getEntryPoint() + "  " + f.getName());
                totalFuncs++;
            }
        }
        println("\ntotal attributed functions: " + totalFuncs
                + " across " + byFile.size() + " source files");

        // Decompile anything attributed to image decoding / drawing.
        String[] wanted = {"lv_img_decoder.c", "lv_img_buf.c", "lv_draw_img.c", "lv_img_cache.c"};
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int emitted = 0;
        for (Map.Entry<String, Set<Function>> e : byFile.entrySet()) {
            boolean hit = false;
            for (String w : wanted) if (e.getKey().endsWith(w)) hit = true;
            if (!hit) continue;
            for (Function f : e.getValue()) {
                if (emitted >= 5) break;
                banner("DECOMPILE " + f.getName() + " @ " + f.getEntryPoint()
                        + "\nfrom " + e.getKey());
                DecompileResults r = di.decompileFunction(f, 120, new ConsoleTaskMonitor());
                println(r.decompileCompleted()
                        ? r.getDecompiledFunction().getC()
                        : "    failed: " + r.getErrorMessage());
                emitted++;
            }
        }
        di.dispose();
    }
}
