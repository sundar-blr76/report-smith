import os
import google.generativeai as genai

# Configure with your API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Test with a simple query
model = genai.GenerativeModel('gemini-1.5-flash')

prompt = """Analyze this query and return a JSON object:
Query: Show monthly fees for equity funds

Return JSON with: intent_type, entities (list), time_scope, aggregations (list)"""

response = model.generate_content(
    prompt,
    generation_config={
        "temperature": 0,
        "response_mime_type": "application/json",
    }
)

print("✅ Gemini API Test Successful!")
print(f"\nModel: gemini-1.5-flash")
print(f"Response:\n{response.text}")
