import markdown
from bs4 import BeautifulSoup
import xmind

def md_to_xmind_direct(md_file, xmind_file):
    """
    将Markdown文件直接转换为XMind思维导图
    :param md_file: 输入的Markdown文件路径
    :param xmind_file: 输出的XMind文件路径
    """
    md_file=input("请输入Markdown文件路径：")
    # 1. 读取并解析Markdown文件
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # 使用markdown库将Markdown转换为HTML
    html_content = markdown.markdown(md_content)
    
    # 2. 使用BeautifulSoup解析HTML结构
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 3. 创建XMind工作簿和根主题
    workbook = xmind.load(xmind_file)  # 如果文件不存在则创建新工作簿
    sheet = workbook.getPrimarySheet()
    root_topic = sheet.getRootTopic()
    
    # 4. 递归解析HTML并构建思维导图节点
    def parse_html_to_topics(parent_topic, html_element, current_level=1):
        """
        递归解析HTML元素，将其转换为思维导图节点
        """
        # 处理标题元素（h1-h6）
        if html_element.name and html_element.name.startswith('h'):
            level = int(html_element.name[1])
            if level >= current_level:
                # 创建新主题
                topic = parent_topic.addSubTopic()
                topic.setTitle(html_element.get_text().strip())
                return topic, level
        
        # 处理列表项
        elif html_element.name in ['ul', 'ol']:
            for li in html_element.find_all('li', recursive=False):
                li_topic = parent_topic.addSubTopic()
                li_topic.setTitle(li.get_text().strip())
                # 递归处理列表项内的嵌套内容
                for child in li.children:
                    if child.name:
                        parse_html_to_topics(li_topic, child, current_level)
        
        # 处理段落（可作为节点的备注）
        elif html_element.name == 'p':
            # 可以将段落内容作为父节点的备注
            if parent_topic and html_element.get_text().strip():
                notes = parent_topic.getNotes()
                if not notes:
                    parent_topic.setPlainNotes(html_element.get_text().strip())
                else:
                    parent_topic.setPlainNotes(notes + "\n" + html_element.get_text().strip())
        
        return parent_topic, current_level
    
    # 5. 遍历HTML的主要结构元素
    current_parent = root_topic
    current_level = 1
    
    for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'p']):
        current_parent, current_level = parse_html_to_topics(
            current_parent, element, current_level
        )
    
    # 6. 设置根主题标题（通常使用第一个h1标题）
    h1_elements = soup.find_all('h1')
    if h1_elements:
        root_topic.setTitle(h1_elements[0].get_text().strip())
    else:
        # 如果没有h1标题，使用文件名或默认标题
        import os
        root_topic.setTitle(os.path.splitext(os.path.basename(md_file)))
    
    # 7. 保存XMind文件
    xmind.save(workbook, xmind_file)
    print(f"成功将 {md_file} 转换为 {xmind_file}")

# 使用示例
if __name__ == '__main__':
    # 示例：转换单个文件
    md_to_xmind_direct('example.md', 'output.xmind')
    
    # 批量转换示例
    import glob
    md_files = glob.glob('*.md')
    for md_file in md_files:
        output_file = f"output/{os.path.basename(md_file).replace('.md', '.xmind')}"
        md_to_xmind_direct(md_file, output_file)

squares=[1,2,3,4,5]
# squares=[x**2 for x in squares]
squares=squares.remove(1)
print(squares)