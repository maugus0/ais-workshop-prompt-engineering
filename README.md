# Cafe Order Processing System — Prompt Engineering Assignment

This project demonstrates prompt engineering techniques to build a natural-language order processing system that converts customer café orders into structured JSON using the **OpenAI API**. The system is implemented in Python and handles quantities, sizes, modifiers (e.g. iced, decaf), combo/meal expansion, and special instructions so the output is ready for a machine-readable ordering backend. Run the script for an **interactive REPL**: type your order at the prompt and receive a summary plus JSON.

**Developed by:** Ahan Jaiswal  
**Programme:** Master of Technology in Software Engineering (MTech SE)  
**Institution:** National University of Singapore (NUS)  
**Gradeset:** Architecting AI Systems (AIS)  
**Coursework** Architecting Agentic AI Systems (AAAS) 
**Assignment:** AAAS — Day 01 Workshop (Prompt Engineering)

---

## Setup

**Requirements:** Python 3.10+ (3.13 recommended), OpenAI API key.

1. Clone the repository (or download the files).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy the environment template and add your API key:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `OPENAI_API_KEY=sk-your-actual-key`.
4. Run the processor (interactive mode):
   ```bash
   python cafe_order_processor.py
   ```
   A welcome banner appears. Type your order in natural language and press Enter to get a human-readable summary and the JSON output. Type `quit` or `exit` to stop. Use Ctrl+C to exit at any time.

---

## System Prompt

The system prompt is **loaded at runtime** from `prompts/system_prompt.json`. The config uses a **compact, hierarchical structure** (similar to modern assistant configs):

- **`meta`**: `version`, `model` (e.g. `gpt-4o-mini`), `temperature`, `last_updated`.
- **`introduction`**: `identity` (who CafeBot is), `principles` (short list).
- **`output`**: `format`, `forbidden` (what not to do), `error_response` (JSON for non-orders).
- **`schema`**: JSON shape of the response (items, special_instructions, total_items).
- **`rules`**: Per-category bullet lists (quantity, size, modifiers, splitting, combo, naming, special_instructions, total_items).
- **`examples`**: Array of `{ "input", "output" }` few-shot pairs.
- **`guardrails`**: Short list of edge-case rules.

The Python code **builds** the full prompt text from this structure, so you can edit the JSON without writing long prose. No prompt text is hardcoded in the Python file.

---

## Prompt Engineering Techniques

The prompt in `prompts/system_prompt.json` demonstrates these techniques:

| Technique | Purpose |
|-----------|--------|
| **Role & Persona** | Defines the model as "CafeBot" with a single responsibility (parse orders to JSON), constraining identity and reducing off-topic behaviour. |
| **Output Gating** | Strict rule: respond with *only* valid JSON, no markdown fences or commentary. This is the main defence against JSON parse failures. |
| **Typed Schema Contract** | The exact JSON shape (items, name, quantity, size, modifiers, special_instructions, total_items) is specified so the model "implements" a clear contract. |
| **XML-Tagged Rule Sections** | Rules are grouped in `<quantity_rules>`, `<size_rules>`, `<modifier_rules>`, etc. Named sections improve instruction-following on long prompts. |
| **Few-Shot Exemplars** | Three input→output pairs show exact formatting, modifier splitting, and combo expansion so the model matches the expected behaviour. |
| **Guardrails** | Rules for ambiguous input, non-orders, and no hallucination align with defensive handling of model output (e.g. OWASP LLM05). |

---

## Design Decisions

- **Temperature 0.1:** Keeps outputs consistent and predictable so the same phrasing tends to produce the same JSON structure, which is important for integration with an ordering system.
- **Externalised prompt:** The prompt lives in `prompts/system_prompt.json`, not in code. This separates concerns (iterate on prompt without touching code), keeps it version-controllable, and makes it easy to A/B test different prompt versions.
- **XML tags inside the prompt:** The model can reference named sections (e.g. `<quantity_rules>`), which improves instruction adherence on long prompts.
- **Few-shot examples in the system prompt:** Three concrete input→output pairs anchor the model to the exact schema and behaviour (e.g. "2x" notation, combo expansion, modifier splitting).
- **Markdown fence stripping:** The model sometimes wraps JSON in code fences. The code strips these before `json.loads()` to avoid parse failures.
- **Combo/meal expansion:** The prompt explicitly tells the model to expand "burger meal" or "combo" into separate items (main, side, drink), each with its own `name`, `quantity`, and `size`.
- **Modifier splitting:** For phrases like "three iced lattes, make one decaf", the prompt instructs two line items (2× iced latte, 1× iced latte with decaf) so each variant is represented correctly.

---

## Example Inputs and JSON Outputs

Below are five example natural-language inputs and the expected JSON structure (model output may vary slightly; `total_items` is recomputed in code).

### Example 1

**Input:** `2x Americano, 1 large fries and 3 hamburger`

```json
{
  "items": [
    {"name": "Americano", "quantity": 2, "size": "regular", "modifiers": []},
    {"name": "Fries", "quantity": 1, "size": "large", "modifiers": []},
    {"name": "Hamburger", "quantity": 3, "size": "regular", "modifiers": []}
  ],
  "special_instructions": "",
  "total_items": 6
}
```

### Example 2

**Input:** `I'll have a cappuccino and two croissants please`

```json
{
  "items": [
    {"name": "Cappuccino", "quantity": 1, "size": "regular", "modifiers": []},
    {"name": "Croissant", "quantity": 2, "size": "regular", "modifiers": []}
  ],
  "special_instructions": "",
  "total_items": 3
}
```

### Example 3

**Input:** `Can I get three iced lattes, make one of them decaf`

```json
{
  "items": [
    {"name": "Iced Latte", "quantity": 2, "size": "regular", "modifiers": ["iced"]},
    {"name": "Iced Latte", "quantity": 1, "size": "regular", "modifiers": ["iced", "decaf"]}
  ],
  "special_instructions": "",
  "total_items": 3
}
```

### Example 4

**Input:** `One burger meal with coke, and an extra order of fries`

```json
{
  "items": [
    {"name": "Hamburger", "quantity": 1, "size": "regular", "modifiers": []},
    {"name": "Fries", "quantity": 1, "size": "regular", "modifiers": []},
    {"name": "Coke", "quantity": 1, "size": "regular", "modifiers": []},
    {"name": "Fries", "quantity": 1, "size": "regular", "modifiers": []}
  ],
  "special_instructions": "",
  "total_items": 4
}
```

### Example 5

**Input:** `I want 4 espressos and a large chocolate cake, everything to go please`

```json
{
  "items": [
    {"name": "Espresso", "quantity": 4, "size": "regular", "modifiers": []},
    {"name": "Chocolate Cake", "quantity": 1, "size": "large", "modifiers": []}
  ],
  "special_instructions": "everything to go",
  "total_items": 5
}
```

---

## CI/CD and Pre-commit

- **GitHub Actions:** On push/PR to `main` or `develop`, the workflow runs formatting (Black, isort), linting (flake8, pylint), unit tests (pytest with coverage), security checks (Bandit, Safety), config validation, and a quick integration check. See `.github/workflows/ci.yml`.
- **Pre-commit:** Run `./pre-commit.sh` before committing to verify formatting, imports, linting, syntax, `.env.example`, and tests. Optional: install mypy for type checking.

---

## Limitations and Possible Improvements

- **No menu validation:** Any item name is accepted; there is no check against a fixed cafe menu.
- **No pricing:** The system does not compute or return prices.
- **JSON mode:** Using the API’s `response_format={"type": "json_object"}` could further reduce malformed JSON.
- **Retries:** Adding retry logic (e.g. on parse failure or rate limits) would make the script more robust for production use.

---

## AI Tool Declaration

I used Claude (Anthropic) to quickly iterate on this code and refine the system prompt. I am responsible for the content and quality of the submitted work.
