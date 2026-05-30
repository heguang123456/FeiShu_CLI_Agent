"""
测试导入模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """测试所有模块的导入"""
    print("开始测试导入...")
    
    try:
        from src.config.settings import get_settings, Settings
        print("[OK] src.config.settings 导入成功")
    except Exception as e:
        print(f"[FAIL] src.config.settings 导入失败: {e}")
    
    try:
        from src.tools.lark_base import LarkCLI
        print("[OK] src.tools.lark_base 导入成功")
    except Exception as e:
        print(f"[FAIL] src.tools.lark_base 导入失败: {e}")
    
    try:
        from src.tools.note_tools import create_document, update_document
        print("[OK] src.tools.note_tools 导入成功")
    except Exception as e:
        print(f"[FAIL] src.tools.note_tools 导入失败: {e}")
    
    try:
        from src.tools.res_tools import search_messages, read_bitable
        print("[OK] src.tools.res_tools 导入成功")
    except Exception as e:
        print(f"[FAIL] src.tools.res_tools 导入失败: {e}")
    
    try:
        from src.rag.vector_store import VectorStoreManager
        print("[OK] src.rag.vector_store 导入成功")
    except Exception as e:
        print(f"[FAIL] src.rag.vector_store 导入失败: {e}")
    
    try:
        from src.rag.document_loader import DocumentLoader
        print("[OK] src.rag.document_loader 导入成功")
    except Exception as e:
        print(f"[FAIL] src.rag.document_loader 导入失败: {e}")
    
    try:
        from src.agent.prompts import get_system_prompt, get_chat_prompt
        print("[OK] src.agent.prompts 导入成功")
    except Exception as e:
        print(f"[FAIL] src.agent.prompts 导入失败: {e}")
    
    try:
        from src.agent.brain import NoteAgent
        print("[OK] src.agent.brain 导入成功")
    except Exception as e:
        print(f"[FAIL] src.agent.brain 导入失败: {e}")
    
    print("\n导入测试完成！")

if __name__ == "__main__":
    test_imports()
