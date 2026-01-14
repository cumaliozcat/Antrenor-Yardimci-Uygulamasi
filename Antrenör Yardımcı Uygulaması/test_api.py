import google.generativeai as genai

# API ANAHTARINI BURAYA YAZ
GOOGLE_API_KEY = "AIzaSyABevzjTA9thiQQtSl6_mkwSH6JkFVlzOs"

genai.configure(api_key=GOOGLE_API_KEY)

print("Mevcut Modeller Listeleniyor...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print("Hata:", e)