import sys
import os
import asyncio

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MOCK_MODE"] = "true"

from src.agent.brain import get_agent


async def main():
    agent = get_agent()
    session_id = "test_stream"

    print("=" * 60)
    print("测试：创建一个会议纪要文档")
    print("=" * 60)

    tool_events = []
    text_chunks = []

    async for chunk in agent.astream("帮我创建一个会议纪要文档", session_id):
        if chunk.startswith("\x00TOOL_START:"):
            tool_name = chunk[len("\x00TOOL_START:"):]
            tool_events.append(("START", tool_name))
            print(f"  [工具调用] → {tool_name}")
        elif chunk == "\x00TOOL_END":
            tool_events.append(("END", None))
            print(f"  [工具完成]")
        else:
            text_chunks.append(chunk)

    print(f"\n工具事件总数: {len(tool_events)}")
    print(f"文本 chunk 总数: {len(text_chunks)}")

    tool_names = [e[1] for e in tool_events if e[0] == "START"]
    print(f"调用的工具: {tool_names}")

    print("\n" + "=" * 60)
    print("测试：搜索文档")
    print("=" * 60)

    tool_events2 = []
    text_chunks2 = []

    async for chunk in agent.astream("搜索一下会议纪要相关的文档", session_id):
        if chunk.startswith("\x00TOOL_START:"):
            tool_name = chunk[len("\x00TOOL_START:"):]
            tool_events2.append(("START", tool_name))
            print(f"  [工具调用] → {tool_name}")
        elif chunk == "\x00TOOL_END":
            tool_events2.append(("END", None))
            print(f"  [工具完成]")
        else:
            text_chunks2.append(chunk)

    print(f"\n工具事件总数: {len(tool_events2)}")
    print(f"文本 chunk 总数: {len(text_chunks2)}")

    tool_names2 = [e[1] for e in tool_events2 if e[0] == "START"]
    print(f"调用的工具: {tool_names2}")

    print("\n" + "=" * 60)
    print("测试：删除文档")
    print("=" * 60)

    tool_events3 = []
    text_chunks3 = []

    async for chunk in agent.astream("帮我删除文档 doc_test123", session_id):
        if chunk.startswith("\x00TOOL_START:"):
            tool_name = chunk[len("\x00TOOL_START:"):]
            tool_events3.append(("START", tool_name))
            print(f"  [工具调用] → {tool_name}")
        elif chunk == "\x00TOOL_END":
            tool_events3.append(("END", None))
            print(f"  [工具完成]")
        else:
            text_chunks3.append(chunk)

    print(f"\n工具事件总数: {len(tool_events3)}")
    print(f"文本 chunk 总数: {len(text_chunks3)}")

    tool_names3 = [e[1] for e in tool_events3 if e[0] == "START"]
    print(f"调用的工具: {tool_names3}")

    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"创建文档 - 工具调用: {len(tool_names)}次, 文本输出: {len(text_chunks)}个chunk")
    print(f"搜索文档 - 工具调用: {len(tool_names2)}次, 文本输出: {len(text_chunks2)}个chunk")
    print(f"删除文档 - 工具调用: {len(tool_names3)}次, 文本输出: {len(text_chunks3)}个chunk")


if __name__ == "__main__":
    asyncio.run(main())
