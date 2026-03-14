import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from groq import Groq
import requests
import json
import os
from PIL import Image
import io

class ChatRequest(BaseModel):
    message: str
    bill_context: dict

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

genai.configure(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

groq_client = Groq(api_key=GROQ_API_KEY)

async def search_item_prices(item_name, category):
    searches = [
        f"{item_name} price India rupees 2024",
        f"{item_name} CGHS rate India government",
        f"{item_name} MRP India pharmacy"
    ]
    
    all_results = []
    for query in searches:
        url = "https://google.serper.dev/search"
        payload = json.dumps({
            "q": query,
            "num": 3,
            "gl": "in"
        })
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        response = requests.post(url, headers=headers, data=payload)
        data = response.json()
        snippets = []
        for r in data.get("organic", []):
            snippets.append(r.get("snippet", ""))
        all_results.append(f"Query: {query}\nResults: {' | '.join(snippets)}")
    
    return "\n\n".join(all_results)

@app.post("/api/analyze-bill")
async def analyze_bill(file: UploadFile = File(...)):
    print("Starting analysis...")
    try:
        # 1. Read Image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # 2. Send to Gemini
        model = genai.GenerativeModel(MODEL_NAME)
        prompt = """You are a precise medical bill OCR and data extraction system.
Your job is to carefully read this Indian hospital bill image 
and extract EVERY line item with 100% accuracy.

STRICT RULES:
1. Read EVERY number carefully - do not guess or approximate
2. Extract the EXACT amount shown on the bill for each item
3. Do not combine items - each line is a separate item
4. If quantity is not shown, use 1
5. Amount must be a plain number only - no ₹ symbol, no commas
   Example: 850 not ₹850 not 8,50

Return a JSON array where each object has:
- item_name: exact name as written on bill (string)
- billed_amount: exact amount as number (float, no symbols)
- quantity: quantity as number (integer)
- category: one of these only: medicine/test/consumable/procedure/room

Example output format:
[
  {"item_name": "Paracetamol 500mg", "billed_amount": 850, "quantity": 10, "category": "medicine"},
  {"item_name": "Blood CBC Test", "billed_amount": 2800, "quantity": 1, "category": "test"}
]

Return ONLY the raw JSON array.
No markdown, no backticks, no explanation.
Start your response with [ and end with ]"""
        
        response = model.generate_content([prompt, image])
        
        # 3. Parse JSON from Gemini
        gemini_text = response.text.strip()
        if gemini_text.startswith('```'):
            gemini_text = gemini_text.split('```')[1]
            if gemini_text.startswith('json'):
                gemini_text = gemini_text[4:]
        gemini_text = gemini_text.strip()
            
        items = json.loads(gemini_text)
        
        print(f"Gemini extracted {len(items)} items")
        
        # 4. Search prices with Serper API
        search_results = {}
        items_searched = 0
        for item in items:
            cat = item.get("category", "").lower()
            if cat in ["medicine", "test", "consumable"]:
                item_name = item.get("item_name", "")
                
                search_results[item_name] = await search_item_prices(item_name, cat)
                items_searched += 1
                    
        print(f"Serper searched {items_searched} items")
        
        # 5. Send to Groq API
        system_prompt = """You are an Indian medical pricing expert. Based on the 
web search results provided, determine the fair price RANGE 
for each item in India.

PRICING GUIDELINES:
- fair_price_min = Jan Aushadhi / government hospital price
- fair_price_max = reasonable private hospital price in metro city
- Use CGHS rates as reference for government pricing
- Use actual search result data, not guesses
- If search shows specific prices, use those exact numbers
- Medicines: check MRP on package vs billed amount
- Tests: CGHS rate is usually 40-60% of private rate
- Consumables: check actual pharmacy/medical store prices

COMMON INDIAN PRICE REFERENCES:
- General ward per day: ₹500-1500 (govt) to ₹3000-6000 (private metro)
- ICU per day: ₹2000-5000 (govt) to ₹8000-15000 (private metro)
- Doctor consultation: ₹200-500 (govt) to ₹800-2000 (private metro)
- Specialist consultation: ₹500-1000 (govt) to ₹1500-3000 (private)
- Nursing charges per day: ₹200-500 (govt) to ₹1000-2000 (private)
- Ambulance: ₹500-1000 (govt) to ₹2000-5000 (private)
- OT charges: ₹2000-5000 (govt) to ₹10000-30000 (private)
- Paracetamol 500mg strip: ₹15-30 (Jan Aushadhi) to ₹50-80 (branded)
- Blood CBC test: ₹150-300 (govt) to ₹500-800 (private metro)
- Saline IV 500ml: ₹40-80 (govt) to ₹150-250 (private)
- Surgical gloves pair: ₹10-20 (govt) to ₹40-60 (private)
- X-Ray chest: ₹100-200 (govt) to ₹400-700 (private)
- ECG: ₹100-200 (govt) to ₹300-500 (private)
- Urine routine test: ₹50-100 (govt) to ₹200-400 (private)
- Bandage roll: ₹15-30 (govt) to ₹50-100 (private)

RULE: Every single item MUST have fair_price_min and 
fair_price_max greater than 0.
If you are unsure, use conservative Indian estimates.
Never return 0 for any price range.

For the range:
- fair_price_min: lowest legitimate price (govt/Jan Aushadhi)
- fair_price_max: highest reasonable price (private metro)
- Room charges: only flag if billed > 2x the fair_price_max
- Doctor consultation: only flag if billed > 3x fair_price_max
- These are more variable so be less aggressive with fraud score
- If billed_amount is within the range: fraud_confidence = 10-30
- If billed_amount is 2x max: fraud_confidence = 60-75
- If billed_amount is 3x max: fraud_confidence = 85-95
- If billed_amount is 5x+ max: fraud_confidence = 95-99

Return ONLY a raw JSON object. No markdown. No explanation.
Start with { and end with }"""

        user_prompt = f"""Here are the hospital bill items extracted from the bill:
{json.dumps(items, indent=2)}

Here are the market price search results for suspicious items:
{json.dumps(search_results)}

INSTRUCTIONS:
1. For each item in the bill, extract the exact search ranges.
2. Calculate overcharge_amount = billed_amount - fair_price_max
   If fair_price_max >= billed_amount, overcharge_amount = 0

CRITICAL MATH RULES:
- total_billed = sum of ALL billed_amount values from the items list
- estimated_fair_total = sum of ALL fair_price_estimate values
- total_overcharge = total_billed - estimated_fair_total
- Double check your addition before returning
- All amounts must be numbers, not strings

Return this EXACT JSON structure:
{{
  "all_items": [
    {{
      "item_name": "Paracetamol 500mg",
      "billed_amount": 850,
      "category": "medicine",
      "fair_price_min": 30,
      "fair_price_max": 80,
      "fair_price_display": "₹30 - ₹80",
      "overcharge_amount": 770,
      "fraud_confidence": 95,
      "reason": "Jan Aushadhi price ₹30, max private rate ₹80"
    }}
  ],
  "flagged_items": [],
  "total_billed": 24650,
  "fair_range_min_total": 1200,
  "fair_range_max_total": 4500,
  "fair_range_display": "₹1,200 - ₹4,500",
  "total_overcharge_min": 20150,
  "total_overcharge_max": 23450,
  "overcharge_range_display": "₹20,150 - ₹23,450",
  "summary": "2-3 lines about overall fraud analysis"
}}"""

        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        
        groq_resp = chat_completion.choices[0].message.content.strip()
        
        if groq_resp.startswith("```json"):
            groq_resp = groq_resp[7:]
        if groq_resp.endswith("```"):
            groq_resp = groq_resp[:-3]
            
        final_result = json.loads(groq_resp.strip())
        
        # Fix any items with 0 fair prices
        for item in final_result.get('all_items', []):
            if item.get('fair_price_min', 0) == 0:
                item['fair_price_min'] = item.get('billed_amount', 0) * 0.3
            if item.get('fair_price_max', 0) == 0:
                item['fair_price_max'] = item.get('billed_amount', 0) * 0.7
            if not item.get('fair_price_display'):
                item['fair_price_display'] = f"₹{item['fair_price_min']:,.0f} - ₹{item['fair_price_max']:,.0f}"

        # Recalculate totals using ranges
        total_billed = sum(item.get('billed_amount', 0) for item in final_result.get('all_items', []))
        fair_min_total = sum(item.get('fair_price_min', 0) for item in final_result.get('all_items', []))
        fair_max_total = sum(item.get('fair_price_max', 0) for item in final_result.get('all_items', []))
        overcharge_min = total_billed - fair_max_total
        overcharge_max = total_billed - fair_min_total

        final_result['total_billed'] = round(total_billed, 2)
        final_result['fair_range_min_total'] = round(fair_min_total, 2)
        final_result['fair_range_max_total'] = round(fair_max_total, 2)
        final_result['fair_range_display'] = f"₹{fair_min_total:,.0f} - ₹{fair_max_total:,.0f}"
        final_result['total_overcharge_min'] = round(overcharge_min, 2)
        final_result['total_overcharge_max'] = round(overcharge_max, 2)
        final_result['overcharge_range_display'] = f"₹{overcharge_min:,.0f} - ₹{overcharge_max:,.0f}"

        # Keep estimated_fair_total as midpoint for compatibility
        final_result['estimated_fair_total'] = round((fair_min_total + fair_max_total) / 2, 2)
        final_result['total_overcharge'] = round(total_billed - final_result['estimated_fair_total'], 2)

        final_result['flagged_items'] = [
            item for item in final_result.get('all_items', []) 
            if item.get('fraud_confidence', 0) > 50
        ]

        print(f"Total billed: {total_billed}")
        print(f"Fair range: {fair_min_total} - {fair_max_total}")
        print(f"Overcharge range: {overcharge_min} - {overcharge_max}")
        
        print("Groq analysis complete")
        return final_result
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Request

@app.post("/api/chat")
async def chat(request: Request):
    body = await request.json()
    user_message = body.get("message", "")
    bill_context = body.get("bill_context", {})
    chat_history = body.get("chat_history", [])
    
    client = Groq(api_key=GROQ_API_KEY)
    
    # Step 1: Use Groq to detect location from message
    location_detection = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are a location detector. 
                Extract ANY location mentioned in the user message.
                Location can be:
                - Any Indian city (Mumbai, Patna, Gorakhpur etc)
                - Any Indian village or town
                - Any Indian district
                - Any Indian state
                - Any international location
                - Rural/Urban/Tier-2 type mentions
                
                Return ONLY a JSON object:
                {"location_found": true/false, "location": "extracted location or null", "location_type": "metro/tier2/tier3/rural/international or null"}
                
                Examples:
                "I am in Gorakhpur" -> {"location_found": true, "location": "Gorakhpur", "location_type": "tier3"}
                "mai mumbai mein hun" -> {"location_found": true, "location": "Mumbai", "location_type": "metro"}
                "mere gaon mein" -> {"location_found": true, "location": "rural area", "location_type": "rural"}
                "which item is overcharged" -> {"location_found": false, "location": null, "location_type": null}
                "I live in a small village in UP" -> {"location_found": true, "location": "rural Uttar Pradesh", "location_type": "rural"}
                "Dubai mein" -> {"location_found": true, "location": "Dubai", "location_type": "international"}
                
                Return ONLY raw JSON. No explanation."""
            },
            {"role": "user", "content": user_message}
        ],
        max_tokens=100,
        temperature=0
    )
    
    # Parse location detection result
    location_data = {"location_found": False, "location": None, "location_type": None}
    try:
        location_text = location_detection.choices[0].message.content.strip()
        if location_text.startswith('```'):
            location_text = location_text.split('```')[1]
            if location_text.startswith('json'):
                location_text = location_text[4:]
        location_data = json.loads(location_text.strip())
    except:
        pass
    
    # Step 2: Build location context if found
    location_context = ""
    if location_data.get("location_found"):
        location = location_data.get("location")
        location_type = location_data.get("location_type")
        
        pricing_rules = {
            "metro": "Top metro city. Private hospitals charge premium rates. Fair price is 70-80% of max range.",
            "tier2": "Tier 2 city. Moderate pricing. Fair price is midpoint of range.",
            "tier3": "Tier 3 city or small town. Lower costs. Fair price is 30-40% of max range.",
            "rural": "Rural/village area. Very low costs. Use minimum range or lower. Government PHC rates apply.",
            "international": "International location. Indian hospital prices apply since bill is from India."
        }
        
        rule = pricing_rules.get(location_type, "Use midpoint of fair price range.")
        
        location_context = f"""
        LOCATION DETECTED: {location} (Type: {location_type})
        PRICING RULE: {rule}
        
        Give specific price estimates for {location}.
        Format each item as:
        "In {location}, fair price for [item]: ₹X - ₹Y
        You were billed ₹Z ([N]x overcharge)"
        
        At the end add:
        "💡 Tip for {location}: [specific advice for that location type]"
        """
    
    # Step 3: Build chat messages with history
    messages = []
    for msg in chat_history[-8:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    messages.append({
        "role": "user",
        "content": f"""
        Bill Analysis: {json.dumps(bill_context)}
        {location_context}
        User Question: {user_message}
        """
    })
    
    # Step 4: Get main response
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """You are BillSanjivani AI - India's smartest 
                hospital billing fraud detective.
                
                You know hospital prices for EVERY location in India:
                - Every metro, tier 2, tier 3, small town, village
                - CGHS rates, IRDAI rates, Jan Aushadhi prices
                - ESI hospital rates
                - State government hospital rates
                - Private hospital rates by city tier
                
                RULES:
                1. If location is mentioned, give SPECIFIC prices for that 
                   exact location. Even for small towns and villages.
                2. Always mention if patient is still overcharged 
                   even at their location's rates
                3. Be conversational, warm and helpful
                4. Use ₹ for all amounts
                5. Understand Hindi, Hinglish, and regional language hints
                6. Keep response under 200 words
                7. Always end with one actionable tip
                8. For rural areas, mention Jan Aushadhi stores 
                   and government hospital options nearby
                9. For metros, mention consumer court and 
                   insurance dispute options
                
                LOCATION TIPS TO GIVE:
                - Rural: "Visit nearest Jan Aushadhi store, 
                  Government PHC for follow up"
                - Tier 3: "District hospital offers same tests 
                  at 60-70% lower cost"
                - Tier 2: "Check with 2-3 diagnostic labs, 
                  prices vary significantly"  
                - Metro: "File complaint with state medical council,
                  IRDAI grievance portal"
                """
            },
            *messages
        ],
        max_tokens=500,
        temperature=0.7
    )
    
    return {
        "reply": response.choices[0].message.content,
        "location_detected": location_data.get("location"),
        "location_type": location_data.get("location_type")
    }
