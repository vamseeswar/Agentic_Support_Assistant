# Solution Note: Trendly Agentic Support Assistant

## Architecture

The system is built as a deterministic, tool-augmented Agentic AI loop using a combination of FastAPI, Pydantic, and Groq/Gemini LLMs. 

Unlike a standard RAG pipeline or keyword matcher, this architecture operates on the principle of **LLM as the orchestrator, Python as the engine**.

1. **Input Guardrails (`app/guardrails/safety.py`)**: Before the LLM ever sees a user prompt, a deterministic Python layer intercepts adversarial inputs (e.g., prompt injections), explicit discount begging (enforcing Section 7 of the policy), and raw financial details (credit cards, CVVs). This guarantees absolute adherence to strict compliance rules without trusting the LLM to self-regulate.
2. **Conversation State (`app/state.py`)**: An in-memory conversational state manager tracks multi-turn interactions. It automatically binds the active Customer ID and tracks current contexts (like `current_order_id`) across tool boundaries.
3. **Tool Registry (`app/tools/`)**: The LLM acts entirely through highly-constrained tools (`get_order`, `search_policy`, `check_return_eligibility`, etc.). The LLM does *not* make policy decisions itself; it delegates the decision logic to the deterministic tools, which calculate time-windows (e.g., 30-day limits), exceptions (jewellery/innerwear), and generate structured JSON responses that the LLM then formats into natural language.
4. **Escalation Engine (`app/services/escalation_service.py`)**: A dedicated service structured to capture state, reason, and an LLM-generated summary, dispatching it as a high-fidelity support ticket (`ESC-XXXXXX`) when an automated resolution is blocked.

## Key Trade-offs

1. **Hardcoded Eligibility vs. LLM Reasoning**: I chose to hardcode the return/exchange eligibility logic (calculating the 30-day window, checking categories) into a deterministic Python tool (`check_return_eligibility`) rather than feeding the LLM the policy text and asking it to deduce eligibility. 
   - *Trade-off*: Harder to update (requires a code change rather than a prompt change).
   - *Benefit*: Zero chance of hallucination. The LLM can never accidentally grant a return for a 45-day old order due to bad math or prompt bypass.
2. **In-Memory State vs. Persistent Database**: 
   - *Trade-off*: State vanishes on server restart. Not suitable for a distributed production load balancer.
   - *Benefit*: Dramatically faster iteration and easier testing for this screening assignment without requiring Redis/Postgres infrastructure.
3. **Lexical vs. Semantic Search**: For policy grounding, I built a lexical search tool (`search_policy`) rather than a full vector database / RAG setup.
   - *Trade-off*: Misses highly nuanced semantic queries.
   - *Benefit*: Zero latency, perfectly exact matches to section numbers, and requires no embedding infrastructure or costs, fitting within the "Free LLM tiers only" requirement.

## Known Limitations

- **Date Handling**: The current `REFERENCE_DATE` for "today" is hardcoded in the testing setup as `August 1, 2026` to align with the provided `orders.json` delivery dates (which are all in early/mid 2026). In production, this must be switched to `datetime.utcnow()`.
- **Single-Threaded File Locking**: The JSON repositories (`order_repository.py`) load from disk synchronously. Under heavy concurrent load (2,000 chats/day), this would cause I/O blocking.
- **LLM Rate Limits**: Groq's free tier has strict requests-per-minute limits. The multi-turn tool calling architecture executes multiple LLM round-trips per user message, which can quickly exhaust free rate limits.

## Five Discovery Questions for Trendly Ops Team

If tasked with deploying this into production, I would need the operations team to clarify these critical ambiguities:

1. **Carrier API Integration**: What logistics API (Shiprocket, Bluedart, Delhivery) does Trendly use, and do they support webhooks for real-time delivery status, or will the agent need to poll?
2. **Partial Returns Policy**: If a customer bought a "Buy 2 Get 1 Free" bundle, how do we prorate the refund if they only return one item? (The policy document does not cover bundle prorating).
3. **Fraud Detection Flags**: Does the backend order system provide a "high return rate" or "suspected fraud" boolean flag on the Customer profile? Should the agent immediately escalate customers with >30% return rates instead of auto-processing?
4. **Human Handoff UX**: When `escalate_to_human` fires, does the human agent step into the *same* chat window seamlessly (like Intercom/Zendesk), or is it an asynchronous email ticket? If seamless, what is the maximum acceptable wait time before falling back to email?
5. **Footwear Deduction Edge Case**: Section 2.5 states a ₹300 deduction applies if the shoe box is missing. How does the AI agent definitively know the box is missing during the chat? Do we force the customer to confirm a checkbox, or do we refund the full amount provisionally and claw it back at the warehouse?
