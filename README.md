# Weather MCP Server

Production-ready weather server with both MCP and REST API support.

## Features
- **MCP Protocol**: For AI assistants (Claude Desktop, Cursor, etc.)
- **REST API**: For chatbots and web apps
- OpenWeatherMap API integration
- Returns: temperature, humidity, rain, wind, conditions

## Endpoints

### MCP Endpoint (for AI assistants)
```
https://your-server.com/sse
```

### REST API (for chatbots)
```
GET https://your-server.com/api/weather?city=London
GET https://your-server.com/api/weather?lat=51.5074&lon=-0.1278
```

**Response:**
```json
{
  "temperature": 15.2,
  "humidity": 72,
  "rain_mm_per_hour": 0,
  "is_raining": false,
  "wind_speed": 3.5,
  "weather_condition": "Clouds",
  "weather_description": "overcast clouds",
  "clouds_percent": 90,
  "location": "London",
  "country": "GB"
}
```

## Deployment

### Render (Free)
1. Fork/clone this repo
2. Go to [render.com](https://render.com)
3. New Web Service → Connect GitHub repo
4. Add environment variable:
   - `OPENWEATHER_API`: your API key
5. Deploy (auto-detects `render.yaml`)

### Local Development
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Server runs on `http://localhost:8080`

## Integration

### With LiteLLM/LangChain Chatbot
```python
import requests

def get_weather(city: str):
    response = requests.get(
        "https://your-server.com/api/weather",
        params={"city": city}
    )
    return response.json()

# Use in your chatbot
weather = get_weather("London")
```

### With Claude Desktop
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "weather": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/client", "https://your-server.com/sse"]
    }
  }
}
```

## Environment Variables
- `OPENWEATHER_API`: Your OpenWeatherMap API key (required)
- `BASE_URL`: API endpoint (default: https://api.openweathermap.org/data/2.5/weather)
- `PORT`: Server port (default: 8080)
