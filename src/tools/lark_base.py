"""
飞书CLI底层封装模块
封装subprocess执行lark-cli的底层方法
"""

import json
import subprocess
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

from ..config.settings import get_settings, handle_feishu_error, FeishuAPIError

logger = logging.getLogger(__name__)


@dataclass
class CLIResult:
    """CLI执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    raw_output: Optional[str] = None


class MockLarkCLI:
    """模拟飞书CLI（用于测试）"""
    
    def __init__(self):
        self.settings = get_settings()
        logger.info("使用模拟模式（MockLarkCLI）")
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())[:8]
    
    def execute_command(self, command: str, args: List[str] = None, json_output: bool = True, timeout: int = 30) -> CLIResult:
        logger.info(f"[模拟] 执行命令: {command} {args}")
        return CLIResult(success=True, data={"mock": True, "command": command})
    
    def create_document(self, title: str, folder_token: str = None) -> CLIResult:
        doc_id = self._generate_id()
        logger.info(f"[模拟] 创建文档: {title}")
        return CLIResult(
            success=True,
            data={
                "document_id": f"doc_{doc_id}",
                "title": title,
                "url": "(模拟模式 - 链接不可用)",
                "created_at": datetime.now().isoformat()
            }
        )
    
    def get_document(self, document_id: str) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "document_id": document_id,
                "title": "模拟文档",
                "content": "# 模拟文档内容\n\n这是一个模拟的飞书文档，用于测试。",
                "updated_at": datetime.now().isoformat()
            }
        )
    
    def update_document(self, document_id: str, content: str) -> CLIResult:
        logger.info(f"[模拟] 更新文档 {document_id}")
        return CLIResult(success=True, data={"document_id": document_id, "updated": True})
    
    def append_to_document(self, document_id: str, content: str) -> CLIResult:
        logger.info(f"[模拟] 追加内容到文档 {document_id}")
        return CLIResult(success=True, data={"document_id": document_id, "appended": True})
    
    def delete_document(self, document_id: str) -> CLIResult:
        logger.info(f"[模拟] 删除文档 {document_id}")
        return CLIResult(success=True, data={"document_id": document_id, "deleted": True})
    
    def search_documents(self, query: str, count: int = 10) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"document_id": f"doc_{self._generate_id()}", "title": f"搜索结果: {query} (1)"},
                    {"document_id": f"doc_{self._generate_id()}", "title": f"搜索结果: {query} (2)"}
                ],
                "total": 2
            }
        )
    
    def search_messages(self, query: str, chat_id: str = None, start_time: str = None, end_time: str = None, count: int = 20) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"message_id": f"msg_{self._generate_id()}", "content": f"关于「{query}」的消息1", "sender": {"name": "张三"}, "chat_name": "项目群", "create_time": "2026-05-29 10:00"},
                    {"message_id": f"msg_{self._generate_id()}", "content": f"关于「{query}」的消息2", "sender": {"name": "李四"}, "chat_name": "技术群", "create_time": "2026-05-29 11:00"}
                ],
                "total": 2
            }
        )
    
    def get_chat_messages(self, chat_id: str, start_time: str = None, end_time: str = None, count: int = 50) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "chat_id": chat_id,
                "items": [
                    {"message_id": f"msg_{self._generate_id()}", "content": "大家好，今天的会议讨论一下项目进度", "sender": {"name": "王五"}, "create_time": "2026-05-29 09:00"},
                    {"message_id": f"msg_{self._generate_id()}", "content": "好的，我来汇报一下本周的工作", "sender": {"name": "赵六"}, "create_time": "2026-05-29 09:01"}
                ],
                "total": 2
            }
        )
    
    def list_bitables(self, folder_token: str = None) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"app_token": f"bascn{self._generate_id()}", "name": "项目管理表"},
                    {"app_token": f"bascn{self._generate_id()}", "name": "任务跟踪表"}
                ]
            }
        )
    
    def get_bitable_records(self, app_token: str, table_id: str, filter_expr: str = None, sort: str = None, count: int = 100) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"record_id": f"rec_{self._generate_id()}", "fields": {"任务名称": "完成文档编写", "状态": "进行中", "负责人": "张三"}},
                    {"record_id": f"rec_{self._generate_id()}", "fields": {"任务名称": "代码审查", "状态": "已完成", "负责人": "李四"}}
                ],
                "total": 2
            }
        )
    
    def create_bitable_record(self, app_token: str, table_id: str, fields: Dict[str, Any]) -> CLIResult:
        logger.info(f"[模拟] 创建多维表格记录: {fields}")
        return CLIResult(success=True, data={"record_id": f"rec_{self._generate_id()}", "created": True})
    
    def search_knowledge_base(self, query: str, space_id: str = None, count: int = 10) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"node_token": f"node_{self._generate_id()}", "title": f"知识库文章: {query}", "space_id": "space_001"},
                    {"node_token": f"node_{self._generate_id()}", "title": f"相关文档: {query}", "space_id": "space_001"}
                ],
                "total": 2
            }
        )
    
    def get_knowledge_article(self, node_token: str) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "node_token": node_token,
                "title": "知识库文章",
                "content": "# 知识库文章\n\n这是一篇模拟的知识库文章内容。",
                "updated_at": datetime.now().isoformat()
            }
        )
    
    def get_minutes(self, meeting_id: str) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "meeting_id": meeting_id,
                "title": "项目周会",
                "date": "2026-05-29",
                "participants": ["张三", "李四", "王五"],
                "transcript": "张三: 大家好，今天我们讨论一下项目进度。\n李四: 好的，我来汇报一下本周的工作...\n王五: 我这边遇到了一些问题..."
            }
        )
    
    def search_minutes(self, query: str, start_time: str = None, end_time: str = None, count: int = 10) -> CLIResult:
        return CLIResult(
            success=True,
            data={
                "items": [
                    {"meeting_id": f"meet_{self._generate_id()}", "title": f"会议: {query}", "date": "2026-05-29"},
                    {"meeting_id": f"meet_{self._generate_id()}", "title": f"讨论: {query}", "date": "2026-05-28"}
                ],
                "total": 2
            }
        )
    
    def check_auth(self) -> CLIResult:
        return CLIResult(success=True, data="模拟模式：已认证", raw_output="Mock mode: authenticated")
    
    def login(self) -> CLIResult:
        return CLIResult(success=True, data="模拟模式：已登录", raw_output="Mock mode: logged in")


class LarkCLI:
    """飞书CLI封装类"""
    
    def __init__(self, cli_path: str = "lark-cli"):
        self.cli_path = cli_path
        self.settings = get_settings()
    
    def execute_command(
        self,
        command: str,
        args: List[str] = None,
        json_output: bool = True,
        timeout: int = 30
    ) -> CLIResult:
        """
        执行lark-cli命令
        
        Args:
            command: 主命令（如 doc, bitable, chat）
            args: 子命令和参数列表
            json_output: 是否解析JSON输出
            timeout: 超时时间（秒）
        
        Returns:
            CLIResult对象
        """
        cmd = [self.cli_path, command]
        if args:
            cmd.extend(args)
        
        if json_output:
            cmd.append("--json")
        
        logger.debug(f"执行命令: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8"
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                logger.error(f"命令执行失败: {error_msg}")
                try:
                    handle_feishu_error(Exception(error_msg))
                except Exception:
                    pass
                return CLIResult(
                    success=False,
                    data=None,
                    error=error_msg,
                    raw_output=result.stdout
                )
            
            output = result.stdout.strip()
            
            if json_output and output:
                try:
                    data = json.loads(output)
                    return CLIResult(
                        success=True,
                        data=data,
                        raw_output=output
                    )
                except json.JSONDecodeError:
                    logger.warning("JSON解析失败，返回原始输出")
                    return CLIResult(
                        success=True,
                        data=output,
                        raw_output=output
                    )
            
            return CLIResult(
                success=True,
                data=output,
                raw_output=output
            )
            
        except subprocess.TimeoutExpired:
            error_msg = f"命令执行超时（{timeout}秒）"
            logger.error(error_msg)
            return CLIResult(success=False, data=None, error=error_msg)
            
        except FileNotFoundError:
            error_msg = f"未找到lark-cli命令: {self.cli_path}"
            logger.error(error_msg)
            try:
                handle_feishu_error(Exception("command not found"))
            except Exception:
                pass
            return CLIResult(success=False, data=None, error=error_msg)
            
        except Exception as e:
            error_msg = f"命令执行异常: {str(e)}"
            logger.error(error_msg)
            return CLIResult(success=False, data=None, error=error_msg)
    
    # ==================== 文档操作 ====================
    
    def create_document(self, title: str, folder_token: str = None) -> CLIResult:
        """
        创建飞书云文档
        
        Args:
            title: 文档标题
            folder_token: 文件夹token（可选）
        
        Returns:
            包含document_id的结果
        """
        args = ["create", "--title", title]
        if folder_token:
            args.extend(["--folder", folder_token])
        
        return self.execute_command("doc", args)
    
    def get_document(self, document_id: str) -> CLIResult:
        """
        获取飞书云文档内容
        
        Args:
            document_id: 文档ID
        
        Returns:
            文档内容
        """
        return self.execute_command("doc", ["get", "--id", document_id])
    
    def update_document(self, document_id: str, content: str) -> CLIResult:
        """
        更新飞书云文档内容
        
        Args:
            document_id: 文档ID
            content: 新内容
        
        Returns:
            更新结果
        """
        return self.execute_command(
            "doc",
            ["update", "--id", document_id, "--content", content]
        )
    
    def append_to_document(self, document_id: str, content: str) -> CLIResult:
        """
        向飞书云文档追加内容
        
        Args:
            document_id: 文档ID
            content: 追加的内容
        
        Returns:
            追加结果
        """
        return self.execute_command(
            "doc",
            ["append", "--id", document_id, "--content", content]
        )
    
    def delete_document(self, document_id: str) -> CLIResult:
        """
        删除飞书云文档
        
        Args:
            document_id: 文档ID
        
        Returns:
            删除结果
        """
        return self.execute_command(
            "doc",
            ["delete", "--id", document_id]
        )
    
    def search_documents(self, query: str, count: int = 10) -> CLIResult:
        """
        搜索飞书云文档
        
        Args:
            query: 搜索关键词
            count: 返回数量
        
        Returns:
            搜索结果列表
        """
        return self.execute_command(
            "doc",
            ["search", "--query", query, "--count", str(count)]
        )
    
    # ==================== 消息操作 ====================
    
    def search_messages(
        self,
        query: str,
        chat_id: str = None,
        start_time: str = None,
        end_time: str = None,
        count: int = 20
    ) -> CLIResult:
        """
        搜索飞书消息
        
        Args:
            query: 搜索关键词
            chat_id: 群聊ID（可选）
            start_time: 开始时间（可选，格式：2024-01-01）
            end_time: 结束时间（可选）
            count: 返回数量
        
        Returns:
            搜索结果
        """
        args = ["search", "--query", query, "--count", str(count)]
        
        if chat_id:
            args.extend(["--chat-id", chat_id])
        if start_time:
            args.extend(["--start-time", start_time])
        if end_time:
            args.extend(["--end-time", end_time])
        
        return self.execute_command("message", args)
    
    def get_chat_messages(
        self,
        chat_id: str,
        start_time: str = None,
        end_time: str = None,
        count: int = 50
    ) -> CLIResult:
        """
        获取群聊消息
        
        Args:
            chat_id: 群聊ID
            start_time: 开始时间
            end_time: 结束时间
            count: 返回数量
        
        Returns:
            消息列表
        """
        args = ["list", "--chat-id", chat_id, "--count", str(count)]
        
        if start_time:
            args.extend(["--start-time", start_time])
        if end_time:
            args.extend(["--end-time", end_time])
        
        return self.execute_command("message", args)
    
    # ==================== 多维表格操作 ====================
    
    def list_bitables(self, folder_token: str = None) -> CLIResult:
        """
        列出多维表格
        
        Args:
            folder_token: 文件夹token（可选）
        
        Returns:
            多维表格列表
        """
        args = ["list"]
        if folder_token:
            args.extend(["--folder", folder_token])
        
        return self.execute_command("bitable", args)
    
    def get_bitable_records(
        self,
        app_token: str,
        table_id: str,
        filter_expr: str = None,
        sort: str = None,
        count: int = 100
    ) -> CLIResult:
        """
        获取多维表格记录
        
        Args:
            app_token: 多维表格应用token
            table_id: 数据表ID
            filter_expr: 过滤表达式（可选）
            sort: 排序表达式（可选）
            count: 返回数量
        
        Returns:
            记录列表
        """
        args = [
            "record", "list",
            "--app-token", app_token,
            "--table-id", table_id,
            "--count", str(count)
        ]
        
        if filter_expr:
            args.extend(["--filter", filter_expr])
        if sort:
            args.extend(["--sort", sort])
        
        return self.execute_command("bitable", args)
    
    def create_bitable_record(
        self,
        app_token: str,
        table_id: str,
        fields: Dict[str, Any]
    ) -> CLIResult:
        """
        创建多维表格记录
        
        Args:
            app_token: 多维表格应用token
            table_id: 数据表ID
            fields: 字段数据
        
        Returns:
            创建结果
        """
        fields_json = json.dumps(fields, ensure_ascii=False)
        
        return self.execute_command(
            "bitable",
            [
                "record", "create",
                "--app-token", app_token,
                "--table-id", table_id,
                "--fields", fields_json
            ]
        )
    
    # ==================== 知识库操作 ====================
    
    def search_knowledge_base(
        self,
        query: str,
        space_id: str = None,
        count: int = 10
    ) -> CLIResult:
        """
        搜索知识库
        
        Args:
            query: 搜索关键词
            space_id: 知识空间ID（可选）
            count: 返回数量
        
        Returns:
            搜索结果
        """
        args = ["search", "--query", query, "--count", str(count)]
        
        if space_id:
            args.extend(["--space-id", space_id])
        
        return self.execute_command("wiki", args)
    
    def get_knowledge_article(self, node_token: str) -> CLIResult:
        """
        获取知识库文章
        
        Args:
            node_token: 节点token
        
        Returns:
            文章内容
        """
        return self.execute_command(
            "wiki",
            ["get", "--node-token", node_token]
        )
    
    # ==================== 妙记操作 ====================
    
    def get_minutes(self, meeting_id: str) -> CLIResult:
        """
        获取妙记逐字稿
        
        Args:
            meeting_id: 会议ID
        
        Returns:
            逐字稿内容
        """
        return self.execute_command(
            "minutes",
            ["get", "--meeting-id", meeting_id]
        )
    
    def search_minutes(
        self,
        query: str,
        start_time: str = None,
        end_time: str = None,
        count: int = 10
    ) -> CLIResult:
        """
        搜索妙记
        
        Args:
            query: 搜索关键词
            start_time: 开始时间
            end_time: 结束时间
            count: 返回数量
        
        Returns:
            搜索结果
        """
        args = ["search", "--query", query, "--count", str(count)]
        
        if start_time:
            args.extend(["--start-time", start_time])
        if end_time:
            args.extend(["--end-time", end_time])
        
        return self.execute_command("minutes", args)
    
    # ==================== 认证操作 ====================
    
    def check_auth(self) -> CLIResult:
        """
        检查认证状态
        
        Returns:
            认证状态
        """
        return self.execute_command("auth", ["status"], json_output=False)
    
    def login(self) -> CLIResult:
        """
        登录飞书
        
        Returns:
            登录结果
        """
        return self.execute_command("auth", ["login"], json_output=False)


# 全局CLI单例
_cli: Optional[Union[LarkCLI, MockLarkCLI]] = None


def get_cli() -> Union[LarkCLI, MockLarkCLI]:
    """获取CLI单例（根据配置决定使用真实CLI还是模拟CLI）"""
    global _cli
    if _cli is None:
        settings = get_settings()
        if settings.mock_mode:
            _cli = MockLarkCLI()
        else:
            _cli = LarkCLI()
    return _cli