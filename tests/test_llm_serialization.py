from gateway.routers.llm import _process_function_calls


class _FailingFunction:
    model_fields = {"arguments"}

    def __init__(self, payload: str):
        self.arguments = payload

    def model_dump(self, *_, **__):
        raise TypeError("MockValSer")


def _failing_model_dump(*_, **__):
    raise TypeError("MockValSer")


class _FailingToolCall:
    model_fields = {"function"}

    def __init__(self, payload: str):
        self.function = _FailingFunction(payload)

    model_dump = _failing_model_dump


class _FailingMessage:
    model_fields = {"function_call", "tool_calls"}

    def __init__(self):
        self.function_call = {"arguments": "{\"alpha\": 1}"}
        self.tool_calls = [_FailingToolCall("{\"beta\": 2}")]

    model_dump = _failing_model_dump


class _FailingChoice:
    model_fields = {"message"}

    def __init__(self):
        self.message = _FailingMessage()

    model_dump = _failing_model_dump


class _FailingResponse:
    model_fields = {"choices"}

    def __init__(self):
        self.choices = [_FailingChoice()]

    model_dump = _failing_model_dump


def test_process_function_calls_handles_model_dump_failure():
    response = _FailingResponse()

    processed = _process_function_calls(response)

    assert processed["choices"][0]["message"]["function_call"]["arguments"] == {"alpha": 1}
    assert processed["choices"][0]["message"]["tool_calls"][0]["function"]["arguments"] == {"beta": 2}
