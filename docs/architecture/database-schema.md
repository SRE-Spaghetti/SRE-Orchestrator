# Database Schema

For the MVP, incident data will be stored in an in-memory dictionary to minimize external dependencies. The structure of the `Incident` object is defined by the following JSON Schema. This schema will be used for validation and will guide the future migration to a persistent NoSQL database (e.g., MongoDB, DynamoDB).

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Incident",
  "description": "Schema for an incident investigation object.",
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the incident."
    },
    "description": {
      "type": "string",
      "description": "The initial problem description provided by the user."
    },
    "status": {
      "type": "string",
      "enum": ["pending", "running", "completed", "failed"],
      "description": "The current state of the investigation."
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of when the incident was created."
    },
    "completed_at": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of when the investigation was completed."
    },
    "evidence": {
      "type": "object",
      "description": "A dictionary to store all collected evidence.",
      "properties": {
        "pod_details": {
          "type": "object"
        },
        "pod_logs": {
          "type": "string"
        }
      }
    },
    "extracted_entities": {
      "type": "object",
      "description": "Key entities extracted from the description by the LLM.",
      "properties": {
        "pod_name": {
          "type": "string"
        },
        "namespace": {
          "type": "string"
        }
      }
    },
    "suggested_root_cause": {
      "type": "string",
      "description": "The final conclusion from the correlation engine."
    },
    "confidence_score": {
      "type": "string",
      "enum": ["high", "medium", "low"],
      "description": "The confidence level of the suggested root cause."
    }
  },
  "required": [
    "id",
    "description",
    "status",
    "created_at"
  ]
}
```
