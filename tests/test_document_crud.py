"""
文档增删查改测试用例
测试 note_tools.py 中的文档操作功能
"""

import sys
import os

# 设置标准输出编码为UTF-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置模拟模式环境变量
os.environ["MOCK_MODE"] = "true"

from src.tools.note_tools import (
    create_document,
    get_document,
    update_document,
    append_to_document,
    delete_document,
    search_documents,
)


def test_create_document():
    """测试创建文档"""
    print("=" * 60)
    print("测试: 创建文档")
    print("=" * 60)
    
    # 测试用例 1: 创建空文档
    print("\n[用例1] 创建空文档")
    result = create_document.invoke({"title": "测试文档"})
    print(f"结果: {result}")
    assert "文档创建成功" in result, "创建文档失败"
    assert "文档ID" in result, "返回结果缺少文档ID"
    print("✓ 测试通过")
    
    # 测试用例 2: 创建带内容的文档
    print("\n[用例2] 创建带内容的文档")
    result = create_document.invoke({
        "title": "带内容的测试文档",
        "content": "# 这是测试内容\n\n这是一段测试文字。"
    })
    print(f"结果: {result}")
    assert "文档创建成功" in result, "创建带内容文档失败"
    print("✓ 测试通过")
    
    # 测试用例 3: 创建空标题文档（边界情况）
    print("\n[用例3] 创建空标题文档")
    result = create_document.invoke({"title": ""})
    print(f"结果: {result}")
    # 空标题应该也能创建成功（由API决定是否允许）
    print("✓ 测试通过")
    
    return True


def test_get_document():
    """测试获取文档"""
    print("\n" + "=" * 60)
    print("测试: 获取文档")
    print("=" * 60)
    
    # 测试用例 1: 获取存在的文档
    print("\n[用例1] 获取文档")
    result = get_document.invoke({"document_id": "doc_test123"})
    print(f"结果: {result}")
    assert "#" in result, "返回结果应包含标题格式"
    assert "模拟文档" in result, "返回结果应包含文档标题"
    print("✓ 测试通过")
    
    # 测试用例 2: 获取不同ID的文档
    print("\n[用例2] 获取不同ID的文档")
    result = get_document.invoke({"document_id": "doc_abc456"})
    print(f"结果: {result}")
    assert "模拟文档" in result, "返回结果应包含文档标题"
    print("✓ 测试通过")
    
    return True


def test_update_document():
    """测试更新文档"""
    print("\n" + "=" * 60)
    print("测试: 更新文档")
    print("=" * 60)
    
    # 测试用例 1: 更新文档内容
    print("\n[用例1] 更新文档内容")
    result = update_document.invoke({
        "document_id": "doc_test123",
        "content": "# 更新后的内容\n\n这是更新后的文档内容。"
    })
    print(f"结果: {result}")
    assert "文档更新成功" in result, "更新文档失败"
    assert "doc_test123" in result, "返回结果应包含文档ID"
    print("✓ 测试通过")
    
    # 测试用例 2: 更新为空内容
    print("\n[用例2] 更新为空内容")
    result = update_document.invoke({
        "document_id": "doc_test123",
        "content": ""
    })
    print(f"结果: {result}")
    assert "文档更新成功" in result, "更新为空内容应成功"
    print("✓ 测试通过")
    
    # 测试用例 3: 更新大量内容
    print("\n[用例3] 更新大量内容")
    large_content = "这是一段很长的内容。\n" * 100
    result = update_document.invoke({
        "document_id": "doc_test123",
        "content": large_content
    })
    print(f"结果: {result}")
    assert "文档更新成功" in result, "更新大量内容失败"
    print("✓ 测试通过")
    
    return True


def test_append_to_document():
    """测试追加文档内容"""
    print("\n" + "=" * 60)
    print("测试: 追加文档内容")
    print("=" * 60)
    
    # 测试用例 1: 追加内容
    print("\n[用例1] 追加内容")
    result = append_to_document.invoke({
        "document_id": "doc_test123",
        "content": "\n\n## 新增章节\n\n这是追加的内容。"
    })
    print(f"结果: {result}")
    assert "内容追加成功" in result, "追加内容失败"
    assert "doc_test123" in result, "返回结果应包含文档ID"
    print("✓ 测试通过")
    
    # 测试用例 2: 追加空内容
    print("\n[用例2] 追加空内容")
    result = append_to_document.invoke({
        "document_id": "doc_test123",
        "content": ""
    })
    print(f"结果: {result}")
    assert "内容追加成功" in result, "追加空内容应成功"
    print("✓ 测试通过")
    
    return True


def test_delete_document():
    """测试删除文档"""
    print("\n" + "=" * 60)
    print("测试: 删除文档")
    print("=" * 60)
    
    # 测试用例 1: 未确认时返回确认提示
    print("\n[用例1] 未确认删除（应返回确认提示）")
    result = delete_document.invoke({"document_id": "doc_test123"})
    print(f"结果: {result}")
    assert "即将删除" in result, "未确认时应返回确认提示"
    print("✓ 测试通过")
    
    # 测试用例 2: 确认后删除
    print("\n[用例2] 确认删除")
    result = delete_document.invoke({"document_id": "doc_test123", "confirm": True})
    print(f"结果: {result}")
    assert "文档删除成功" in result, "确认删除失败"
    assert "doc_test123" in result, "返回结果应包含文档ID"
    print("✓ 测试通过")
    
    # 测试用例 3: 删除另一个文档
    print("\n[用例3] 确认删除另一个文档")
    result = delete_document.invoke({"document_id": "doc_abc456", "confirm": True})
    print(f"结果: {result}")
    assert "文档删除成功" in result, "删除文档失败"
    print("✓ 测试通过")
    
    return True


def test_search_documents():
    """测试搜索文档"""
    print("\n" + "=" * 60)
    print("测试: 搜索文档")
    print("=" * 60)
    
    # 测试用例 1: 搜索文档
    print("\n[用例1] 搜索文档")
    result = search_documents.invoke({"query": "测试"})
    print(f"结果: {result}")
    assert "找到" in result, "搜索结果应包含找到的文档数量"
    assert "搜索结果" in result, "搜索结果应包含文档标题"
    print("✓ 测试通过")
    
    # 测试用例 2: 搜索不同关键词
    print("\n[用例2] 搜索不同关键词")
    result = search_documents.invoke({"query": "会议纪要"})
    print(f"结果: {result}")
    assert "找到" in result, "搜索结果应包含找到的文档数量"
    print("✓ 测试通过")
    
    # 测试用例 3: 指定返回数量
    print("\n[用例3] 指定返回数量")
    result = search_documents.invoke({"query": "文档", "count": 5})
    print(f"结果: {result}")
    assert "找到" in result, "搜索结果应包含找到的文档数量"
    print("✓ 测试通过")
    
    return True


def test_full_crud_workflow():
    """测试完整的CRUD工作流"""
    print("\n" + "=" * 60)
    print("测试: 完整CRUD工作流")
    print("=" * 60)
    
    # 步骤1: 创建文档
    print("\n[步骤1] 创建文档")
    create_result = create_document.invoke({
        "title": "CRUD测试文档",
        "content": "# 初始内容\n\n这是初始内容。"
    })
    print(f"创建结果: {create_result}")
    assert "文档创建成功" in create_result
    
    # 提取文档ID（模拟模式下）
    doc_id = None
    for line in create_result.split("\n"):
        if "文档ID:" in line:
            doc_id = line.split(":")[-1].strip()
            break
    
    if not doc_id:
        print("⚠ 无法提取文档ID，使用默认值")
        doc_id = "doc_test_crud"
    
    print(f"文档ID: {doc_id}")
    
    # 步骤2: 获取文档
    print("\n[步骤2] 获取文档")
    get_result = get_document.invoke({"document_id": doc_id})
    print(f"获取结果: {get_result}")
    assert "模拟文档" in get_result
    
    # 步骤3: 更新文档
    print("\n[步骤3] 更新文档")
    update_result = update_document.invoke({
        "document_id": doc_id,
        "content": "# 更新后的内容\n\n这是更新后的完整内容。"
    })
    print(f"更新结果: {update_result}")
    assert "文档更新成功" in update_result
    
    # 步骤4: 追加内容
    print("\n[步骤4] 追加内容")
    append_result = append_to_document.invoke({
        "document_id": doc_id,
        "content": "\n\n## 追加的章节\n\n这是追加的内容。"
    })
    print(f"追加结果: {append_result}")
    assert "内容追加成功" in append_result
    
    # 步骤5: 搜索文档
    print("\n[步骤5] 搜索文档")
    search_result = search_documents.invoke({"query": "CRUD"})
    print(f"搜索结果: {search_result}")
    assert "找到" in search_result
    
    # 步骤6: 删除文档（先确认再删除）
    print("\n[步骤6] 删除文档")
    delete_result = delete_document.invoke({"document_id": doc_id})
    print(f"确认提示: {delete_result}")
    assert "即将删除" in delete_result
    
    delete_result = delete_document.invoke({"document_id": doc_id, "confirm": True})
    print(f"删除结果: {delete_result}")
    assert "文档删除成功" in delete_result
    
    print("\n✓ 完整CRUD工作流测试通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("飞书CLI笔记工具 - 文档增删查改测试")
    print("=" * 80)
    
    test_results = []
    
    # 运行各个测试
    tests = [
        ("创建文档", test_create_document),
        ("获取文档", test_get_document),
        ("更新文档", test_update_document),
        ("追加文档内容", test_append_to_document),
        ("删除文档", test_delete_document),
        ("搜索文档", test_search_documents),
        ("完整CRUD工作流", test_full_crud_workflow),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ 测试失败: {test_name}")
            print(f"  错误: {str(e)}")
            test_results.append((test_name, False))
    
    # 打印测试总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！文档增删查改功能正常工作。")
    else:
        print("\n⚠ 部分测试失败，请检查代码。")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
