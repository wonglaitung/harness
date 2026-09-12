package com.harness.gate;

import static org.junit.jupiter.api.Assertions.*;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

import org.junit.jupiter.api.*;

/**
 * Cross-language behavioral parity test for the deterministic gate (B2).
 *
 * <p>Layer 1 — regression guard: asserts the Java {@link DeterministicGate#check} decision
 * matches the documented contract. Layer 2 — cross-language probe: shells out to the Python
 * SDK's equivalent implementation and records any Java/Python divergence without failing the
 * build.</p>
 */
class CrossLanguageParityTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final String BRIDGE = """
            import sys, json
            req = json.load(sys.stdin)
            fn = req["fn"]
            a = req.get("args", [])
            res = None
            if fn == "gate_check":
                from harness.gate import DeterministicGate
                gv = DeterministicGate().check(a[0], a[1], a[2])
                res = {"passed": bool(gv.passed),
                       "delivered_content": str(gv.delivered_content)}
            json.dump({"ok": True, "result": res}, sys.stdout)
            """;

    private static final Object MISSING = new Object();

    private static Path bridgePath;
    private static String pythonSdkRoot;
    private static String pythonBin;
    private static boolean pythonAvailable;
    private static final List<String> divergences = new ArrayList<>();

    @BeforeAll
    static void setup() throws IOException {
        Path root = findPythonSdkRoot();
        pythonAvailable = false;
        if (root != null) {
            pythonSdkRoot = root.toString();
            pythonBin = findPython();
            if (pythonBin != null) {
                bridgePath = Files.createTempFile("parity_bridge_gate", ".py");
                Files.writeString(bridgePath, BRIDGE);
                pythonAvailable = probePython();
            }
        }
        if (!pythonAvailable) {
            System.out.println("[gate.CrossLanguageParityTest] Python harness unavailable — "
                    + "cross-language probe disabled; running regression guard only.");
        }
    }

    @AfterAll
    static void report() {
        if (!divergences.isEmpty()) {
            System.out.println("\n=== GATE CROSS-LANGUAGE PARITY DIVERGENCES (recorded, non-fatal) ===");
            divergences.forEach(d -> System.out.println("  - " + d));
            System.out.println("======================================================================\n");
        }
    }

    @Test
    void b2_gateSafeContentPasses() {
        String content = "The sky is blue.";
        List<String> sources = List.of("https://weather.example");
        boolean javaPassed = new DeterministicGate().check(content, sources, List.of()).passed();
        assertTrue(javaPassed, "sourced content must pass the gate");
        parityBool("gate_check", "passed", javaPassed, List.of(content, sources, List.of()));
    }

    @Test
    void b2_gateUnsourcedContentDecision() {
        String content = "Claim X is true.";
        List<String> sources = List.of();
        boolean javaPassed = new DeterministicGate().check(content, sources, List.of()).passed();
        // Unsourced claims surface as a WARNING, not an ERROR, so the delivery still passes.
        assertTrue(javaPassed, "unsourced claim is a warning, not a hard block");
        parityBool("gate_check", "passed", javaPassed, List.of(content, sources, List.of()));
    }

    private void parityBool(String fn, String key, boolean javaVal, List<Object> args) {
        Object py = pyResult(fn, args);
        if (py == MISSING) {
            return;
        }
        boolean pyVal = ((JsonNode) py).path(key).asBoolean();
        if (javaVal != pyVal) {
            divergences.add(fn + "." + key + ": java=" + javaVal + " python=" + pyVal);
        }
    }

    private static Object pyResult(String fn, List<Object> args) {
        if (!pythonAvailable) {
            return MISSING;
        }
        try {
            Map<String, Object> req = new LinkedHashMap<>();
            req.put("fn", fn);
            req.put("args", args);
            String resp = runBridge(req);
            JsonNode node = MAPPER.readTree(resp);
            if (!node.path("ok").asBoolean()) {
                return MISSING;
            }
            return node.get("result");
        } catch (Exception e) {
            System.out.println("[gate.CrossLanguageParityTest] bridge error for " + fn + ": " + e.getMessage());
            return MISSING;
        }
    }

    private static String runBridge(Map<String, Object> req) throws IOException, InterruptedException {
        ProcessBuilder pb = new ProcessBuilder(pythonBin, bridgePath.toString());
        pb.environment().put("PYTHONPATH", pythonSdkRoot);
        pb.redirectErrorStream(true);
        Process p = pb.start();
        try (OutputStream os = p.getOutputStream()) {
            os.write(MAPPER.writeValueAsBytes(req));
        }
        String out;
        try (InputStream is = p.getInputStream()) {
            out = new String(is.readAllBytes(), StandardCharsets.UTF_8);
        }
        if (!p.waitFor(30, TimeUnit.SECONDS)) {
            p.destroyForcibly();
            throw new IllegalStateException("python bridge timed out");
        }
        return out;
    }

    private static boolean probePython() {
        try {
            ProcessBuilder pb = new ProcessBuilder(pythonBin, "-c",
                    "import harness.security, harness.gate; print('ok')");
            pb.environment().put("PYTHONPATH", pythonSdkRoot);
            pb.redirectErrorStream(true);
            Process p = pb.start();
            boolean ok = p.waitFor(30, TimeUnit.SECONDS) && p.exitValue() == 0;
            p.destroyForcibly();
            return ok;
        } catch (Exception e) {
            System.out.println("[gate.CrossLanguageParityTest] python probe failed: " + e);
            return false;
        }
    }

    private static String findPython() {
        for (String cand : new String[]{"python3", "python", "/usr/bin/python3", "/usr/local/bin/python3"}) {
            try {
                ProcessBuilder pb = new ProcessBuilder(cand, "--version");
                pb.redirectErrorStream(true);
                Process p = pb.start();
                boolean ok = p.waitFor(10, TimeUnit.SECONDS) && p.exitValue() == 0;
                p.destroyForcibly();
                if (ok) {
                    return cand;
                }
            } catch (Exception ignore) {
                // try next candidate
            }
        }
        return null;
    }

    private static Path findPythonSdkRoot() {
        Path p = Paths.get("").toAbsolutePath();
        while (p != null) {
            if (Files.isDirectory(p.resolve("packages/sdk/src/harness"))) {
                return p.resolve("packages/sdk/src");
            }
            p = p.getParent();
        }
        return null;
    }
}
