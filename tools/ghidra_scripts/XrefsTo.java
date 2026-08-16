// Print cross-references to arbitrary addresses (code or data).
// GHIDRA_XREF_ADDRS = comma-separated hex.
// @category KW80
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;

public class XrefsTo extends GhidraScript {
    @Override
    public void run() throws Exception {
        String spec = System.getenv("GHIDRA_XREF_ADDRS");
        if (spec == null || spec.isEmpty()) { println("set GHIDRA_XREF_ADDRS"); return; }
        for (String s : spec.split(",")) {
            s = s.trim();
            if (s.isEmpty()) continue;
            Address a = toAddr(Long.decode(s));
            println("================ xrefs to " + a + " ================");
            try {
                println("  value there: 0x" + Integer.toHexString(getInt(a)));
            } catch (Exception e) {
                println("  (unreadable)");
            }
            int n = 0;
            for (Reference r : getReferencesTo(a)) {
                Function f = getFunctionContaining(r.getFromAddress());
                println(String.format("  %s  %-24s size=%-6s [%s]",
                        r.getFromAddress(),
                        f != null ? f.getName() : "<none>",
                        f != null ? String.valueOf(f.getBody().getNumAddresses()) : "-",
                        r.getReferenceType()));
                if (++n >= 25) { println("  ..."); break; }
            }
            if (n == 0) println("  (no references)");
        }
    }
}
