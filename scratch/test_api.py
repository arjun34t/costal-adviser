import requests
import json

url = "http://localhost:8000/chat"
payload = {
    "message": "What is the price of Pomfret?",
    "district": "Kochi",
    "language": "en"
}
headers = {"Content-Type": "application/json"}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
