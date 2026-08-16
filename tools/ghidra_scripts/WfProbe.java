// Locate watchface / BLE handling in the SWC01 firmware.
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

import java.util.LinkedHashSet;
import java.util.Set;

public class WfProbe extends GhidraScript {

    private Set<Address> toDecompile = new LinkedHashSet<>();

    private void banner(String s) {
        println("======================================================================");
        println(s);
        println("======================================================================");
    }

    /** Print every reference to addr, and remember the containing functions. */
    private int showRefs(String label, Address addr) {
        println("");
        println("--- " + label + " @ " + addr + " ---");
        int n = 0;
        for (Reference ref : getReferencesTo(addr)) {
            Function f = getFunctionContaining(ref.getFromAddress());
            println("    from " + ref.getFromAddress()
                    + "  in " + (f != null ? f.getName() + " @ " + f.getEntryPoint() : "<no function>")
                    + "  [" + ref.getReferenceType() + "]");
            if (f != null) {
                toDecompile.add(f.getEntryPoint());
            }
            n++;
            if (n >= 15) {
                println("    ... (truncated)");
                break;
            }
        }
        if (n == 0) {
            println("    (no references)");
        }
        return n;
    }

    @Override
    public void run() throws Exception {
        banner("program : " + currentProgram.getName()
                + "\nbase    : " + currentProgram.getImageBase()
                + "\nfuncs   : " + currentProgram.getFunctionManager().getFunctionCount());

        Address base = currentProgram.getImageBase();

        // File-type tag table discovered at file offset 0x3cbd4.
        showRefs("tag OLWF",   base.add(0x3CBD4L));
        showRefs("tag FACE",   base.add(0x3CBDCL));
        showRefs("tag SOCIAL", base.add(0x3CBE4L));

        // Walk defined strings for the BLE characteristic names and watchface terms.
        banner("interesting defined strings");
        String[] wanted = {
            "Characteristic 8001", "Characteristic 8002",
            "Characteristic 8003", "Characteristic 8004",
            "Characteristic 1531", "Characteristic 1532",
            "OLWF", "FACE", "SOCIAL"
        };
        DataIterator it = currentProgram.getListing().getDefinedData(true);
        int scanned = 0;
        while (it.hasNext() && scanned < 400000) {
            Data d = it.next();
            scanned++;
            if (!d.hasStringValue()) {
                continue;
            }
            StringDataInstance sdi = StringDataInstance.getStringDataInstance(d);
            String s = sdi.getStringValue();
            if (s == null) {
                continue;
            }
            s = s.trim();
            for (String w : wanted) {
                if (s.equals(w)) {
                    showRefs("string \"" + w + "\"", d.getAddress());
                }
            }
        }
        println("");
        println("defined data scanned: " + scanned);

        // Decompile everything that touched those constants.
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        int emitted = 0;
        for (Address entry : toDecompile) {
            if (emitted >= 6) {
                println("\n(stopping after 6 decompilations)");
                break;
            }
            Function f = getFunctionAt(entry);
            if (f == null) {
                continue;
            }
            banner("DECOMPILE " + f.getName() + " @ " + entry);
            DecompileResults res = di.decompileFunction(f, 120, new ghidra.util.task.ConsoleTaskMonitor());
            if (res.decompileCompleted()) {
                println(res.getDecompiledFunction().getC());
            } else {
                println("    failed: " + res.getErrorMessage());
            }
            emitted++;
        }
        di.dispose();
    }
}
