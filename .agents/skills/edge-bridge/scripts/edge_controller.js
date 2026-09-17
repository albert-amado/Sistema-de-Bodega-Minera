/**
 * edge_controller.js
 * Zero-dependency Chrome DevTools Protocol (CDP) client for Microsoft Edge.
 * Connects directly to Microsoft Edge running with --remote-debugging-port=9222.
 */

const fs = require('fs');
const path = require('path');

const CDP_HOST = '127.0.0.1';
const CDP_PORT = 9222;
const BASE_URL = `http://${CDP_HOST}:${CDP_PORT}`;

async function getVersion() {
  const res = await fetch(`${BASE_URL}/json/version`);
  if (!res.ok) throw new Error(`Failed to fetch version: ${res.statusText}`);
  return await res.json();
}

async function getTabs() {
  const res = await fetch(`${BASE_URL}/json/list`);
  if (!res.ok) throw new Error(`Failed to fetch tabs: ${res.statusText}`);
  return await res.json();
}

async function newTab(url = 'about:blank') {
  const res = await fetch(`${BASE_URL}/json/new?${encodeURIComponent(url)}`, { method: 'PUT' });
  if (!res.ok) throw new Error(`Failed to create new tab: ${res.statusText}`);
  return await res.json();
}

function cdpCall(ws, method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = Math.floor(Math.random() * 1000000);
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(`Timeout waiting for CDP response: ${method}`));
    }, 15000);

    function onMessage(event) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.id === id) {
          cleanup();
          if (msg.error) {
            reject(new Error(msg.error.message || JSON.stringify(msg.error)));
          } else {
            resolve(msg.result);
          }
        }
      } catch (err) {
        cleanup();
        reject(err);
      }
    }

    function cleanup() {
      clearTimeout(timeout);
      ws.removeEventListener('message', onMessage);
    }

    ws.addEventListener('message', onMessage);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function waitForEvent(ws, eventName, timeoutMs = 15000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      resolve(null); // Don't crash on timeout, resolve null
    }, timeoutMs);

    function onMessage(event) {
      try {
        const msg = JSON.parse(event.data);
        if (msg.method === eventName) {
          cleanup();
          resolve(msg.params);
        }
      } catch (e) {}
    }

    function cleanup() {
      clearTimeout(timeout);
      ws.removeEventListener('message', onMessage);
    }

    ws.addEventListener('message', onMessage);
  });
}

async function connectToActiveTab() {
  const tabs = await getTabs();
  const pageTab = tabs.find(t => t.type === 'page' && t.webSocketDebuggerUrl) || tabs[0];
  if (!pageTab || !pageTab.webSocketDebuggerUrl) {
    throw new Error('No active page tab found with WebSocket debugger URL.');
  }

  const ws = new WebSocket(pageTab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    ws.addEventListener('open', resolve, { once: true });
    ws.addEventListener('error', (err) => reject(new Error('WebSocket connection failed')), { once: true });
  });

  return { ws, tab: pageTab };
}

async function main() {
  const [,, command, ...args] = process.argv;

  if (!command || command === 'help') {
    console.log(`
Microsoft Edge Automation Bridge
Usage:
  node edge_controller.js status
  node edge_controller.js info
  node edge_controller.js navigate <url>
  node edge_controller.js screenshot <output.png> [url]
  node edge_controller.js eval "<javascript_code>"
  node edge_controller.js click "<css_selector>"
`);
    return;
  }

  try {
    if (command === 'status') {
      const ver = await getVersion();
      console.log(JSON.stringify({
        connected: true,
        browser: ver.Browser,
        protocolVersion: ver['Protocol-Version'],
        userAgent: ver['User-Agent'],
        webSocketDebuggerUrl: ver.webSocketDebuggerUrl
      }, null, 2));
      return;
    }

    if (command === 'info') {
      const ver = await getVersion();
      const tabs = await getTabs();
      console.log(`Edge Version: ${ver.Browser}`);
      console.log(`User Agent: ${ver['User-Agent']}`);
      console.log(`Open Tabs (${tabs.length}):`);
      tabs.forEach((t, i) => {
        console.log(`  [${i + 1}] ${t.title || 'Untitled'} - ${t.url}`);
      });
      return;
    }

    const { ws, tab } = await connectToActiveTab();

    try {
      await cdpCall(ws, 'Page.enable');
      await cdpCall(ws, 'Runtime.enable');
      await cdpCall(ws, 'DOM.enable');

      if (command === 'navigate') {
        const targetUrl = args[0];
        if (!targetUrl) throw new Error('URL required');
        console.log(`Navigating Edge tab to: ${targetUrl}...`);
        const loadPromise = waitForEvent(ws, 'Page.loadEventFired', 10000);
        await cdpCall(ws, 'Page.navigate', { url: targetUrl });
        await loadPromise;
        console.log(`Navigation completed.`);
      } else if (command === 'screenshot') {
        const outPath = args[0] || 'screenshot_edge.png';
        const targetUrl = args[1];

        if (targetUrl) {
          console.log(`Navigating to ${targetUrl}...`);
          const loadPromise = waitForEvent(ws, 'Page.loadEventFired', 10000);
          await cdpCall(ws, 'Page.navigate', { url: targetUrl });
          await loadPromise;
          // small delay to let animations settle
          await new Promise(r => setTimeout(r, 1000));
        }

        console.log(`Capturing screenshot from Microsoft Edge...`);
        const res = await cdpCall(ws, 'Page.captureScreenshot', { format: 'png' });
        const absPath = path.resolve(outPath);
        fs.mkdirSync(path.dirname(absPath), { recursive: true });
        fs.writeFileSync(absPath, Buffer.from(res.data, 'base64'));
        console.log(`Screenshot saved successfully at: ${absPath}`);
      } else if (command === 'eval') {
        const code = args.join(' ');
        const res = await cdpCall(ws, 'Runtime.evaluate', {
          expression: code,
          returnByValue: true,
          awaitPromise: true
        });
        console.log('Result:', JSON.stringify(res.result ? res.result.value : res, null, 2));
      } else if (command === 'click') {
        const selector = args[0];
        const code = `(() => {
          const el = document.querySelector(${JSON.stringify(selector)});
          if (!el) return { success: false, error: 'Element not found' };
          el.scrollIntoView({ behavior: 'instant', block: 'center' });
          el.click();
          return { success: true, tagName: el.tagName, text: el.innerText.slice(0, 50) };
        })()`;
        const res = await cdpCall(ws, 'Runtime.evaluate', {
          expression: code,
          returnByValue: true
        });
        console.log('Click result:', JSON.stringify(res.result ? res.result.value : res, null, 2));
      } else {
        throw new Error(`Unknown command: ${command}`);
      }
    } finally {
      ws.close();
    }
  } catch (err) {
    console.error(`Edge Bridge Error: ${err.message}`);
    process.exit(1);
  }
}

main();
