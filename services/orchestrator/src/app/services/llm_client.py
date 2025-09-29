import os
import json
from typing import Optional, Dict, Any
import google.generativeai as genai

class LLMClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')

    def extract_entities(self, description: str) -> Optional[Dict[str, Any]]:
        prompt = f"""You are an SRE assistant. Extract the pod name, namespace, and a summary of the error from the following incident description. Respond with a JSON object containing 'pod_name', 'namespace', and 'error_summary'. If a field cannot be extracted, use null. If the pod name is not explicitly mentioned, try to infer it from context. If the namespace is not explicitly mentioned, assume 'default'.

Incident Description: {description}

Example JSON Response:
{{
  "pod_name": "my-pod-xyz",
  "namespace": "my-namespace",
  "error_summary": "Container crashed due to OOM"
}}
"""
        try:
            response = self.model.generate_content(prompt)
            # Assuming the LLM response is directly a JSON string
            extracted_data = json.loads(response.text)
            return extracted_data
        except Exception as e:
            print(f"Error extracting entities with LLM: {e}")
            return None

llm_client_instance: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global llm_client_instance
    if llm_client_instance is None:
        llm_client_instance = LLMClient()
    return llm_client_instance
