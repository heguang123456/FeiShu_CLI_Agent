"""
测试Agent初始化
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_agent_init():
    """测试Agent初始化"""
    print("测试Agent初始化...")
    
    try:
        from src.config.settings import get_settings
        settings = get_settings()
        print(f"[OK] 配置加载成功")
        print(f"  - API Key: {settings.openai_api_key[:10]}...")
        print(f"  - Model: {settings.openai_model_name}")
    except Exception as e:
        print(f"[FAIL] 配置加载失败: {e}")
        return
    
    try:
        from src.agent.brain import NoteAgent
        agent = NoteAgent()
        print(f"[OK] Agent初始化成功")
        print(f"  - 工具数量: {len(agent.tools)}")
        print(f"  - Agent类型: {type(agent.agent)}")
    except Exception as e:
        print(f"[FAIL] Agent初始化失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_init()
