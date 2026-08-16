// Locate hardware drivers via their debug strings, decompile them, and pull out
// constants that look like I2C addresses or panel opcodes.
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
import java.util.regex.*;

public class HwProbe extends GhidraScript {

    // Debug strings that sit inside peripheral drivers.
    private static final String[] NEEDLES = {
        "Gsensor", "G-SENSOR", "FLASH ID", "flash switch 4bit",
        "console_uart_init", "DMA uart_tx_ch_num", "amp_timer_on",
    };

    @Override
    public void run() throws Exception {
        Map<String, Set<Function>> hits = new LinkedHashMap<>();

        DataIterator it = currentProgram.getListing().getDefinedData(true);
        while (it.hasNext()) {
            Data d = it.next();
            if (!d.hasStringValue()) continue;
            StringDataInstance sdi = StringDataInstance.getStringDataInstance(d);
            String s = sdi.getStringValue();
            if (s == null) continue;
            for (String n : NEEDLES) {
                if (!s.contains(n)) continue;
                Set<Function> fs = hits.computeIfAbsent(
                        n + "  @" + d.getAddress() + "  \"" + s.trim() + "\"",
                        k -> new LinkedHashSet<>());
                for (Reference r : getReferencesTo(d.getAddress())) {
                    Function f = getFunctionContaining(r.getFromAddress());
                    if (f != null) fs.add(f);
                }
            }
        }

        println("======================================================================");
        println("HARDWARE DRIVER STRINGS AND THEIR FUNCTIONS");
        println("======================================================================");
        Set<Function> toDecomp = new LinkedHashSet<>();
        for (Map.Entry<String, Set<Function>> e : hits.entrySet()) {
            println(e.getKey());
            for (Function f : e.getValue()) {
                println("      " + f.getEntryPoint() + "  " + f.getName()
                        + "  size=" + f.getBody().getNumAddresses());
                toDecomp.add(f);
            }
            if (e.getValue().isEmpty()) println("      (no references)");
        }

        // Decompile and surface byte-sized constants (candidate I2C addresses / opcodes).
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        Pattern hex = Pattern.compile("0x[0-9a-f]{1,2}\\b");
        int n = 0;
        for (Function f : toDecomp) {
            if (n++ >= 6) break;
            DecompileResults r = di.decompileFunction(f, 120, new ConsoleTaskMonitor());
            if (!r.decompileCompleted()) continue;
            String c = r.getDecompiledFunction().getC();
            println("\n======================================================================");
            println("DECOMPILE " + f.getName() + " @ " + f.getEntryPoint());
            println("======================================================================");
            println(c);
            Matcher m = hex.matcher(c);
            TreeSet<Integer> consts = new TreeSet<>();
            while (m.find()) {
                int v = Integer.decode(m.group());
                if (v >= 0x08 && v <= 0xEF) consts.add(v);
            }
            println("  byte-range constants: " + consts);
        }
        di.dispose();
    }
}
