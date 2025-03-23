import asyncio
from dotenv import load_dotenv
from typing import Any, Dict, List, Union

load_dotenv()

from openai.types.responses import ResponseTextDeltaEvent
from agents import Agent, Runner, StreamEvent, set_default_openai_api, set_tracing_disabled, function_tool
from collections.abc import AsyncIterator

set_tracing_disabled(disabled=True)
set_default_openai_api("chat_completions")


@function_tool
def add(a: int, b: int):
    """Calculate the sum of two number

    Args:
        a (int): _description_
        b (int): _description_
    """
    return a + b


class AgentWorkflow:
    def __init__(self):
        self.agent = Agent(
            name="Joker",
            # model='qwq-32b',
            model='qwen-plus-latest',
            instructions="You are a helpful assistant.",
            tools=[add]
        )

    async def stream_events(self, input: Union[str, List[Dict[str, Any]]]) -> AsyncIterator[StreamEvent]:
        result = Runner.run_streamed(self.agent, input=input)
        async for event in result.stream_events():
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                yield event


async def main():
    agent = AgentWorkflow()
    message = [
        {'role': 'user', 'content': "234+35435等于多少"},
        {'role': 'assistant', 'content': "234+35435等于35669"},
        {'role': 'user', 'content': "那234+35呢"}
    ]
    async for event in agent.stream_events(input=message):
        # print(event)
        print(event.data.delta, end='')
        print()


if __name__ == "__main__":
    asyncio.run(main())
