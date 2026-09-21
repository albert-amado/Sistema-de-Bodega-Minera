---
name: edge-bridge
description: >-
  Microsoft Edge Remote Debugging and Automation Bridge. Controls, automates,
  and inspects Microsoft Edge instances launched with remote debugging port 9222.
---

# Microsoft Edge Bridge Skill

This skill allows Antigravity to connect to and control your real Microsoft Edge browser via Chrome DevTools Protocol (CDP) on port 9222.

## Launching Microsoft Edge in Debug Mode

Before connecting, Microsoft Edge must be launched with the remote debugging port enabled. In PowerShell or Command Prompt:

```powershell
# 1. Close existing Edge background processes if needed:
Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue

# 2. Launch Edge with remote debugging and custom profile:
Start-Process "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList @(
    "--remote-debugging-port=9222",
    "--user-data-dir=C:\EdgeDebugProfile",
    "--no-first-run",
    "--no-default-browser-check"
)
```

## Automating Edge via edge_controller.js

The script `.agents/skills/edge-bridge/scripts/edge_controller.js` interacts directly with Edge:

- **Check connection:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js status`

- **List tabs and version:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js info`

- **Navigate to project URL:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js navigate http://127.0.0.1:8000/`

- **Capture screenshot:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js screenshot <path_to_png> [url]`

- **Click elements:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js click "<css_selector>"`

- **Execute JavaScript:**
  `node .agents/skills/edge-bridge/scripts/edge_controller.js eval "<code_expression>"`

## MCP Configuration

The MCP server configuration is registered in `.agents/plugins/edge-bridge/mcp_config.json` and uses `chrome-devtools-mcp` pointed to `http://127.0.0.1:9222`.
