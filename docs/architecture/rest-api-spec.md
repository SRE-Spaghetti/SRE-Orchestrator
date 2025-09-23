# REST API Spec

```yaml
openapi: 3.0.0
info:
  title: SRE Orchestrator API
  version: 1.0.0
  description: API for the SRE Orchestrator to manage incident investigations.
servers:
  - url: /api/v1
    description: API v1

paths:
  /incidents:
    post:
      summary: Create a new incident investigation
      operationId: createIncident
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/NewIncidentRequest'
      responses:
        '202':
          description: Accepted
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/NewIncidentResponse'
        '400':
          description: Bad Request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /incidents/{id}:
    get:
      summary: Get the status of an incident investigation
      operationId: getIncident
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Incident'
        '404':
          description: Not Found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

  /health:
    get:
      summary: Health check
      operationId: getHealth
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    example: ok

components:
  schemas:
    NewIncidentRequest:
      type: object
      properties:
        description:
          type: string
          example: "Pod 'auth-service-xyz' is in CrashLoopBackOff"
      required:
        - description

    NewIncidentResponse:
      type: object
      properties:
        incident_id:
          type: string
          format: uuid
          example: "123e4567-e89b-12d3-a456-426614174000"
      required:
        - incident_id

    Incident:
      type: object
      properties:
        id:
          type: string
          format: uuid
        description:
          type: string
        status:
          type: string
          enum: [pending, running, completed, failed]
        created_at:
          type: string
          format: date-time
        completed_at:
          type: string
          format: date-time
        evidence:
          type: object
        extracted_entities:
          type: object
        suggested_root_cause:
          type: string
        confidence_score:
          type: string
          enum: [high, medium, low]
      required:
        - id
        - description
        - status
        - created_at

    Error:
      type: object
      properties:
        code:
          type: integer
        message:
          type: string
      required:
        - code
        - message
```
