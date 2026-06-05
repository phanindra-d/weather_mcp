from fastmcp import FastMCP
from typing import Optional
import dotenv, os, requests

mcp=FastMCP(name='weather_mcp')
dotenv.load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API')
BASE_URL = os.getenv('BASE_URL')


@mcp.tool
def weather_tool(
    city: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None
    ) -> dict:
    try:
        if city:
            params = {'q': city}
        elif latitude is not None and longitude is not None:
            params = {'lat': latitude, 'lon':longitude}  
        else:
            raise ValueError('Provide either city OR latitude and longitude')    
        params.update({
            'appid':API_KEY,
            'units': "metric"
        })  
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        # Actual measured rain
        rain_mm = 0
        if "rain" in data and "1h" in data["rain"]:
            rain_mm = data["rain"]["1h"]
        elif "rain" in data and "3h" in data["rain"]:
            rain_mm = data["rain"]["3h"] / 3

        # Rain status based on weather condition
        weather_main = data['weather'][0]['main'].lower()
        is_raining = weather_main in ['rain', 'drizzle', 'thunderstorm']    

        return {
            "temperature": data['main']['temp'],
            "humidity": data['main']['humidity'],
            "rain_mm_per_hour": rain_mm,
            "is_raining": is_raining,
            "wind_speed": data['wind']['speed'],
            "weather_condition": data['weather'][0]['main'],
            "weather_description": data['weather'][0]['description'],
            "clouds_percent": data['clouds']['all']
        }    
    except Exception as e:
        return {'Error': str(e)}
    

if __name__ == "__main__":
    import sys
    # Support both local (stdio) and remote (SSE) transports
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    mcp.run(transport=transport)    