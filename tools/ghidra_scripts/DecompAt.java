// Decompile specific addresses. Addresses come from the GHIDRA_DECOMP_ADDRS
// environment variable, comma-separated hex (e.g. "0x02178d16,0x021a5022").
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.util.task.ConsoleTaskMonitor;

public class DecompAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String spec = System.getenv("GHIDRA_DECOMP_ADDRS");
        if (spec == null || spec.isEmpty()) {
            println("set GHIDRA_DECOMP_ADDRS");
            return;
        }
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (String s : spec.split(",")) {
            s = s.trim();
            if (s.isEmpty()) continue;
            Address a = toAddr(Long.decode(s));
            Function f = getFunctionContaining(a);
            println("======================================================================");
            if (f == null) {
                // Task entry points are only referenced via os_task_create, so
                // Ghidra's auto-analysis misses them. Define one here.
                println("no function at " + a + " — creating one");
                f = createFunction(a, null);
                if (f == null) {
                    println("  createFunction failed");
                    continue;
                }
            }
            println("DECOMPILE " + f.getName() + " @ " + f.getEntryPoint()
                    + "  (size " + f.getBody().getNumAddresses() + ")");
            println("callers:");
            int n = 0;
            for (Reference r : getReferencesTo(f.getEntryPoint())) {
                Function c = getFunctionContaining(r.getFromAddress());
                println("    " + r.getFromAddress() + "  "
                        + (c != null ? c.getName() : "<none>") + "  [" + r.getReferenceType() + "]");
                if (++n >= 10) { println("    ..."); break; }
            }
            if (n == 0) println("    (none)");
            println("======================================================================");
            DecompileResults res = di.decompileFunction(f, 180, new ConsoleTaskMonitor());
            println(res.decompileCompleted()
                    ? res.getDecompiledFunction().getC()
                    : "    failed: " + res.getErrorMessage());
        }
        di.dispose();
    }
}
