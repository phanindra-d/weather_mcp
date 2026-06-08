from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import dotenv, os, requests, uvicorn

dotenv.load_dotenv()
API_KEY = os.getenv('OPENWEATHER_API')
BASE_URL = os.getenv('BASE_URL', 'https://api.openweathermap.org/data/2.5/weather')

# FastAPI app for REST API
app = FastAPI(title="Weather API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_weather_data(city=None, latitude=None, longitude=None):
    """Fetch weather from OpenWeatherMap API"""
    if city:
        params = {'q': city}
    elif latitude is not None and longitude is not None:
        params = {'lat': latitude, 'lon': longitude}
    else:
        raise ValueError('Provide either city OR latitude and longitude')

    params.update({'appid': API_KEY, 'units': 'metric'})

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    # Calculate rain
    rain_mm = 0
    if "rain" in data and "1h" in data["rain"]:
        rain_mm = data["rain"]["1h"]
    elif "rain" in data and "3h" in data["rain"]:
        rain_mm = data["rain"]["3h"] / 3

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
        "clouds_percent": data['clouds']['all'],
        "location": data.get('name', 'Unknown'),
        "country": data.get('sys', {}).get('country', 'N/A')
    }

@app.get("/")
def root():
    return {
        "service": "Weather API",
        "version": "1.0.0",
        "endpoint": "/api/weather?city=London"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/weather")
def weather_endpoint(
    city: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None
):
    """
    Get current weather data

    Query params:
    - city: City name (e.g., "London")
    - lat, lon: Coordinates
    """
    try:
        return get_weather_data(city, lat, lon)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except requests.exceptions.HTTPError:
        raise HTTPException(status_code=404, detail="Location not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
