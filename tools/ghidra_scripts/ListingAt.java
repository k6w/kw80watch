// Print disassembly around an address, and try to define a function there.
// GHIDRA_LIST_ADDR = hex address, GHIDRA_LIST_BACK / GHIDRA_LIST_FWD = byte counts.
// @category KW80
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.util.task.ConsoleTaskMonitor;

public class ListingAt extends GhidraScript {
    @Override
    public void run() throws Exception {
        String spec = System.getenv("GHIDRA_LIST_ADDR");
        if (spec == null) { println("set GHIDRA_LIST_ADDR"); return; }
        long back = Long.decode(System.getenv().getOrDefault("GHIDRA_LIST_BACK", "0x80"));
        long fwd  = Long.decode(System.getenv().getOrDefault("GHIDRA_LIST_FWD",  "0x60"));
        Address target = toAddr(Long.decode(spec));

        println("=========== disassembly around " + target + " ===========");
        Address a = target.subtract(back);
        while (a.compareTo(target.add(fwd)) < 0) {
            Instruction ins = getInstructionAt(a);
            if (ins == null) {
                println("  " + a + "  (no instruction)");
                a = a.add(2);
                continue;
            }
            String mark = ins.getAddress().equals(target) ? "   <<< TARGET" : "";
            Function f = getFunctionContaining(a);
            println(String.format("  %s  %-40s %s%s", a, ins.toString(),
                    f != null ? "[" + f.getName() + "]" : "", mark));
            a = a.add(ins.getLength());
        }

        // Walk back to a push{...,lr} prologue and define a function there.
        println("\n=========== searching backwards for a prologue ===========");
        Address p = target;
        for (int i = 0; i < 400; i++) {
            Instruction ins = getInstructionAt(p);
            if (ins != null && ins.getMnemonicString().toLowerCase().startsWith("push")) {
                println("  candidate prologue at " + p + " : " + ins);
                Function f = getFunctionContaining(p);
                if (f == null) {
                    f = createFunction(p, null);
                    println("  createFunction -> " + (f != null ? f.getName() : "failed"));
                }
                if (f != null) {
                    DecompInterface di = new DecompInterface();
                    di.openProgram(currentProgram);
                    DecompileResults r = di.decompileFunction(f, 180, new ConsoleTaskMonitor());
                    println("\n=========== DECOMPILE " + f.getName() + " ===========");
                    println(r.decompileCompleted()
                            ? r.getDecompiledFunction().getC()
                            : "  failed: " + r.getErrorMessage());
                    di.dispose();
                    return;
                }
            }
            p = p.subtract(2);
        }
        println("  no prologue found");
    }
}
