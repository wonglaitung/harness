package com.harness.mcp;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Duration;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.*;

/**
 * Unit tests for MCP module data classes and manager logic.
 * Does NOT require a running MCP server.
 */
class McpTypesTest {

    // ---- McpToolInfo ----

    @Test
    void mcpToolInfoFullName() {
        var info = new McpToolInfo("fs", "read_file", "Read a file", Map.of());
        assertEquals("mcp_fs_read_file", info.fullName());
    }

    @Test
    void mcpToolInfoShortDescriptionTruncates() {
        String longDesc = "A".repeat(300);
        var info = new McpToolInfo("s", "t", longDesc, Map.of());
        assertTrue(info.shortDescription().length() <= 203); // 200 + "..."
    }

    @Test
    void mcpToolInfoShortDescriptionFallback() {
        var info = new McpToolInfo("s", "t", "", Map.of());
        assertEquals("MCP tool: t", info.shortDescription());
    }

    // ---- McpToolResult ----

    @Test
    void mcpToolResultSuccess() {
        var r = McpToolResult.success("ok");
        assertTrue(r.success());
        assertFalse(r.isError());
        assertEquals("ok", r.content());
        assertEquals("ok", r.contentOrError());
    }

    @Test
    void mcpToolResultError() {
        var err = new JsonRpcResponse.JsonRpcError(-32601, "Method not found", null);
        var r = McpToolResult.error("not found", err);
        assertFalse(r.success());
        assertTrue(r.isError());
        assertEquals("not found", r.content());
        assertTrue(r.contentOrError().contains("Method not found"));
    }

    @Test
    void mcpToolResultErrorNullError() {
        var r = McpToolResult.error("msg", null);
        assertEquals("msg", r.contentOrError());
    }

    // ---- McpServerConfig ----

    @Test
    void mcpServerConfigSseFactory() {
        var cfg = McpServerConfig.sse("test", "http://localhost:3000/mcp");
        assertEquals("test", cfg.name());
        assertEquals("http://localhost:3000/mcp", cfg.url());
        assertEquals(McpServerConfig.McpTransportType.SSE, cfg.transportType());
        assertTrue(cfg.enabled());
        assertEquals(Duration.ofSeconds(30), cfg.requestTimeout());
    }

    @Test
    void mcpServerConfigWithTimeout() {
        var cfg = McpServerConfig.sse("t", "http://x")
            .withTimeout(Duration.ofSeconds(5));
        assertEquals(Duration.ofSeconds(5), cfg.requestTimeout());
    }

    @Test
    void mcpServerConfigDisabled() {
        var cfg = McpServerConfig.sse("t", "http://x").disabled();
        assertFalse(cfg.enabled());
    }

    // ---- JsonRpcRequest ----

    @Test
    void jsonRpcRequestCreate() {
        var req = JsonRpcRequest.create("test_method", Map.of("k", "v"));
        assertEquals("2.0", req.jsonrpc());
        assertNotNull(req.id());
        assertEquals("test_method", req.method());
        assertEquals("v", req.params().get("k"));
    }

    @Test
    void jsonRpcRequestInitialize() {
        var req = JsonRpcRequest.initialize();
        assertEquals("initialize", req.method());
        assertTrue(req.params().containsKey("protocolVersion"));
        assertTrue(req.params().containsKey("capabilities"));
    }

    @Test
    void jsonRpcRequestListTools() {
        var req = JsonRpcRequest.listTools();
        assertEquals("tools/list", req.method());
    }

    @Test
    void jsonRpcRequestCallTool() {
        var req = JsonRpcRequest.callTool("read", Map.of("path", "/tmp"));
        assertEquals("tools/call", req.method());
        assertEquals("read", req.params().get("name"));
    }

    @Test
    void jsonRpcRequestPing() {
        var req = JsonRpcRequest.ping();
        assertEquals("ping", req.method());
    }

    // ---- JsonRpcResponse ----

    @Test
    void jsonRpcResponseSuccess() {
        var resp = new JsonRpcResponse("2.0", "1", Map.of("key", "val"), null);
        assertTrue(resp.isSuccess());
        assertFalse(resp.hasError());
        assertEquals("val", resp.resultAsMap().get("key"));
        assertNull(resp.errorMessage());
    }

    @Test
    void jsonRpcResponseError() {
        var err = new JsonRpcResponse.JsonRpcError(-32600, "bad request", null);
        var resp = new JsonRpcResponse("2.0", "1", null, err);
        assertFalse(resp.isSuccess());
        assertTrue(resp.hasError());
        assertEquals("bad request", resp.errorMessage());
    }

    @Test
    void jsonRpcResponseResultAsList() {
        var resp = new JsonRpcResponse("2.0", "1", List.of("a", "b"), null);
        assertEquals(2, resp.resultAsList().size());
    }

    @Test
    void jsonRpcResponseResultAsMapEmpty() {
        var resp = new JsonRpcResponse("2.0", "1", "not a map", null);
        assertTrue(resp.resultAsMap().isEmpty());
    }

    // ---- JsonRpcError standard codes ----

    @Test
    void jsonRpcErrorStandardCodes() {
        var err = new JsonRpcResponse.JsonRpcError(-32603, "Internal error", null);
        assertTrue(err.isStandardError());
        assertTrue(err.description().contains("Internal error"));

        var err2 = new JsonRpcResponse.JsonRpcError(-999, "custom", null);
        assertFalse(err2.isStandardError());
    }

    // ---- McpManager (no real server) ----

    @Test
    void mcpManagerRegisterAndGet() {
        McpManager mgr = new McpManager();
        var cfg = McpServerConfig.sse("test-server", "http://localhost:9999/mcp");
        mgr.registerServer(cfg);

        assertEquals(1, mgr.getRegisteredServers().size());
        assertEquals("test-server", mgr.getRegisteredServers().get(0));
        assertNotNull(mgr.getConfig("test-server"));
    }

    @Test
    void mcpManagerConnectFailsGracefully() {
        McpManager mgr = new McpManager();
        mgr.registerServer(McpServerConfig.sse("no-server", "http://localhost:1/mcp"));

        boolean result = mgr.connect("nonexistent");
        assertFalse(result);

        assertFalse(mgr.isConnected("nonexistent"));
        assertTrue(mgr.getConnectedServers().isEmpty());
    }

    @Test
    void mcpManagerDisconnect() {
        McpManager mgr = new McpManager();
        mgr.registerServer(McpServerConfig.sse("s", "http://x"));
        mgr.disconnect("s");
        assertFalse(mgr.isConnected("s"));
    }

    @Test
    void mcpManagerGetStats() {
        McpManager mgr = new McpManager();
        mgr.registerServer(McpServerConfig.sse("a", "http://a"));
        mgr.registerServer(McpServerConfig.sse("b", "http://b"));

        var stats = mgr.getStats();
        assertEquals(2, stats.get("registeredServers"));
        assertEquals(0, stats.get("connectedServers"));
        assertEquals(0, stats.get("totalTools"));
    }

    @Test
    void mcpManagerGetToolInfoNotFound() {
        McpManager mgr = new McpManager();
        assertNull(mgr.getToolInfo("nonexistent_tool"));
    }

    @Test
    void mcpManagerDisabledServerSkipsConnect() {
        McpManager mgr = new McpManager();
        var cfg = McpServerConfig.sse("disabled", "http://x").disabled();
        mgr.registerServer(cfg);

        boolean result = mgr.connect("disabled");
        assertFalse(result);
    }

    @Test
    void mcpManagerStatusMap() {
        McpManager mgr = new McpManager();
        mgr.registerServer(McpServerConfig.sse("s", "http://x"));
        var status = mgr.getStatus();
        assertEquals(1, status.size());
        assertTrue(status.get("s").contains("disconnected"));
    }

    // ---- McpToolWrapper (without real server) ----

    @Test
    void mcpToolWrapperValidateMissingRequired() {
        McpClient client = new McpClient("http://localhost:1");
        var info = new McpToolInfo("s", "t", "desc", Map.of(
            "required", List.of("path", "mode")
        ));
        var wrapper = new McpToolWrapper(client, info);

        var result = wrapper.validate(Map.of("path", "/tmp"));
        assertFalse(result.isValid());
        assertTrue(result.error().contains("mode"));
    }

    @Test
    void mcpToolWrapperValidateAllPresent() {
        McpClient client = new McpClient("http://localhost:1");
        var info = new McpToolInfo("s", "t", "desc", Map.of(
            "required", List.of("path")
        ));
        var wrapper = new McpToolWrapper(client, info);

        var result = wrapper.validate(Map.of("path", "/tmp"));
        assertTrue(result.isValid());
    }

    @Test
    void mcpToolWrapperValidateNoSchema() {
        McpClient client = new McpClient("http://localhost:1");
        var info = new McpToolInfo("s", "t", "desc", Map.of());
        var wrapper = new McpToolWrapper(client, info);

        assertTrue(wrapper.validate(Map.of()).isValid());
    }

    @Test
    void mcpToolWrapperMetadata() {
        McpClient client = new McpClient("http://localhost:1");
        var info = new McpToolInfo("fs", "read", "Read file", Map.of());
        var wrapper = new McpToolWrapper(client, info);

        assertEquals("mcp_fs_read", wrapper.name());
        assertEquals("Read file", wrapper.description());
        assertTrue(wrapper.isDangerous());
        assertEquals("fs", wrapper.serverName());
        assertEquals("read", wrapper.originalName());
        assertSame(client, wrapper.client());
    }
}
