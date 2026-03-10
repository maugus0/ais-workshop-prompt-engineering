"""
Cafe Order Processing System — Prompt Engineering Assignment.
Converts natural-language cafe orders into structured JSON using the OpenAI API.
Interactive REPL: run script, type orders at the prompt, get summary + JSON.
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

# Load prompt config relative to this script's directory (works from any cwd)
_DEFAULT_PROMPT_PATH = "prompts/system_prompt.json"


def _assemble_prompt_from_sections(sections: dict) -> str:
    """Build a single system_prompt string from prompt_sections (for readable JSON)."""
    parts = [
        sections["role"],
        sections["output_rules"],
        sections["schema"],
    ]
    rules = sections.get("rules", {})
    rule_order = [
        "quantity_rules",
        "size_rules",
        "modifier_rules",
        "splitting_rules",
        "combo_rules",
        "naming_rules",
        "special_instructions_rules",
        "total_items_rule",
    ]
    parts.append("\n\n<rules>\n\n" + "\n\n".join(rules.get(k, "") for k in rule_order) + "\n\n</rules>")
    parts.append(sections["examples"])
    parts.append(sections["guardrails"])
    return "\n\n".join(parts)


def _build_prompt_from_structured_config(config: dict) -> str:
    """Build system_prompt from structured config (introduction, output, schema, rules, examples, guardrails)."""
    intro = config.get("introduction", {})
    identity = intro.get("identity", "")
    principles = intro.get("principles", [])
    lines = [identity]
    if principles:
        lines.append("")
        for p in principles:
            lines.append(f"- {p}")

    out = config.get("output", {})
    if out:
        lines.append("")
        lines.append("<output_rules>")
        lines.append(f"- Respond with {out.get('format', 'single valid JSON only')}.")
        for fb in out.get("forbidden", []):
            lines.append(f"- Do NOT: {fb}.")
        err = out.get("error_response", {})
        if err:
            lines.append(f"- If input is not a cafe order, return: {json.dumps(err)}")
        lines.append("</output_rules>")

    schema = config.get("schema", {})
    if schema:
        lines.append("")
        lines.append("<schema>")
        lines.append(json.dumps(schema, indent=2))
        lines.append("</schema>")

    rules = config.get("rules", {})
    if rules:
        rule_order = [
            "quantity",
            "size",
            "modifiers",
            "splitting",
            "combo",
            "naming",
            "special_instructions",
            "total_items",
        ]
        lines.append("")
        lines.append("<rules>")
        for key in rule_order:
            if key not in rules:
                continue
            lines.append(f"<{key}_rules>")
            for bullet in rules[key]:
                lines.append(f"- {bullet}")
            lines.append(f"</{key}_rules>")
            lines.append("")
        lines.append("</rules>")

    examples = config.get("examples", [])
    if examples:
        lines.append("<examples>")
        for ex in examples:
            lines.append("")
            lines.append("<example>")
            lines.append(f"Input: \"{ex.get('input', '')}\"")
            lines.append(f"Output:\n{ex.get('output', '')}")
            lines.append("</example>")
        lines.append("")
        lines.append("</examples>")

    guardrails = config.get("guardrails", [])
    if guardrails:
        lines.append("")
        lines.append("<guardrails>")
        for g in guardrails:
            lines.append(f"- {g}")
        lines.append("</guardrails>")

    return "\n".join(lines)


def load_prompt_config(path: str = _DEFAULT_PROMPT_PATH) -> dict:
    """
    Load prompt configuration from a JSON file.
    Path is resolved relative to the directory containing this script.
    Supports two formats: a single "system_prompt" string, or "prompt_sections"
    (role, output_rules, schema, rules, examples, guardrails) which are assembled.
    """
    script_dir = Path(__file__).resolve().parent
    config_path = script_dir / path
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        raise SystemExit(f"ERROR: Could not load {path} — file not found at {config_path}") from None
    except json.JSONDecodeError as e:
        raise SystemExit(f"ERROR: Could not load {path} — invalid JSON: {e}") from None
    if "meta" not in config:
        raise SystemExit(f"ERROR: Could not load {path} — missing 'meta'") from None
    if "system_prompt" not in config:
        if "prompt_sections" in config:
            config["system_prompt"] = _assemble_prompt_from_sections(config["prompt_sections"])
        elif "introduction" in config and "output" in config:
            config["system_prompt"] = _build_prompt_from_structured_config(config)
        else:
            raise SystemExit(
                f"ERROR: Could not load {path} — need 'system_prompt', 'prompt_sections', or structured (introduction + output)"
            ) from None
    return config


PROMPT_CONFIG = load_prompt_config()


def strip_json_fences(text: str) -> str:
    """Remove markdown code fences from LLM response if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def process_order(customer_input: str) -> dict:
    """
    Send customer order to OpenAI and return parsed JSON.
    Validates and fixes total_items; strips markdown fences; handles parse errors.
    Uses prompt and API params from PROMPT_CONFIG (loaded from prompts/system_prompt.json).
    """
    raw_text = ""
    try:
        meta = PROMPT_CONFIG["meta"]
        model = meta.get("model", "gpt-4o-mini")
        temperature = float(meta.get("temperature", 0.1))
        system_prompt = PROMPT_CONFIG["system_prompt"]

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": customer_input},
            ],
            temperature=temperature,
        )
        raw_text = response.choices[0].message.content or ""
        raw_text = strip_json_fences(raw_text)
        order = json.loads(raw_text)

        # Validate and fix
        if "items" not in order or not isinstance(order["items"], list):
            return {"error": "Invalid response: missing or invalid items", "raw_response": raw_text}

        for item in order["items"]:
            if "name" not in item or "quantity" not in item:
                return {"error": "Invalid response: item missing name or quantity", "raw_response": raw_text}
            item.setdefault("size", "regular")
            item.setdefault("modifiers", [])

        order.setdefault("special_instructions", "")
        computed_total = sum(item["quantity"] for item in order["items"])
        order["total_items"] = computed_total

        return order
    except json.JSONDecodeError as e:
        return {"error": "Failed to parse JSON", "raw_response": raw_text, "detail": str(e)}
    except Exception as e:
        return {"error": str(e), "raw_response": ""}


def display_order(order: dict) -> None:
    """Print a formatted, human-readable order and the raw JSON."""
    if "error" in order:
        print("ERROR:", order["error"])
        if order.get("raw_response"):
            print("Raw response:", order["raw_response"][:500])
        return

    print("Order summary:")
    for item in order.get("items", []):
        mod_str = f" [{', '.join(item.get('modifiers', []))}]" if item.get("modifiers") else ""
        print(f"  {item['quantity']}x {item['name']} ({item.get('size', 'regular')}){mod_str}")
    if order.get("special_instructions"):
        print("  Special:", order["special_instructions"])
    print(f"  Total items: {order.get('total_items', 0)}")
    print("\nJSON:")
    print(json.dumps(order, indent=2))


def run_repl() -> None:
    """Interactive REPL: prompt for orders, call API, print summary + JSON until quit."""
    print()
    print("   ☕ Cafe Order Processing System")
    print("   ═══════════════════════════════")
    print("   Type your order in natural language. Type 'quit' or 'exit' to stop.")
    print()

    while True:
        try:
            order_text = input("   🛒 Your order: ").strip()
        except EOFError:
            print("\n   Goodbye.")
            break
        if not order_text:
            print("   Please enter an order.")
            continue
        if order_text.lower() in ("quit", "exit"):
            print("   Goodbye.")
            break

        result = process_order(order_text)
        print()
        display_order(result)
        print()


def main() -> int:
    """Entry point: run interactive REPL. Handles Ctrl+C cleanly."""
    try:
        run_repl()
        return 0
    except KeyboardInterrupt:
        print("\n   Goodbye.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
