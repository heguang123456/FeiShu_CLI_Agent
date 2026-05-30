"""
飞书CLI笔记智能体 (NoteAgent) 主入口
命令行交互界面
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme
from rich.live import Live
from rich.spinner import Spinner

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings, FeishuAuthError, FeishuAPIError
from src.agent.brain import get_agent

# 自定义主题
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "user": "bold blue",
    "assistant": "bold green",
})

console = Console(theme=custom_theme)


def setup_logging():
    """配置日志"""
    settings = get_settings()
    
    # 创建日志目录
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(settings.log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )


def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           📝 飞书CLI笔记智能体 (NoteAgent) 📝               ║
║                                                              ║
║    基于 LangChain 和飞书CLI 的智能笔记管理助手              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="info")
    
    help_text = """
[bold]可用命令:[/bold]
  • 直接输入问题或指令，与AI助手对话
  • [cyan]/help[/cyan] - 显示帮助信息
  • [cyan]/tools[/cyan] - 显示可用工具列表
  • [cyan]/history[/cyan] - 显示对话历史
  • [cyan]/clear[/cyan] - 清除对话历史
  • [cyan]/quit[/cyan] 或 [cyan]/exit[/cyan] - 退出程序

[bold]示例:[/bold]
  • "帮我创建一个会议纪要文档"
  • "搜索关于项目进度的群聊消息"
  • "把这段内容整理成周报"
  • "分析一下这个文档的要点"
"""
    console.print(Panel(help_text, title="帮助信息", border_style="cyan"))


def print_tools(agent):
    """打印可用工具列表"""
    tools = agent.get_tool_descriptions()
    
    console.print("\n[bold]可用工具列表:[/bold]\n")
    
    for i, tool in enumerate(tools, 1):
        console.print(f"[cyan]{i}. {tool['name']}[/cyan]")
        console.print(f"   {tool['description'][:100]}...")
        console.print()


def print_history(agent, session_id: str):
    """打印对话历史"""
    history = agent.get_history(session_id)
    
    if not history:
        console.print("[yellow]暂无对话历史[/yellow]")
        return
    
    console.print("\n[bold]对话历史:[/bold]\n")
    
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        
        if role == "user":
            console.print(f"[user]👤 用户:[/user]")
            console.print(f"   {content}\n")
        else:
            console.print(f"[assistant]🤖 助手:[/assistant]")
            console.print(Markdown(content))
            console.print()


async def process_input_streaming(agent, user_input: str, session_id: str):
    """流式处理用户输入"""
    full_response = ""
    live_context = None
    
    with Live(console=console, refresh_per_second=10) as live:
        live_context = live
        try:
            async for chunk in agent.astream(user_input, session_id):
                if chunk.startswith("\x00TOOL_START:"):
                    tool_name = chunk[len("\x00TOOL_START:"):]
                    live.stop()
                    console.print(f"[dim] → 正在使用工具: {tool_name}[/dim]")
                    live.start()
                elif chunk == "\x00TOOL_END":
                    pass
                else:
                    full_response += chunk
                    live.update(Markdown(full_response))
        except Exception as e:
            live.update(f"[error]错误: {str(e)}[/error]")
    
    return full_response


def process_input_sync(agent, user_input: str, session_id: str):
    """同步处理用户输入"""
    with console.status("[bold green]思考中...", spinner="dots"):
        response = agent.run(user_input, session_id)
    return response


def main():
    """主函数"""
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 打印横幅
    print_banner()
    
    # 初始化Agent
    console.print("[info]正在初始化NoteAgent...[/info]")
    
    try:
        agent = get_agent()
        console.print("[success]✓ NoteAgent初始化成功[/success]\n")
    except Exception as e:
        console.print(f"[error]✗ NoteAgent初始化失败: {str(e)}[/error]")
        console.print("[warning]请检查配置文件 .env 是否正确设置[/warning]")
        return
    
    # 会话ID
    session_id = "default"
    
    # 主循环
    while True:
        try:
            # 获取用户输入
            user_input = Prompt.ask("\n[bold blue]👤 您[/bold blue]")
            
            # 跳过空输入
            if not user_input.strip():
                continue
            
            # 处理退出命令（支持带/和不带/的格式）
            command = user_input.lower().strip()
            if command in ["quit", "exit", "/quit", "/exit"]:
                console.print("\n[info]再见！期待下次与您合作！👋[/info]")
                break
            
            # 处理其他命令
            if user_input.startswith("/"):
                if command == "/help":
                    print_banner()
                    continue
                
                elif command == "/tools":
                    print_tools(agent)
                    continue
                
                elif command == "/history":
                    print_history(agent, session_id)
                    continue
                
                elif command == "/clear":
                    agent.clear_history(session_id)
                    console.print("[success]✓ 对话历史已清除[/success]")
                    continue
                
                else:
                    console.print(f"[warning]未知命令: {command}[/warning]")
                    console.print("[info]输入 /help 查看可用命令[/info]")
                    continue
            
            # 处理普通输入
            console.print()  # 空行
            
            # 尝试流式输出
            try:
                response = asyncio.run(process_input_streaming(agent, user_input, session_id))
            except Exception:
                # 降级到同步处理
                response = process_input_sync(agent, user_input, session_id)
                console.print(Markdown(response))
            
            console.print()  # 空行
            
        except KeyboardInterrupt:
            console.print("\n\n[info]检测到中断，正在退出...[/info]")
            break
        
        except FeishuAuthError as e:
            console.print(f"\n[error]飞书认证错误: {str(e)}[/error]")
            console.print("[warning]请执行 'lark-cli auth login' 重新登录[/warning]")
        
        except FeishuAPIError as e:
            console.print(f"\n[error]飞书API错误: {str(e)}[/error]")
        
        except Exception as e:
            logger.error(f"处理输入时出错: {str(e)}", exc_info=True)
            console.print(f"\n[error]处理出错: {str(e)}[/error]")
            console.print("[info]请重试或输入其他问题[/info]")


if __name__ == "__main__":
    main()