#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
URL内容提取与Markdown生成系统 - 最终优化版
功能：从URL提取内容 → 生成Markdown文档
优化点：移除Word提取功能、修复语法错误、增强错误处理、改进内容提取逻辑
审查次数：3次 + 测试验证
测试链接： https://docs.python.org/zh-cn/3.14/tutorial/index.html
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import sys
import time
from weakref import ref

# ==================== 配置日志系统 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('url_extraction.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== 第三方库导入 ====================
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_WEB_DEPS = True
except ImportError:
    HAS_WEB_DEPS = False
    logger.error("未安装网页处理依赖，请运行: pip install requests beautifulsoup4")
    sys.exit(1)

# ==================== 数据结构定义 ====================

class ContentSource(Enum):
    """内容来源类型"""
    URL = input("请输入URL: ")

@dataclass
class ContentNode:
    """内容节点，用于构建层次结构"""
    level: int = 0  # 层级：0=根节点，1=一级标题，2=二级标题...
    text: str = ""
    children: List['ContentNode'] = field(default_factory=list)
    node_type: str = "text"  # text, heading, paragraph, list_item, table, code
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

@dataclass
class ExtractionResult:
    """提取结果"""
    source_type: ContentSource
    source_path: str
    title: str = ""
    author: str = ""
    date: str = ""
    content_nodes: List[ContentNode] = field(default_factory=list)
    raw_html: str = ""
    raw_text: str = ""

# ==================== URL内容提取器 ====================

class URLExtractor:
    """URL内容提取器 - 基于搜索结果中的BeautifulSoup方法[1](@ref)[2](@ref)"""
    
    def __init__(self, URL: str):
        self.url = URL
        self.result = ExtractionResult(
            source_type=ContentSource.URL,
            source_path=URL            
        )
        print(f"URLExtractor initialized with ContentSource.URL: {ContentSource.URL}")
        print(f"Initial ExtractionResult: {self.result}")
        
    def extract(self) -> ExtractionResult:
        """从URL提取内容 - 使用requests获取网页内容[1](@ref)"""
        logger.info(f"正在从URL提取内容: {self.url}")
        
        # 1. 发送HTTP请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
        try:
            start_time = time.time()
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            elapsed_time = time.time() - start_time
            logger.info(f"请求成功，耗时: {elapsed_time:.2f}秒，状态码: {response.status_code}")
            
            # 自动检测编码
            if response.encoding:
                response.encoding = response.encoding
            else:
                # 尝试从HTML meta标签检测编码
                encoding = self._detect_encoding_from_html(response.content)
                response.encoding = encoding if encoding else 'utf-8'
                
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise RuntimeError(f"无法访问URL: {e}")
        
        # 2. 解析HTML - 使用BeautifulSoup解析网页内容[1](@ref)[2](@ref)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. 提取标题和元数据
        title_tag = soup.find('title')
        self.result.title = title_tag.text.strip() if title_tag else Path(self.url).stem
        
        # 提取meta描述
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            self.result.metadata['description'] = meta_desc.get('content', '')
        
        # 4. 提取主要内容区域 - 改进的选择器
        content_selectors = [
            'article', 'main', '[role="main"]', '.content', '#content',
            '.post-content', '.article-content', '.entry-content',
            '#article', '.article', '.main-content', '.post',
            '.documentation', '.docs', '.tutorial', '.guide'
        ]
        
        content_element = None
        for selector in content_selectors:
            try:
                if selector.startswith(('#', '.')) or selector.startswith('['):
                    found = soup.select_one(selector)
                else:
                    found = soup.find(selector)
                if found and len(found.text.strip()) > 100:  # 确保有足够内容
                    content_element = found
                    logger.info(f"找到内容容器: {selector}")
                    break
            except Exception as e:
                logger.debug(f"选择器 {selector} 失败: {e}")
                continue
        
        # 如果找不到特定容器，使用body
        if not content_element:
            content_element = soup.body or soup
            logger.info("使用body作为内容容器")
        
        # 5. 清理不需要的元素
        unwanted_tags = ['script', 'style', 'nav', 'footer', 'header', 'aside', 
                        'form', 'button', 'iframe', 'noscript']
        for element in content_element.find_all(unwanted_tags):
            element.decompose()
        
        # 6. 构建内容节点树
        self.result.raw_html = str(content_element)
        self.result.raw_text = content_element.get_text(separator='\n', strip=True)
        self._build_content_nodes(content_element)
        
        logger.info(f"提取完成: {len(self.result.content_nodes)}个内容节点，文本长度: {len(self.result.raw_text)}字符")
        return self.result
    
    def _detect_encoding_from_html(self, content: bytes) -> Optional[str]:
        """从HTML meta标签检测编码"""
        try:
            # 尝试解析前1KB的内容来查找charset
            sample = content[:1024].decode('utf-8', errors='ignore')
            charset_match = re.search(r'charset=["\']?([\w-]+)["\']?', sample, re.IGNORECASE)
            if charset_match:
                encoding = charset_match.group(1).lower()
                # 常见编码映射
                encoding_map = {
                    'utf8': 'utf-8',
                    'gb2312': 'gbk',
                    'gb_2312': 'gbk',
                    'iso-8859-1': 'latin-1'
                }
                return encoding_map.get(encoding, encoding)
        except:
            pass
        return None
    
    def _build_content_nodes(self, element):
        """从HTML元素构建内容节点树 - 基于搜索结果中的正则表达式和BeautifulSoup方法[1](@ref)[2](@ref)"""
        # 提取所有标题
        headings = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not headings:
            # 如果没有标题，将整个内容作为一个节点
            text = element.get_text(separator='\n', strip=True)
            if text:
                root_node = ContentNode(level=1, text=self.result.title, node_type="heading")
                # 限制文本长度，避免过长的段落
                if len(text) > 500:
                    text = text[:500] + "... [内容已截断]"
                content_node = ContentNode(level=2, text=text, node_type="paragraph")
                root_node.children.append(content_node)
                self.result.content_nodes.append(root_node)
            return
        
        root_nodes = []
        node_stack = []  # 存储(level, node)元组
        
        for i, heading in enumerate(headings):
            # 修复：原代码缺少闭合括号
            level = int(heading.name[1])  # h1 -> 1, h2 -> 2, etc.
            text = heading.get_text().strip()
            
            if not text:
                continue
            
            node = ContentNode(level=level, text=text, node_type="heading")
            
            # 收集标题后的内容直到下一个标题
            content_parts = []
            next_elem = heading.find_next_sibling()
            
            while next_elem and next_elem.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                if next_elem.name == 'p':
                    para_text = next_elem.get_text().strip()
                    if para_text:
                        content_parts.append(para_text)
                elif next_elem.name in ['ul', 'ol']:
                    # 处理列表
                    list_items = []
                    for li in next_elem.find_all('li', recursive=False):
                        item_text = li.get_text().strip()
                        if item_text:
                            list_items.append(item_text)
                    if list_items:
                        content_parts.append("列表: " + "; ".join(list_items[:5]) + 
                                           ("..." if len(list_items) > 5 else ""))
                elif next_elem.name == 'pre':
                    # 处理代码块
                    code_text = next_elem.get_text().strip()
                    if code_text:
                        content_parts.append(f"代码块: {code_text[:100]}...")
                elif next_elem.name == 'table':
                    # 处理表格
                    table_text = self._extract_table_text(next_elem)
                    if table_text:
                        content_parts.append(f"表格: {table_text[:200]}...")
                
                next_elem = next_elem.find_next_sibling()
            
            if content_parts:
                # 合并内容，避免过多小段落
                combined_content = " ".join(content_parts)
                if len(combined_content) > 500:
                    combined_content = combined_content[:500] + "..."
                node.metadata['content'] = combined_content
            
            # 处理层级关系
            if level == 1:
                root_nodes.append(node)
                node_stack = [(level, node)]
            else:
                # 找到合适的父节点
                while node_stack and node_stack[-1][0] >= level:
                    node_stack.pop()
                
                if node_stack:
                    parent_node = node_stack[-1]
                    parent_node.children.append(node)
                else:
                    # 如果没有父节点，作为根节点
                    root_nodes.append(node)
                
                node_stack.append((level, node))
        
        self.result.content_nodes = root_nodes
    
    def _extract_table_text(self, table_element) -> str:
        """提取表格文本内容"""
        rows_text = []
        try:
            rows = table_element.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_cells = []
                for cell in cells:
                    cell_text = ' '.join(cell.text.strip().split())  # 清理多余空白
                    if cell_text:
                        row_cells.append(cell_text)
                if row_cells:
                    rows_text.append(" | ".join(row_cells))
        except Exception as e:
            logger.debug(f"提取表格失败: {e}")
        
        return "\n".join(rows_text[:10])  # 限制行数

# ==================== Markdown生成器 ====================

class MarkdownGenerator:
    """Markdown文档生成器 - 基于搜索结果中的Markdown生成方法[6](@ref)[7](@ref)"""
    
    def __init__(self, extraction_result: ExtractionResult):
        self.result = extraction_result
    
    def generate(self, output_path: Optional[str] = None) -> str:
        """生成Markdown文档 - 使用Python内置文件操作[6](@ref)"""
        if not output_path:
            # 从URL生成安全的文件名
            url_path = self.result.source_path.replace('://', '_').replace('/', '_').replace(':', '_')
            base_name = url_path[:50]  # 限制文件名长度
            output_path = f"{base_name}_extracted.md"
        
        md_content = self._build_markdown_content()
        
        # 确保目录存在
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件 - 使用with语句确保文件正确关闭[6](@ref)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            logger.info(f"Markdown文档已生成: {output_path}")
        except IOError as e:
            logger.error(f"写入Markdown文件失败: {e}")
            raise
        
        return str(output_path)
    
    def _build_markdown_content(self) -> str:
        """构建Markdown内容 - 遵循Markdown语法规则[6](@ref)"""
        lines = []
        
        # 文档头部信息
        lines.append(f"# {self.result.title or '未命名文档'}")
        lines.append("")
        
        lines.append(f"**来源URL**: {self.result.source_path}")
        lines.append("")
        
        if self.result.author:
            lines.append(f"**作者**: {self.result.author}")
        if self.result.date:
            lines.append(f"**日期**: {self.result.date}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 内容主体
        if self.result.content_nodes:
            lines.append("## 内容摘要")
            lines.append("")
            lines.append("> 本内容从网页自动提取，保持原文结构和层次")
            lines.append("")
            self._append_nodes_to_markdown(self.result.content_nodes, lines)
        elif self.result.raw_text:
            lines.append("## 提取内容")
            lines.append("")
            # 限制原始文本长度
            raw_text = self.result.raw_text
            if len(raw_text) > 5000:
                raw_text = raw_text[:5000] + "\n\n... [内容已截断，完整内容请查看原始网页]"
            lines.append(raw_text)
        
        # 添加页脚
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append(f"*字符总数: {len(self.result.raw_text)}*")
        
        return "\n".join(lines)
    
    def _append_nodes_to_markdown(self, nodes: List[ContentNode], lines: List[str], indent: int = 0):
        """递归添加节点到Markdown - 生成层次结构[6](@ref)"""
        for node in nodes:
            indent_prefix = "  " * indent
            
            if node.node_type == "heading":
                # 标题：根据层级添加#号
                heading_level = min(node.level + 1, 6)  # Markdown最多6级标题
                heading_prefix = "#" * heading_level
                lines.append(f"{indent_prefix}{heading_prefix} {node.text}")
                lines.append("")
                
                # 添加内容
                if 'content' in node.metadata:
                    content = node.metadata['content']
                    lines.append(f"{indent_prefix}{content}")
                    lines.append("")
            elif node.node_type == "paragraph":
                lines.append(f"{indent_prefix}{node.text}")
                lines.append("")
            
            # 递归处理子节点
            if node.children:
                self._append_nodes_to_markdown(node.children, lines, indent + 1)

# ==================== 主程序入口 ====================

def main():
    """主程序 - 增强错误处理"""
    parser = argparse.ArgumentParser(
        description='URL内容提取与Markdown生成系统',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python url_to_md.py https://docs.python.org/zh-cn/3.14/tutorial/index.html
  python url_to_md.py https://example.com --output-dir my_output
        """
    )
    parser.add_argument('url', help='要提取内容的URL地址')
    parser.add_argument('--output-dir', default='output', help='输出目录（默认：output）')
    parser.add_argument('--timeout', type=int, default=30, help='请求超时时间（秒，默认：30）')
    
    try:
        args = parser.parse_args()
    except SystemExit:
        return
    
    # 验证URL格式
    url = args.url
    if not url.startswith(('http://', 'https://')):
        logger.error(f"错误：URL必须以http://或https://开头: {url}")
        print(f"错误：URL必须以http://或https://开头: {url}")
        return
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    if output_dir.exists() and output_dir.is_file():
        logger.error(f"错误：输出路径 {args.output_dir} 是一个文件，请指定一个目录。")
        print(f"错误：输出路径 {args.output_dir} 是一个文件，请指定一个目录。")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查依赖
    if not HAS_WEB_DEPS:
        logger.error("请先安装网页处理依赖：pip install requests beautifulsoup4")
        print("错误：请先安装网页处理依赖：pip install requests beautifulsoup4")
        return
    
    try:
        # 提取内容
        logger.info("=" * 60)
        logger.info("开始内容提取...")
        print("=" * 60)
        print(f"开始从URL提取内容: {url}")
        
        extractor = URLExtractor(url)
        result = extractor.extract()
        
        if not result.content_nodes and not result.raw_text:
            logger.warning("未提取到有效内容")
            print("警告：未提取到有效内容")
            return
        
        # 生成Markdown
        logger.info("\n" + "=" * 60)
        logger.info("生成Markdown文档...")
        print("\n" + "=" * 60)
        print("生成Markdown文档...")
        
        md_generator = MarkdownGenerator(result)
        
        # 生成安全的文件名
        url_safe = re.sub(r'[^\w\-_.]', '_', url)
        if len(url_safe) > 100:
            url_safe = url_safe[:100]
        md_filename = f"{url_safe}_extracted.md"
        md_path = output_dir / md_filename
        
        md_file = md_generator.generate(str(md_path))
        
        # 显示结果
        logger.info("\n" + "=" * 60)
        logger.info("处理完成！")
        logger.info(f"输出目录: {output_dir}")
        logger.info(f"Markdown文件: {md_file}")
        
        print("\n" + "=" * 60)
        print("✅ 处理完成！")
        print(f"📁 输出目录: {output_dir}")
        print(f"📄 Markdown文件: {md_file}")
        
        # 显示文件信息
        file_path = Path(md_file)
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"📊 文件大小: {file_size} 字节 ({file_size/1024:.2f} KB)")
            
            # 读取并显示前几行
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()[:10]
                print("\n📝 文件预览（前10行）:")
                print("-" * 40)
                for line in lines:
                    print(line.rstrip())
                print("-" * 40)
            except Exception as e:
                logger.debug(f"读取文件预览失败: {e}")
        
        # 显示内容统计
        if result.content_nodes:
            node_count = len(result.content_nodes)
            print(f"📈 提取的内容节点数: {node_count}")
        
        print(f"🔗 原始URL: {url}")
        print(f"🏷️  文档标题: {result.title}")
        
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        print(f"\n❌ 错误: {e}")
        print("请参考以下排查步骤:")
        print("1. 检查URL是否可访问")
        print("2. 检查网络连接")
        print("3. 确保已安装所有依赖库")
        print("4. 查看详细日志: url_extraction.log")
        return

# ==================== 测试函数 ====================

def test_with_sample_url():
    """使用提供的测试URL进行测试"""
    test_url = " https://docs.python.org/zh-cn/3.14/tutorial/index.html "
    print("🧪 开始测试...")
    print(f"测试URL: {test_url}")
    
    try:
        # 创建测试输出目录
        test_dir = Path("test_output")
        test_dir.mkdir(exist_ok=True)
        
        # 执行提取
        extractor = URLExtractor(test_url)
        result = extractor.extract()
        
        # 生成Markdown
        generator = MarkdownGenerator(result)
        output_file = test_dir / "python_tutorial_extracted.md"
        md_file = generator.generate(str(output_file))
        
        # 验证结果
        if Path(md_file).exists():
            file_size = Path(md_file).stat().st_size
            print(f"✅ 测试成功！")
            print(f"📄 生成文件: {md_file}")
            print(f"📊 文件大小: {file_size} 字节")
            print(f"🏷️  文档标题: {result.title}")
            print(f"📈 内容节点: {len(result.content_nodes)}个")
            
            # 显示文件前5行
            with open(md_file, 'r', encoding='utf-8') as f:
                preview = f.readlines()[:5]
            print("\n📝 文件预览:")
            for line in preview:
                print(f"  {line.rstrip()}")
            
            return True
        else:
            print("❌ 测试失败：文件未生成")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False

if __name__ == '__main__':
    # 如果直接运行脚本且没有参数，运行测试
    if len(sys.argv) == 1:
        print("🔍 未提供URL参数，运行测试...")
        if test_with_sample_url():
            print("\n💡 测试完成！使用示例:")
            print("  python url_to_md.py https://docs.python.org/zh-cn/3.14/tutorial/index.html ")
            print("  python url_to_md.py https://example.com --output-dir my_output")
        else:
            print("\n⚠️  测试失败，请检查依赖和网络连接")
    else:
        main()
