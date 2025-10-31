import logging
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
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(model_name)

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
            logging.info(f"LLM Response: {response.text}")

            # The LLM may wrap the JSON in a markdown block (```json ... ```).
            # We need to extract the raw JSON string.
            response_text = response.text
            start_index = response_text.find("{")
            end_index = response_text.rfind("}")

            if start_index == -1 or end_index == -1:
                raise ValueError("Could not find a JSON object in the LLM response.")

            json_string = response_text[start_index : end_index + 1]
            extracted_data = json.loads(json_string)
            return extracted_data
        except Exception as e:
            logging.error(f"Error extracting entities with LLM: {e}")
            return None


llm_client_instance: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global llm_client_instance
    if llm_client_instance is None:
        llm_client_instance = LLMClient()
    return llm_client_instance
