# MCP Server Tutorial: Step-by-Step Implementation Guide

This guide walks you through converting your local MCP server to a production HTTP-based server. Each step is small, testable, and includes concept explanations.

---

## 📚 Table of Contents

- [Part 0: Understanding Current Setup](#part-0-understanding-current-setup)
- [Part 1: Understanding MCP Transports](#part-1-understanding-mcp-transports)
- [Part 2: Test Current Setup](#part-2-test-current-setup)
- [Part 3: Add HTTP Transport (No Auth)](#part-3-add-http-transport-no-auth)
- [Part 4: Convert REST Endpoints to Custom Routes](#part-4-convert-rest-endpoints-to-custom-routes)
- [Part 5: Test HTTP MCP Server Locally](#part-5-test-http-mcp-server-locally)
- [Part 6: Setup GitHub OAuth (Optional)](#part-6-setup-github-oauth-optional)
- [Part 7: Add Authentication to MCP Server](#part-7-add-authentication-to-mcp-server)
- [Part 8: Deploy to Render](#part-8-deploy-to-render)
- [Part 9: Connect Remote MCP Clients](#part-9-connect-remote-mcp-clients)
- [Troubleshooting](#troubleshooting)

---

## Part 0: Understanding Current Setup

### 🎯 What You Have Now

Your `main.py` runs **two separate servers** in one file:

```
┌─────────────────────────────────────┐
│         main.py                     │
├─────────────────────────────────────┤
│                                     │
│  1. MCP Server (FastMCP)            │
│     - weather_tool()                │
│     - Uses: stdio transport         │
│     - Works: Local only             │
│     - Client: Claude Desktop        │
│                                     │
│  2. FastAPI Server                  │
│     - /api/weather endpoint         │
│     - Uses: HTTP protocol           │
│     - Works: Remote (Render)        │
│     - Client: Browsers, bots        │
│                                     │
└─────────────────────────────────────┘
```

### 📖 Key Concepts

**MCP (Model Context Protocol)**: Protocol that lets AI assistants call tools/functions on servers. Think of it like an API, but designed specifically for AI agents.

**Transport**: How client and server communicate.
- **stdio**: Process spawns on same machine, talks via stdin/stdout
- **HTTP**: Network connection, client POSTs to server URL

**FastMCP**: Python library that makes building MCP servers easy

**Current Problem**: MCP tool only works locally (stdio). Remote clients can't connect.

**Goal**: Enable HTTP transport so any remote MCP client can connect.

### ✅ Checkpoint

Before proceeding, verify you understand:
- [ ] What MCP is (protocol for AI to call tools)
- [ ] Difference between stdio (local) and HTTP (remote)
- [ ] Current setup has MCP tool + REST API
- [ ] You want remote clients to access MCP tool

---

## Part 1: Understanding MCP Transports

### 📖 Concept: How MCP Clients Connect

#### Stdio Transport (Current)

```
┌──────────────┐                    ┌──────────────┐
│ Claude       │                    │ MCP Server   │
│ Desktop      │  Spawns Process    │ (main.py)    │
│              ├───────────────────>│              │
│ (Client)     │  stdin/stdout      │ (Server)     │
│              │<───────────────────│              │
└──────────────┘                    └──────────────┘
     Same computer
```

**How it works:**
1. Claude Desktop reads your config
2. Runs: `python main.py`
3. Talks to it via stdin/stdout (like terminal input/output)
4. One client = one process

**Limitations:**
- Client must be on same machine
- Client must have Python installed
- Can't share server across network
- New process per client session

#### HTTP Transport (Goal)

```
┌──────────────┐                    ┌──────────────┐
│ Any MCP      │                    │ MCP Server   │
│ Client       │  HTTP POST         │ on Render    │
│              ├───────────────────>│              │
│ (Anywhere)   │  to /mcp endpoint  │ (Always on)  │
│              │<───────────────────│              │
└──────────────┘                    └──────────────┘
     Internet connection
```

**How it works:**
1. MCP server runs on cloud (Render)
2. Client makes HTTP POST to `https://your-app.com/mcp`
3. Server responds with tool results
4. Multiple clients share one server

**Benefits:**
- Works from anywhere
- No local installation needed
- One server, many clients
- Can add authentication

### 🔍 Example: Weather Tool Request Flow

**Stdio (current):**
```
User asks: "What's weather in London?"
  ↓
Claude Desktop calls: weather_tool(city="London")
  ↓
Sends to stdin of python main.py process
  ↓
Server returns: {"temperature": 15, ...}
  ↓
Reads from stdout
  ↓
Claude shows: "It's 15°C in London"
```

**HTTP (goal):**
```
User asks: "What's weather in London?"
  ↓
Claude sends POST https://your-app.com/mcp
  Body: {tool: "weather_tool", args: {city: "London"}}
  ↓
Server processes request
  ↓
Server returns: HTTP 200, body: {"temperature": 15, ...}
  ↓
Claude shows: "It's 15°C in London"
```

### ✅ Checkpoint

Before proceeding:
- [ ] Understand stdio = local process spawn
- [ ] Understand HTTP = network POST requests
- [ ] Know why HTTP better for production (remote access)
- [ ] Understand one HTTP server serves many clients

---

## Part 2: Test Current Setup

### 🎯 Goal
Verify your current code works before making changes.

### 📝 Steps

**Step 2.1: Check environment variables**

```bash
cat .env
```

Should see:
```
OPENWEATHER_API=your_api_key_here
BASE_URL=https://api.openweathermap.org/data/2.5/weather
```

If missing, create `.env` file with your OpenWeatherMap API key.

**Step 2.2: Start server**

```bash
python main.py
```

Should see:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Step 2.3: Test REST API**

Open new terminal:
```bash
curl "http://localhost:8080/api/weather?city=London"
```

Should get JSON response with weather data.

**Step 2.4: Test MCP tool (if you have Claude Desktop)**

This currently only works with stdio config in Claude Desktop. Skip if you don't have it configured.

### ✅ Checkpoint

- [ ] Server starts without errors
- [ ] REST API returns weather data
- [ ] Ready to add HTTP transport

---

## Part 3: Add HTTP Transport (No Auth)

### 🎯 Goal
Make MCP server accessible via HTTP without breaking existing code.

### 📖 What We'll Do

Instead of running only FastAPI with `uvicorn.run(app)`, we'll run FastMCP with HTTP transport using `mcp.run(transport="http")`.

This creates an endpoint at `/mcp` where MCP clients can connect.

### 📝 Changes to `main.py`

**Step 3.1: Backup current file**

```bash
cp main.py main.py.backup
```

**Step 3.2: Modify the `if __name__ == "__main__"` block**

Find this code (around line 116):

```python
if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    # Run FastAPI server (MCP tool available via stdio locally)
    uvicorn.run(app, host="0.0.0.0", port=port)
```

Replace with:

```python
if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    # Run MCP server with HTTP transport
    # This creates /mcp endpoint for remote clients
    mcp.run(transport="http", host="0.0.0.0", port=port)
```

**Step 3.3: Remove uvicorn import (now unused)**

Find line 5:
```python
import dotenv, os, requests, uvicorn
```

Change to:
```python
import dotenv, os, requests
```

### 📖 What Changed?

**Before:**
- `uvicorn.run(app)` → Runs only FastAPI
- MCP available via stdio only
- REST endpoints work

**After:**
- `mcp.run(transport="http")` → Runs MCP server
- MCP available via HTTP at `/mcp`
- REST endpoints currently **broken** (we'll fix in Part 4)

### 🧪 Test It

**Step 3.4: Start server**

```bash
python main.py
```

Should see different output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

**Step 3.5: Check MCP endpoint exists**

```bash
curl -X POST http://localhost:8080/mcp
```

You'll get an error response (because we sent wrong format), but **that's okay**! The important part is the endpoint responds. If you get "404 Not Found", something's wrong.

**Step 3.6: Notice REST API is broken**

```bash
curl "http://localhost:8080/api/weather?city=London"
```

Returns 404 Not Found. **This is expected!** We'll fix it in Part 4.

### 📖 Why REST API Broke?

When you run `mcp.run(transport="http")`, it creates an MCP HTTP server. The FastAPI app (`app`) is no longer being run, so its routes (`/api/weather`, `/health`) don't exist.

**Solution:** Use FastMCP custom routes to add REST endpoints back.

### ✅ Checkpoint

- [ ] Changed to `mcp.run(transport="http")`
- [ ] Server starts successfully
- [ ] `/mcp` endpoint exists (even if errors)
- [ ] REST API returns 404 (expected)
- [ ] Understand why: FastAPI app not running anymore

---

## Part 4: Convert REST Endpoints to Custom Routes

### 🎯 Goal
Restore REST API by converting FastAPI routes to FastMCP custom routes.

### 📖 Concept: Custom Routes

FastMCP custom routes let you add regular HTTP endpoints alongside the `/mcp` endpoint.

```
Same Server:
├── /mcp              → MCP protocol endpoint
├── /api/weather      → REST API (custom route)
├── /health           → Health check (custom route)
└── /                 → Root info (custom route)
```

Custom routes use Starlette (FastAPI's foundation), so syntax is similar.

### 📝 Changes to `main.py`

**Step 4.1: Add imports for custom routes**

Add to top of file (after existing imports):

```python
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
```

Your imports section should now look like:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from typing import Optional
import dotenv, os, requests
```

**Step 4.2: Remove FastAPI app code**

Delete lines 75-114 (the entire FastAPI section):

```python
# FastAPI app - for REST API
app = FastAPI(title="Weather MCP Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "service": "Weather MCP Server",
        "version": "1.0.0",
        "mcp_tool": "weather_tool",
        "rest_endpoint": "/api/weather?city=London"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

# REST endpoint - for chatbots
@app.get("/api/weather")
def weather_endpoint(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    """Get current weather data via REST API"""
    try:
        return get_weather_data(city, lat, lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.HTTPError:
        raise HTTPException(status_code=404, detail="Location not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 4.3: Add custom routes instead**

After the `weather_tool` function (around line 74), add:

```python
# Custom HTTP routes - for REST API compatibility
# These work alongside /mcp endpoint

@mcp.custom_route("/", methods=["GET"])
async def root(request: Request) -> JSONResponse:
    """Root endpoint - server info"""
    return JSONResponse({
        "service": "Weather MCP Server",
        "version": "1.0.0",
        "mcp_endpoint": "/mcp",
        "rest_endpoint": "/api/weather?city=London",
        "health_check": "/health"
    })

@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "healthy"})

@mcp.custom_route("/api/weather", methods=["GET"])
async def weather_endpoint(request: Request) -> JSONResponse:
    """REST API endpoint for weather data"""
    try:
        # Get query parameters
        city = request.query_params.get("city")
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        
        # Convert lat/lon to float if provided
        if lat:
            lat = float(lat)
        if lon:
            lon = float(lon)
        
        # Call core weather function
        data = get_weather_data(city, lat, lon)
        return JSONResponse(data)
        
    except ValueError as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=400
        )
    except requests.exceptions.HTTPError:
        return JSONResponse(
            {"error": "Location not found"},
            status_code=404
        )
    except Exception as e:
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )
```

**Step 4.4: Remove unused imports**

Since we removed FastAPI, delete these imports:

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
```

### 📖 What Changed?

**Before:**
```python
@app.get("/api/weather")  # FastAPI route
def weather_endpoint(...):
```

**After:**
```python
@mcp.custom_route("/api/weather", methods=["GET"])  # MCP custom route
async def weather_endpoint(request: Request) -> JSONResponse:
```

**Key Differences:**
1. `@mcp.custom_route()` instead of `@app.get()`
2. Functions must be `async`
3. First parameter is `request: Request`
4. Query params accessed via `request.query_params.get()`
5. Return `JSONResponse()` instead of plain dict
6. Manual error handling with `JSONResponse(status_code=...)`

### 🧪 Test It

**Step 4.5: Restart server**

```bash
python main.py
```

**Step 4.6: Test REST API is restored**

```bash
curl "http://localhost:8080/api/weather?city=London"
```

Should return weather data (working again!).

**Step 4.7: Test other endpoints**

```bash
curl http://localhost:8080/
curl http://localhost:8080/health
```

Both should work.

**Step 4.8: Verify MCP endpoint still exists**

```bash
curl -X POST http://localhost:8080/mcp
```

Still responds (with error about format, which is fine).

### ✅ Checkpoint

- [ ] Removed FastAPI app code
- [ ] Added custom routes
- [ ] REST API works again (`/api/weather`)
- [ ] Health endpoint works (`/health`)
- [ ] MCP endpoint exists (`/mcp`)
- [ ] Understand custom routes run alongside MCP

---

## Part 5: Test HTTP MCP Server Locally

### 🎯 Goal
Verify MCP tool works via HTTP transport before adding auth or deploying.

### 📖 How to Test MCP Endpoints

MCP clients send specific JSON-RPC messages. We can simulate this with curl or use MCP Inspector tool.

### 📝 Option A: Quick Test with Curl

**Step 5.1: Test MCP initialization**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {
        "name": "test-client",
        "version": "1.0.0"
      }
    }
  }'
```

Should return server capabilities (long JSON response).

**Step 5.2: Test listing tools**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
```

Should return:
```json
{
  "tools": [
    {
      "name": "weather_tool",
      "description": "Get current weather data for a location.",
      ...
    }
  ]
}
```

**Step 5.3: Test calling weather tool**

```bash
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "weather_tool",
      "arguments": {
        "city": "London"
      }
    }
  }'
```

Should return weather data.

### 📝 Option B: Use MCP Inspector (Recommended)

**Step 5.4: Open MCP Inspector**

Visit: https://inspector.modelcontextprotocol.io/

**Step 5.5: Connect to your local server**

1. In MCP Inspector, select "HTTP" transport
2. Enter URL: `http://localhost:8080/mcp`
3. Click "Connect"

**Step 5.6: Explore your server**

- View available tools (should see `weather_tool`)
- Click on `weather_tool` to see parameters
- Call it with `city: "London"`
- See weather results

### 📖 Understanding MCP Protocol

MCP uses JSON-RPC 2.0 over HTTP:

```
Client                          Server
  │                               │
  ├─ POST /mcp ─────────────────→ │
  │  method: initialize           │
  │                               │
  │ ←─────────── capabilities ────┤
  │                               │
  ├─ POST /mcp ─────────────────→ │
  │  method: tools/list           │
  │                               │
  │ ←────── [weather_tool] ───────┤
  │                               │
  ├─ POST /mcp ─────────────────→ │
  │  method: tools/call           │
  │  name: weather_tool           │
  │  args: {city: "London"}       │
  │                               │
  │ ←────── {temp: 15, ...} ──────┤
```

### ✅ Checkpoint

- [ ] Can POST to `/mcp` endpoint
- [ ] `tools/list` returns `weather_tool`
- [ ] `tools/call` returns weather data
- [ ] Used MCP Inspector OR curl successfully
- [ ] Understand MCP uses JSON-RPC over HTTP

---

## Part 6: Setup GitHub OAuth (Optional)

### 🎯 Goal
Create GitHub OAuth app for authentication. **Skip if you want to deploy without auth first.**

### 📖 Why Authentication?

For public production servers:
- Prevents abuse (random people spamming your API)
- Tracks usage per user
- Free tier services often require auth
- Standard security practice

GitHub OAuth is easiest:
- Free
- No extra services needed
- FastMCP has built-in support
- Users trust GitHub login

### 📝 Steps

**Step 6.1: Go to GitHub OAuth Apps**

Visit: https://github.com/settings/developers

Click "OAuth Apps" → "New OAuth App"

**Step 6.2: Fill in application details**

```
Application name: Weather MCP Server
Homepage URL: https://weather-mcp.onrender.com (use your Render URL)
Application description: Weather data via MCP
Authorization callback URL: https://weather-mcp.onrender.com/oauth/callback
```

**Important:** If you don't have Render URL yet:
- Use placeholder: `http://localhost:8080/oauth/callback` 
- Update later after deploying

**Step 6.3: Register application**

Click "Register application"

**Step 6.4: Generate client secret**

Click "Generate a new client secret"

**Step 6.5: Save credentials**

You'll see:
- **Client ID**: `Ov23li...` (visible always)
- **Client Secret**: `abc123...` (shown once, copy now!)

**Save these somewhere safe!** You'll need them in Part 7.

**Step 6.6: Update callback URL after deploy**

After deploying to Render (Part 8), come back and update:
```
Authorization callback URL: https://your-actual-app.onrender.com/oauth/callback
```

### ✅ Checkpoint

- [ ] Created GitHub OAuth App
- [ ] Saved Client ID
- [ ] Saved Client Secret
- [ ] Know to update callback URL after deploy
- [ ] (Or decided to skip auth for now)

---

## Part 7: Add Authentication to MCP Server

### 🎯 Goal
Protect your MCP server with GitHub OAuth. **Skip if you skipped Part 6.**

### 📖 How OAuth Works

```
1. Client connects to /mcp
   ↓
2. Server: "Need auth, go to GitHub"
   ↓
3. User logs in to GitHub
   ↓
4. GitHub redirects back with code
   ↓
5. Server exchanges code for token
   ↓
6. Client includes token in future requests
   ↓
7. Server validates token, allows access
```

### 📝 Changes to `main.py`

**Step 7.1: Add GitHub provider import**

Add to top of file:

```python
from fastmcp.server.auth.providers.github import GitHubProvider
```

**Step 7.2: Setup auth provider**

Add after `dotenv.load_dotenv()` (around line 7):

```python
dotenv.load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API')
BASE_URL = os.getenv('BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')

# GitHub OAuth authentication (optional - disabled if env vars not set)
auth = None
github_client_id = os.getenv('GITHUB_CLIENT_ID')
github_client_secret = os.getenv('GITHUB_CLIENT_SECRET')
base_url = os.getenv('BASE_URL_OAUTH')  # Your app URL for OAuth redirects

if github_client_id and github_client_secret and base_url:
    auth = GitHubProvider(
        client_id=github_client_id,
        client_secret=github_client_secret,
        base_url=base_url
    )
    print(f"✓ GitHub OAuth enabled for {base_url}")
else:
    print("⚠ GitHub OAuth disabled (env vars not set)")
```

**Step 7.3: Pass auth to MCP server**

Change line 12:

```python
# Before
mcp = FastMCP(name='weather_mcp')

# After
mcp = FastMCP(name='weather_mcp', auth=auth)
```

**Step 7.4: Update .env file**

Add to `.env`:

```bash
# GitHub OAuth (leave empty to disable auth)
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
BASE_URL_OAUTH=http://localhost:8080
```

Replace `your_client_id_here` and `your_client_secret_here` with values from Part 6.

For production, you'll change `BASE_URL_OAUTH` to your Render URL.

### 🧪 Test It

**Step 7.5: Test without auth (empty env vars)**

Remove credentials from `.env`:
```bash
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

Restart server:
```bash
python main.py
```

Should see:
```
⚠ GitHub OAuth disabled (env vars not set)
```

MCP works without auth.

**Step 7.6: Test with auth enabled**

Add credentials back to `.env`, restart server.

Should see:
```
✓ GitHub OAuth enabled for http://localhost:8080
```

Try MCP Inspector:
1. Connect to `http://localhost:8080/mcp`
2. Should get auth challenge
3. Click "Login with GitHub"
4. Authorize app
5. Should connect successfully

**Step 7.7: Test REST API still works**

```bash
curl "http://localhost:8080/api/weather?city=London"
```

Should work (custom routes not protected by auth, only `/mcp` endpoint).

### 📖 Auth is Optional

Your code now supports both modes:
- **With env vars**: Auth required for `/mcp`
- **Without env vars**: `/mcp` open to anyone

This lets you:
- Test locally without auth
- Deploy to production with auth
- Gradually migrate

### ✅ Checkpoint

- [ ] Added GitHub OAuth provider
- [ ] MCP server accepts `auth` parameter
- [ ] Works without auth (env vars empty)
- [ ] Works with auth (env vars set)
- [ ] REST API unaffected
- [ ] Tested with MCP Inspector

---

## Part 8: Deploy to Render

### 🎯 Goal
Deploy your HTTP MCP server to Render so remote clients can connect.

### 📝 Steps

**Step 8.1: Update render.yaml**

Open `render.yaml`, add OAuth env vars:

```yaml
services:
  - type: web
    name: weather-mcp
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: OPENWEATHER_API
        sync: false
      - key: BASE_URL
        value: https://api.openweathermap.org/data/2.5/weather
      - key: GITHUB_CLIENT_ID
        sync: false
      - key: GITHUB_CLIENT_SECRET
        sync: false
      - key: BASE_URL_OAUTH
        value: https://weather-mcp.onrender.com
```

**Note:** Change `weather-mcp.onrender.com` to your actual Render app name.

**Step 8.2: Commit changes**

```bash
git add main.py render.yaml MCP_TUTORIAL.md
git commit -m "Add HTTP transport and GitHub OAuth to MCP server"
git push
```

**Step 8.3: Deploy to Render**

If you haven't connected Render yet:
1. Go to https://render.com
2. Connect GitHub repo
3. Render auto-detects `render.yaml`
4. Click "Apply"

If already connected, push triggers auto-deploy.

**Step 8.4: Add environment variables in Render dashboard**

Go to your service → Environment:

Add:
```
OPENWEATHER_API = your_api_key
GITHUB_CLIENT_ID = your_client_id (from Part 6)
GITHUB_CLIENT_SECRET = your_client_secret (from Part 6)
```

`BASE_URL` and `BASE_URL_OAUTH` already set in `render.yaml`.

**Step 8.5: Wait for deploy**

Check logs in Render dashboard. Should see:
```
✓ GitHub OAuth enabled for https://your-app.onrender.com
INFO:     Uvicorn running on http://0.0.0.0:10000
```

**Step 8.6: Test deployed endpoints**

Replace `YOUR_APP` with your Render app name:

```bash
# Health check
curl https://YOUR_APP.onrender.com/health

# REST API
curl "https://YOUR_APP.onrender.com/api/weather?city=London"

# MCP endpoint exists
curl -X POST https://YOUR_APP.onrender.com/mcp
```

All should work.

### ✅ Checkpoint

- [ ] Updated `render.yaml` with OAuth env vars
- [ ] Committed and pushed code
- [ ] Added env vars in Render dashboard
- [ ] Deploy succeeded
- [ ] Health endpoint responds
- [ ] REST API works remotely
- [ ] MCP endpoint exists remotely

---

## Part 9: Connect Remote MCP Clients

### 🎯 Goal
Connect Claude Desktop (or other MCP clients) to your production server.

### 📝 For Claude Desktop

**Step 9.1: Find Claude config file**

**macOS:**
```bash
code ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

**Windows:**
```bash
code %APPDATA%\Claude\claude_desktop_config.json
```

**Step 9.2: Add HTTP server config**

```json
{
  "mcpServers": {
    "weather": {
      "transport": {
        "type": "http",
        "url": "https://YOUR_APP.onrender.com/mcp"
      }
    }
  }
}
```

Replace `YOUR_APP` with your Render app name.

**Step 9.3: Restart Claude Desktop**

Fully quit and restart Claude Desktop app.

**Step 9.4: Test connection**

In Claude Desktop, ask:
```
What tools do you have available?
```

Should mention `weather_tool`.

Then ask:
```
What's the weather in London?
```

Should call your remote MCP server and return weather data!

**Step 9.5: First-time OAuth (if auth enabled)**

If you enabled GitHub OAuth:
1. First request triggers OAuth flow
2. Browser opens GitHub login
3. Authorize app
4. Returns to Claude
5. Future requests use cached token

### 📝 For Other MCP Clients

Any MCP client can connect using:
```
Transport: HTTP
URL: https://YOUR_APP.onrender.com/mcp
```

### 📖 What Just Happened?

```
┌─────────────────┐         Internet          ┌──────────────┐
│ Claude Desktop  │                            │  Your MCP    │
│ (Your laptop)   │ ─── POST to /mcp ───────> │  Server      │
│                 │ <── Weather data ──────── │  (Render)    │
└─────────────────┘                            └──────────────┘
                                                      │
                                                      ▼
                                               ┌──────────────┐
                                               │ OpenWeather  │
                                               │     API      │
                                               └──────────────┘
```

Your MCP tool now works remotely!

### ✅ Checkpoint

- [ ] Updated Claude Desktop config to HTTP transport
- [ ] Claude can list `weather_tool`
- [ ] Claude can call weather tool remotely
- [ ] OAuth login worked (if enabled)
- [ ] Understand client → server → weather API flow

---

## 🎉 Congratulations!

You've converted your local MCP server to a production HTTP server!

### What You Learned

**MCP Concepts:**
- ✅ MCP transports (stdio vs HTTP)
- ✅ MCP protocol (JSON-RPC over HTTP)
- ✅ Tools, resources, and prompts
- ✅ Client-server communication

**FastMCP Features:**
- ✅ HTTP transport configuration
- ✅ Custom routes for REST APIs
- ✅ OAuth authentication with providers
- ✅ Production deployment patterns

**Architecture:**
- ✅ Single server for MCP + REST
- ✅ Shared business logic (`get_weather_data`)
- ✅ Multiple client types (MCP clients + HTTP clients)

### Next Steps

**Enhance Your Server:**
- Add more tools (forecast, alerts, air quality)
- Add rate limiting
- Add caching for API responses
- Monitor usage with logging

**Learn More:**
- FastMCP docs: https://gofastmcp.com
- MCP spec: https://modelcontextprotocol.io
- Build more complex tools
- Create multi-tool servers

### Your Production Server URLs

After completing all parts:

```
MCP Endpoint:  https://YOUR_APP.onrender.com/mcp
REST API:      https://YOUR_APP.onrender.com/api/weather
Health Check:  https://YOUR_APP.onrender.com/health
Server Info:   https://YOUR_APP.onrender.com/
```

---

## Troubleshooting

### Issue: "Module fastmcp not found"

```bash
pip install -r requirements.txt
```

### Issue: "401 Unauthorized" when testing MCP

Auth is enabled but you're not sending token. Either:
- Test with MCP Inspector (handles OAuth)
- Disable auth (remove env vars)

### Issue: REST API returns 404

Did you convert to custom routes (Part 4)?

### Issue: "Application startup failed" on Render

Check Render logs. Common causes:
- Missing env vars
- Wrong Python version (need 3.10+)
- Syntax errors in code

### Issue: OAuth callback fails

Check:
- GitHub OAuth app callback URL matches Render URL
- `BASE_URL_OAUTH` env var correct
- HTTPS (not HTTP) in production

### Issue: Render server sleeps (free tier)

Free tier spins down after 15min inactivity. First request takes 30sec to wake. Upgrade to paid tier for always-on.

### Still Stuck?

Check:
1. Render logs for errors
2. Network tab in browser for HTTP errors
3. MCP Inspector for protocol issues
4. Compare your code to `main.py.backup`

---

## Appendix: Complete File Structure

After all parts complete:

```
weather_mcp/
├── main.py                    # HTTP MCP server with custom routes
├── main.py.backup             # Original file (backup)
├── requirements.txt           # Dependencies (unchanged)
├── render.yaml                # Render config with OAuth vars
├── .env                       # Local env vars (not committed)
├── MCP_TUTORIAL.md            # This file
├── CLAUDE.md                  # Architecture docs
└── README.md                  # Project readme
```

### Key Code Patterns

**MCP Tool Definition:**
```python
@mcp.tool()
def your_tool(param: str) -> dict:
    """Tool description"""
    return {"result": "data"}
```

**Custom Route:**
```python
@mcp.custom_route("/path", methods=["GET"])
async def handler(request: Request) -> JSONResponse:
    return JSONResponse({"key": "value"})
```

**Run HTTP Server:**
```python
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)
```

**Auth Setup:**
```python
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id=os.getenv("GITHUB_CLIENT_ID"),
    client_secret=os.getenv("GITHUB_CLIENT_SECRET"),
    base_url=os.getenv("BASE_URL_OAUTH")
)

mcp = FastMCP(name="server", auth=auth)
```
