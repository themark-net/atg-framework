import pytest
from pydantic import BaseModel

from atg.llm import LLMError, MockLLMClient, coerce_structured, extract_json


class Answer(BaseModel):
    value: int


def test_mock_keyed_by_node_id_consumes_lists():
    llm = MockLLMClient(
        structured={"a": [{"value": 1}, {"value": 2}], "b": {"value": 9}}
    )
    assert llm.complete_structured([], Answer, context={"node_id": "a"}).value == 1
    assert llm.complete_structured([], Answer, context={"node_id": "a"}).value == 2
    # last scripted answer for a key is sticky
    assert llm.complete_structured([], Answer, context={"node_id": "a"}).value == 2
    assert llm.complete_structured([], Answer, context={"node_id": "b"}).value == 9
    with pytest.raises(LLMError):
        llm.complete_structured([], Answer, context={"node_id": "missing"})
    assert len(llm.calls) == 5


def test_mock_sequence_and_callable():
    seq = MockLLMClient(structured=[Answer(value=3), '{"value": 4}'])
    assert seq.complete_structured([], Answer).value == 3
    assert seq.complete_structured([], Answer).value == 4
    with pytest.raises(LLMError):
        seq.complete_structured([], Answer)

    fn = MockLLMClient(
        structured=lambda messages, schema, ctx: {"value": len(messages)}
    )
    assert fn.complete_structured([{"role": "user", "content": "x"}], Answer).value == 1


def test_mock_text_and_errors():
    llm = MockLLMClient(text=["hello"])
    assert llm.complete([]) == "hello"
    with pytest.raises(LLMError):
        llm.complete([])
    with pytest.raises(LLMError):
        MockLLMClient().complete_structured([], Answer)


def test_coerce_structured_handles_fenced_json_and_validation():
    raw = 'Sure! Here you go:\n```json\n{"value": 7}\n```'
    assert coerce_structured(raw, Answer).value == 7
    assert extract_json('prefix {"value": 1} suffix') == '{"value": 1}'
    with pytest.raises(LLMError):
        coerce_structured({"value": "not-an-int"}, Answer)
