"""Layer 6: untrusted input. What happens when the data talks back?"""

from __future__ import annotations

import re

from ..model import Layer, Severity, Status
from ..repo import FileKind
from .base import NO_TOOLS_MSG, Outcome, ScanContext, check, tiered

L = Layer.UNTRUSTED_INPUT


@check(
    "UI-01", L, "Untrusted content is marked as data", Severity.CRITICAL,
    why="Web pages, emails, files and tool results can carry instructions. If the prompt "
        "doesn't separate them from yours, the model can't either. This is prompt injection.",
    look_for="Code that labels external content as untrusted, prompt-injection defences, "
             "guardrail libraries (LLM Guard, NeMo Guardrails, Rebuff, Lakera, Prompt Guard); "
             "weaker: wrapping external content in tags such as <document> or <search_results>.",
    full="External content is labelled untrusted or screened before it reaches the model.",
    partial="External content is wrapped in delimiters, or prompt injection is acknowledged in code, "
            "but content is not labelled or screened.",
    fix="Wrap every piece of external content in a labelled block, tell the model it is "
        "data, never instructions, screen it, and keep tool tiers enforced whatever it says.",
)
def untrusted_marked(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[
            r"\b(untrusted|quarantin\w*|data,? not instructions|treat (it|this|them|the \w+) as data|never (follow|obey) (instructions|commands) (in|from|inside))\b",
            r"\b(llm[-_]?guard|nemoguardrails|NeMo[-_ ]?Guardrails|rebuff|lakera|PromptGuard|prompt[-_]?guard|prompt[-_]?shield|guardrails[-_]?ai)\b",
        ],
        partial=[
            r"<\s*/?\s*(document|documents|web_?content|webpage|search_results?|tool_(output|result)|external_content|email|file_content|context)\s*>",
            r"\b(prompt[-_ ]?injection|indirect[-_ ]?injection)\b",
        ],
        kinds=(FileKind.CODE, FileKind.CONFIG),
        flags=re.I,
        full_msg="Untrusted content is labelled or screened.",
        partial_msg="Content is delimited or injection is acknowledged, but external content is not labelled untrusted.",
        missing_msg="No handling of untrusted content found.",
    )


@check(
    "UI-02", L, "Model output is parsed into a schema", Severity.HIGH,
    why="Free text that later drives a tool call or a database write is where hallucinated "
        "and injected values slip through. A schema rejects them at the boundary.",
    look_for="with_structured_output, response_format / json_schema, output_pydantic, "
             "output_type, PydanticOutputParser, Zod schemas, instructor; weaker: bare "
             "json.loads / JSON.parse of model text.",
    full="Model output that drives actions is validated against a schema.",
    partial="Model output is parsed as JSON without a schema.",
    fix="Request structured output and validate it with Pydantic or Zod before anything acts on it.",
)
def structured_output(ctx: ScanContext) -> Outcome:
    return tiered(
        ctx,
        full=[r"\b(with_structured_output|response_format|output_pydantic|output_json|output_type|outputType|PydanticOutputParser|JsonOutputParser|StructuredOutputParser|model_validate_json|TypeAdapter|instructor\.|json_schema|output_format|outputFormat|zodResponseFormat|generateObject)\b"],
        partial=[r"\bjson\.loads\(|\bJSON\.parse\(|\bjson\.Unmarshal\("],
        flags=0,
        full_msg="Model output is validated against schemas.",
        partial_msg="Output is parsed as JSON, without schema validation.",
        missing_msg="No parsing or validation of model output found.",
    )


@check(
    "UI-03", L, "Tool arguments are validated", Severity.HIGH,
    why="The model writes the arguments. Types, ranges and formats are the last check before "
        "they hit a shell, a query or an API.",
    look_for="args_schema, input_schema / inputSchema, Pydantic models with constraints, "
             "validate_call, jsonschema.validate, Zod; weaker: typed tool functions only.",
    full="Tool inputs are checked against explicit schemas or constraints.",
    partial="Tools are typed, but inputs are not validated beyond that.",
    fix="Give every tool a schema with constraints (enums, lengths, patterns) and reject "
        "anything outside it before execution.",
)
def tool_args(ctx: ScanContext) -> Outcome:
    if not ctx.has_tools:
        return Outcome(Status.NOT_APPLICABLE, NO_TOOLS_MSG)
    return tiered(
        ctx,
        full=[
            r"\b(args_schema|input_schema|inputSchema|InputSchema|parameters_schema)\s*[=:]",
            r"\b(validate_call|validate_arguments|jsonschema\.validate|Draft\d+Validator|model_validate)\(",
            r"\bz\.object\(|\bField\([^)]*\b(ge|le|gt|lt|max_length|min_length|pattern)\s*=",
            r"\bmcp\.(WithString|WithNumber|Required|Enum)\(",
        ],
        partial=[r"^\s*@(tool|function_tool)\b", r"\b(server|mcp)\.tool\(", r"\bBaseTool\b"],
        flags=re.M,
        full_msg="Tool inputs are validated.",
        partial_msg="Tools are typed, but their inputs are not validated beyond types.",
        missing_msg="No validation of tool arguments found.",
    )

