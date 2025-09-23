# Data Models

### Incident

**Purpose:** Represents a single investigation from initiation to completion. It is the central data object for the system.

**Key Attributes:**
- `id`: `string` (UUID) - Unique identifier for the incident.
- `description`: `string` - The initial problem description by the user.
- `status`: `string` - The current state of the investigation (e.g., `pending`, `running`, `completed`, `failed`).
- `created_at`: `datetime` - Timestamp of when the incident was created.
- `completed_at`: `datetime` - Timestamp of when the investigation was completed.
- `evidence`: `dict` - A dictionary to store all collected evidence, such as pod logs and status.
- `extracted_entities`: `dict` - Key entities extracted from the description by the LLM (e.g., pod name, namespace).
- `suggested_root_cause`: `string` - The final conclusion from the correlation engine.
- `confidence_score`: `string` - The confidence level of the suggested root cause (e.g., `high`, `medium`, `low`).

**Relationships:**
- This is the root model and does not have explicit relationships to other models in the MVP.
