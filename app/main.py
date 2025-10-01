import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from transformers import pipeline
from typing import Dict

app = FastAPI()

classifier = pipeline(
    "text-classification",
    model="protectai/deberta-v3-base-prompt-injection-v2",
    truncation=True,
    max_length=512,
    device=-1  # CPU
)

API_KEY_NAME = "x-api-key"
api_key_header = APIKeyHeader(name=API_KEY_NAME)

async def get_api_key(api_key: str = Depends(api_key_header)):
    expected_key = os.getenv("API_KEY")  # Load from environment variable
    if not expected_key:
        raise HTTPException(status_code=500, detail="API_KEY environment variable not set")
    if api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key


class ValidateRequest(BaseModel):
    text: str
    guardrails: Dict[str, Dict]  


@app.post("/api/v1/validate")
def validate(request: ValidateRequest, api_key: str = Depends(get_api_key)):
    if "aws/prompt_attack" not in request.guardrails:
        raise HTTPException(status_code=400, detail="Unsupported guardrail")
    
    result = classifier(request.text)[0]
    score = result["score"] if result["label"] == "INJECTION" else 1 - result["score"]
    
    return {
        "results": {
            "aws/prompt_attack": {"score": round(score, 4)}
        }
    }

@app.get("/")
def root():
    return {"message": "Guardrail API is running"}