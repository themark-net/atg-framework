"""Interface-preserving recursive compilation.

Zhang et al. (2026), Atomic Task Graph, §4.1. The model emits a
``Decomposition`` JSON object (Decision 0012). The JSON schema for that
object is built from the same identifier and ``$ref`` patterns as the
graph model (Decision 0025). A plan that fails validation is returned
to the model with the validator text, for at most
``max_compile_attempts`` calls. Depth cap is 6 (Decision 0007).
Independent reimplementation; see docs/ATTRIBUTION.md
(``zhang2026atg``).
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from atg.graph import GraphError, TaskGraph
from atg.history import GraphHistory
from atg.llm import LLMError
from atg.metrics import Metrics
from atg.tools import ToolRegistry, is_atomic
from atg.types import ID_HEAD, ID_TAIL, ID_PATTERN, REF_PATTERN, TaskNode, parse_ref
from atg.validation import InterfaceError, assert_interface_preserved

# First plan plus two corrections. Counted on Metrics.compile_retries, not repairs.
DEFAULT_COMPILE_ATTEMPTS = 3

_SYSTEM = (
    "You compile one task node into a typed atomic task graph. "
    "The method is Zhang et al. (2026), Atomic Task Graph, arXiv:2607.01942, section 4.1. "
    "This is an independent reimplementation, not an official release by those authors. "
    "Return only JSON that matches the schema.\n"
    "Typing rules:\n"
    "- tool_name is exactly one name from the tool list, or null when the node is not yet a tool call.\n"
    "- Set refine to false whenever tool_name is set.\n"
    "- Fill every parameter of the chosen tool. An input is a JSON literal or "
    '{"$ref": "producer_id.outputs.field"}.\n'
    "- The $ref string must contain .outputs. between the producer id and the field. "
    "producer.field is invalid.\n"
    "- A $ref may name a child that is an ancestor through edges, or an id already present "
    "on the parent inputs. Do not name the parent id.\n"
    "- A $ref to another child is valid only when edges includes that child as src "
    "and the reader as dst.\n"
    "- Never emit an edge whose src and dst are the same id.\n"
    "- A $ref that names an id already on the parent inputs does not get an edge.\n"
    "- Copy every parent $ref onto some child. Do not invent an external $ref the parent does not have. "
    "Never emit an id that starts with example_. Those ids exist only in the example.\n"
    "- Every sink (a node with no outgoing edge) must list the parent declared_outputs "
    "by those exact names. Do not leave declared_outputs empty.\n"
    "- Edges connect child ids only. Do not use the parent id as a node or an edge endpoint.\n"
    "- Steps that do not depend on each other are siblings with no edge between them. "
    "When the task applies two operations to the same value in parallel, both operations are siblings, "
    "each takes a $ref to that value, and a later node combines their outputs. "
    "Do not chain one of those operations into the other, and do not replace one of them with a bare literal.\n"
    "The example in the user message shows the shape. Use the task's own numbers and tools. "
    "Do not copy the example numbers when the task states different ones."
)


class CompileError(Exception):
    """Compilation stopped without an all-atomic graph."""

    def __init__(self, message: str, *, compile_retries: int = 0) -> None:
        super().__init__(message)
        self.compile_retries = compile_retries


class ChildNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tool_name: str | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    declared_outputs: list[str] = Field(default_factory=list)
    refine: bool = True


class EdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str
    dst: str


class Decomposition(BaseModel):
    """One refinement of a single parent node."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[ChildNode]
    edges: list[EdgeSpec] = Field(default_factory=list)


class RefBinding(BaseModel):
    """One planner ``$ref``. The pattern is ``REF_PATTERN`` from the graph model."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    ref: str = Field(alias="$ref", pattern=REF_PATTERN)


InputValue = int | float | str | bool | None | RefBinding


class PlanningNode(BaseModel):
    """Schema twin of ``ChildNode``. Field names must stay aligned with it."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=ID_PATTERN)
    name: str
    tool_name: str | None = None
    inputs: dict[str, InputValue] = Field(default_factory=dict)
    declared_outputs: list[str] = Field(default_factory=list)
    refine: bool = True


class PlanningDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nodes: list[PlanningNode]
    edges: list[EdgeSpec] = Field(default_factory=list)


_PLANNING_MODELS: dict[tuple[tuple[str, ...], bool], type[BaseModel]] = {}


def planning_model(tool_names: tuple[str, ...], *, require_declared_output: bool) -> type[BaseModel]:
    """Pydantic model whose JSON schema is what the client sends.

    ``tool_name`` is the registry's names, or null. When the parent declares
    outputs, each child must declare at least one. The ``$ref`` pattern is
    ``RefBinding``, not a second copy of the regex.
    """

    names = tuple(sorted({name for name in tool_names if name}))
    key = (names, require_declared_output)
    cached = _PLANNING_MODELS.get(key)
    if cached is not None:
        return cached
    tool_ann = (Literal[names] | None) if names else (str | None)
    output_field = (
        Field(default_factory=list, min_length=1)
        if require_declared_output
        else Field(default_factory=list)
    )
    node = create_model(
        "PlanningNode",
        __base__=PlanningNode,
        tool_name=(tool_ann, None),
        declared_outputs=(list[str], output_field),
    )
    spec = create_model(
        "PlanningDecomposition",
        __base__=PlanningDecomposition,
        nodes=(list[node], ...),
    )
    _PLANNING_MODELS[key] = spec
    return spec


def decomposition_gbnf(tool_names: list[str] | None = None) -> str:
    """GBNF for one decomposition. Identifier classes are ``ID_HEAD`` and ``ID_TAIL``.

    A ``$ref`` value must contain ``.outputs.``. llama-server takes this string
    as ``grammar`` on ``OpenAICompatClient``. Ollama keeps using JSON schema.
    """

    names = sorted({name for name in (tool_names or []) if name})
    if names:
        literal = " | ".join('"\\"' + name + '\\""' for name in names)
        tool_rule = f"tool-name ::= {literal} | \"null\""
    else:
        tool_rule = 'tool-name ::= string | "null"'
    lines = [
        'root ::= "{" ws "\\"nodes\\"" ws ":" ws nodes ws "," ws "\\"edges\\"" ws ":" ws edges ws "}"',
        "ws ::= [ \\t\\n]*",
        'nodes ::= "[" ws "]" | "[" ws node (ws "," ws node)* ws "]"',
        'edges ::= "[" ws "]" | "[" ws edge (ws "," ws edge)* ws "]"',
        (
            'node ::= "{" ws "\\"id\\"" ws ":" ws qident ws "," ws "\\"name\\"" ws ":" ws string '
            'ws "," ws "\\"tool_name\\"" ws ":" ws tool-name ws "," ws "\\"inputs\\"" ws ":" ws input-object '
            'ws "," ws "\\"declared_outputs\\"" ws ":" ws strings ws "," ws "\\"refine\\"" ws ":" ws boolean ws "}"'
        ),
        'edge ::= "{" ws "\\"src\\"" ws ":" ws qident ws "," ws "\\"dst\\"" ws ":" ws qident ws "}"',
        'input-object ::= "{" ws "}" | "{" ws input-pair (ws "," ws input-pair)* ws "}"',
        'input-pair ::= string ws ":" ws input-value',
        'input-value ::= number | string | boolean | "null" | ref-object',
        'ref-object ::= "{" ws "\\"$ref\\"" ws ":" ws refstring ws "}"',
        'refstring ::= "\\"" ident ".outputs." ident "\\""',
        'strings ::= "[" ws "]" | "[" ws string (ws "," ws string)* ws "]"',
        'boolean ::= "true" | "false"',
        'number ::= "-"? [0-9]+ ("." [0-9]+)?',
        'string ::= "\\"" char* "\\""',
        'char ::= [^"\\\\] | "\\\\" .',
        'qident ::= "\\"" ident "\\""',
        f"ident ::= [{ID_HEAD}] [{ID_TAIL}]*",
        tool_rule,
    ]
    return "\n".join(lines) + "\n"


def compile_task(
    root: TaskNode,
    registry: ToolRegistry,
    llm: Any,
    *,
    max_depth: int = 6,
    metrics: Metrics | None = None,
    max_compile_attempts: int = DEFAULT_COMPILE_ATTEMPTS,
) -> tuple[TaskGraph, GraphHistory]:
    graph = TaskGraph()
    graph.add_node(root)
    history = GraphHistory()
    history.append(graph, "initial")
    for step in range(max_depth):
        pending = [
            node_id
            for node_id in graph.topological_order()
            if not is_atomic(graph.get(node_id), registry)
        ]
        if not pending:
            return graph, history
        for node_id in pending:
            if node_id not in graph or is_atomic(graph.get(node_id), registry):
                continue
            parent = graph.get(node_id)
            subgraph = propose_subgraph(
                parent,
                registry,
                llm,
                metrics=metrics,
                max_attempts=max_compile_attempts,
            )
            graph.replace_node(node_id, subgraph)
        history.append(graph, f"refine-{step + 1}")
    left = [
        node_id
        for node_id in graph.node_ids()
        if not is_atomic(graph.get(node_id), registry)
    ]
    if left:
        raise CompileError(
            f"depth cap {max_depth} with non-atomic nodes: {left}",
            compile_retries=0 if metrics is None else metrics.compile_retries,
        )
    return graph, history


def propose_subgraph(
    parent: TaskNode,
    registry: ToolRegistry,
    llm: Any,
    *,
    note: str | None = None,
    repair: bool = False,
    metrics: Metrics | None = None,
    max_attempts: int = DEFAULT_COMPILE_ATTEMPTS,
) -> TaskGraph:
    """Ask for one subgraph. On a validator failure, send that text back.

    ``metrics.compile_retries`` counts the extra calls, not the first plan
    and not an execution repair. The attempt budget includes the first plan.
    """

    schema = planning_model(
        tuple(registry.names()),
        require_declared_output=bool(parent.declared_outputs),
    )
    attempts = max(1, max_attempts)
    last: BaseException | None = None
    last_spec: Decomposition | None = None
    local_retries = 0
    for attempt in range(attempts):
        if attempt:
            local_retries += 1
            _bump_retries(metrics)
        validator_error = None if last is None else str(last)
        try:
            raw = llm.complete_structured(
                _messages(
                    parent,
                    registry,
                    note=note,
                    repair=repair,
                    validator_error=validator_error,
                ),
                schema,
            )
        except Exception as exc:
            if not _plan_rejection(exc):
                if last is not None:
                    raise CompileError(
                        _failure_text(last, last_spec),
                        compile_retries=_reported_retries(metrics, local_retries),
                    ) from exc
                raise
            last = exc
            last_spec = None
            if attempt + 1 == attempts:
                raise CompileError(
                    str(exc),
                    compile_retries=_reported_retries(metrics, local_retries),
                ) from exc
            continue
        spec: Decomposition | None = None
        try:
            spec = _as_decomposition(raw)
            last_spec = spec
            copied = _copied_example_ids(spec)
            if copied:
                raise CompileError(
                    "ids copied from the example ("
                    + ", ".join(copied)
                    + "). Invent new ids. Do not emit example_. "
                    "A $ref to another child needs an edge from that child to the reader."
                )
            subgraph = _decomposition_graph(spec, parent)
            assert_interface_preserved(parent, subgraph)
        except (ValidationError, InterfaceError, GraphError, CompileError) as exc:
            last = exc
            if attempt + 1 == attempts:
                raise CompileError(
                    _failure_text(exc, spec),
                    compile_retries=_reported_retries(metrics, local_retries),
                ) from exc
            continue
        return subgraph
    raise CompileError(
        _failure_text(last, last_spec) if last else "no plan",
        compile_retries=_reported_retries(metrics, local_retries),
    )


def _messages(
    node: TaskNode,
    registry: ToolRegistry,
    *,
    note: str | None = None,
    repair: bool = False,
    validator_error: str | None = None,
) -> list[dict]:
    payload: dict[str, Any] = {
        "node": {
            "id": node.id,
            "name": node.name,
            "inputs": node.inputs,
            "declared_outputs": node.declared_outputs,
        },
        "tools": registry.as_openai_tools(),
        "sink_outputs": list(node.declared_outputs),
    }
    example = _catalog_example(node, registry, repair=repair)
    if example is not None:
        payload["example"] = example
    if note:
        payload["note"] = note
    if validator_error:
        payload["validator_error"] = validator_error
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": json.dumps(payload)},
    ]


def _catalog_example(
    node: TaskNode,
    registry: ToolRegistry,
    *,
    repair: bool,
) -> dict[str, Any] | None:
    """One example whose tool and parameter names come from the registry.

    A root compile shows a child ``$ref`` and the edge that makes that child
    an ancestor. Repair prompts do not. A parent that already has a ``$ref``
    is copied, and ``example_src`` is not added. Copied ``example_`` ids are
    a compile error, not a rewrite of the ``$ref``.
    """

    tools = registry.as_openai_tools()
    if not tools:
        return None
    function = tools[0]["function"]
    params = list(function.get("parameters", {}).get("properties", {})) or ["value"]
    outputs = list(node.declared_outputs) or ["value"]
    parent_refs = _parent_ref_strings(node)
    if parent_refs:
        inputs: dict[str, Any] = {params[0]: {"$ref": parent_refs[0]}}
        for name in params[1:]:
            inputs[name] = 1
        return _one_node_example(function["name"], inputs, outputs)
    if repair:
        inputs = {name: index + 1 for index, name in enumerate(params)}
        return _one_node_example(function["name"], inputs, outputs)
    literals = {name: index + 1 for index, name in enumerate(params)}
    consumer: dict[str, Any] = {params[0]: {"$ref": f"example_src.outputs.{outputs[0]}"}}
    for name in params[1:]:
        consumer[name] = 1
    return {
        "nodes": [
            {
                "id": "example_src",
                "name": "example_src",
                "tool_name": function["name"],
                "inputs": literals,
                "declared_outputs": outputs,
                "refine": False,
            },
            {
                "id": "example_dst",
                "name": "example_dst",
                "tool_name": function["name"],
                "inputs": consumer,
                "declared_outputs": outputs,
                "refine": False,
            },
        ],
        "edges": [{"src": "example_src", "dst": "example_dst"}],
    }


def _one_node_example(tool_name: str, inputs: dict[str, Any], outputs: list[str]) -> dict[str, Any]:
    return {
        "nodes": [
            {
                "id": "example_dst",
                "name": "example_dst",
                "tool_name": tool_name,
                "inputs": inputs,
                "declared_outputs": outputs,
                "refine": False,
            }
        ],
        "edges": [],
    }


def _ref_producer_id(value: Any) -> str | None:
    """Producer id from a ``$ref`` object. Malformed refs are left to the compiler."""

    if not isinstance(value, dict) or set(value) != {"$ref"}:
        return None
    raw = value.get("$ref")
    if not isinstance(raw, str) or ".outputs." not in raw:
        return None
    return raw.split(".outputs.", 1)[0]


def _copied_example_ids(spec: Decomposition) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        if value.startswith("example_") and value not in seen:
            seen.add(value)
            found.append(value)

    for child in spec.nodes:
        add(child.id)
        for item in child.inputs.values():
            producer = _ref_producer_id(item)
            if producer is not None:
                add(producer)
    for edge in spec.edges:
        add(edge.src)
        add(edge.dst)
    return found


def _parent_ref_strings(node: TaskNode) -> list[str]:
    found: list[str] = []
    for value in node.inputs.values():
        parsed = parse_ref(value)
        if parsed is not None:
            found.append(f"{parsed.node_id}.outputs.{parsed.field}")
    return found


def _as_decomposition(raw: Any) -> Decomposition:
    if type(raw) is Decomposition:
        return raw
    if isinstance(raw, BaseModel):
        return Decomposition.model_validate(raw.model_dump(by_alias=True))
    return Decomposition.model_validate(raw)


def _decomposition_graph(spec: Decomposition, parent: TaskNode) -> TaskGraph:
    graph = TaskGraph()
    for child in spec.nodes:
        try:
            node = TaskNode(
                id=child.id,
                name=child.name,
                tool_name=child.tool_name,
                inputs=dict(child.inputs),
                declared_outputs=list(child.declared_outputs),
                refine=child.refine,
                parent_id=parent.id,
            )
        except ValidationError as exc:
            raise CompileError(
                f"decomposition node {child.id!r} is not a valid task node: {exc}"
            ) from exc
        graph.add_node(node)
    known = {child.id for child in spec.nodes}
    # Decision 0027. A self-edge is dropped. An internal $ref adds its edge
    # when the model omitted it. The $ref string is not rewritten.
    for edge in spec.edges:
        if edge.src not in known or edge.dst not in known or edge.src == edge.dst:
            continue
        if edge.dst in graph.successors(edge.src):
            continue
        graph.add_edge(edge.src, edge.dst)
    for child in spec.nodes:
        for value in child.inputs.values():
            producer = _ref_producer_id(value)
            if producer is None or producer not in known or producer == child.id:
                continue
            if child.id in graph.successors(producer):
                continue
            graph.add_edge(producer, child.id)
    return graph


def _plan_rejection(exc: BaseException) -> bool:
    if isinstance(exc, (ValidationError, InterfaceError, GraphError, CompileError)):
        return True
    return isinstance(exc, LLMError) and "invalid structured output" in str(exc)


def _failure_text(exc: BaseException, spec: Decomposition | None) -> str:
    text = str(exc)
    if spec is not None and "decomposition=" not in text:
        text = f"{text}; decomposition={spec.model_dump()}"
    return text


def _bump_retries(metrics: Metrics | None) -> None:
    if metrics is not None:
        metrics.compile_retries += 1


def _reported_retries(metrics: Metrics | None, local_retries: int) -> int:
    if metrics is None:
        return local_retries
    return metrics.compile_retries
