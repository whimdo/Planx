import requests

url = "http://localhost:8000/extract_keywords/"
data = {
    "text": (
        "The rapid advancement of Artificial Intelligence (AI) has revolutionized various industries, "
        "including healthcare, finance, and transportation. Machine learning algorithms, particularly "
        "deep learning models like neural networks, enable systems to process vast amounts of data and "
        "make accurate predictions. In healthcare, AI-powered tools assist doctors in diagnosing diseases "
        "and personalizing treatment plans based on patient data. In finance, predictive analytics driven "
        "by AI helps detect fraud, optimize trading strategies, and forecast market trends with high precision. "
        "Meanwhile, self-driving cars in transportation rely on real-time data processing and computer vision, "
        "both powered by sophisticated AI techniques that integrate sensor data and environmental analysis. "
        "The adoption of AI technologies is accelerating globally, with companies investing heavily in research "
        "and development to stay competitive. However, challenges such as data privacy, ethical concerns, "
        "algorithmic bias, and the need for robust computational resources remain critical issues. Addressing "
        "these concerns requires collaboration between governments, tech companies, and academic institutions "
        "to ensure AI is deployed responsibly and equitably across society."
    ),
    "keyword_count": 10,
    "model": "llama3.3:latest",
    "temp": 0.8,
    "max_tokens": 14000
}

response = requests.post(url, json=data)
print(f"Status Code: {response.status_code}")
print(f"Response Text: {response.text}")
try:
    print(response.json())
except requests.exceptions.JSONDecodeError as e:
    print(f"JSON Decode Error: {e}")