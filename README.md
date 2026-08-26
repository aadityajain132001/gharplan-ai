# GharPlan AI

## Render configuration

Set these Environment Variables on the Render web service:

- `OPENAI_API_KEY` — your newly created OpenAI API key
- `OPENAI_MODEL` — `gpt-5.4-mini`

Start command:

`uvicorn main:app --host 0.0.0.0 --port $PORT`

The application uses the OpenAI Responses API to turn the customer's complete requirements into a structured architectural brief, then renders three dimensioned conceptual floor-plan options as SVG.
