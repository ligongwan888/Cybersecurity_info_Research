from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os 

# 初始化 Flask 应用
app = Flask(__name__)
# 启用 CORS，允许前端页面访问这个 API
CORS(app)

# --- 1. 从环境变量中读取敏感信息 ---
# 注意：这些变量必须在 Render 平台上设置
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")

# Google Custom Search API 基 URL
SEARCH_URL = "https://www.googleapis.com/customsearch/v1"

def search_company_info_real(company_name):
    """
    使用 Google Custom Search API 搜索公司信息。
    通过多次定向搜索来模拟信息收集，并限制摘要长度。
    """
    
    # 检查环境变量是否配置
    if not (GOOGLE_API_KEY and GOOGLE_CSE_ID):
        return {
            "error": "后端配置错误：Google API 凭证缺失。",
            "details": "请在 Render 中设置 GOOGLE_API_KEY 和 GOOGLE_CSE_ID 环境变量。"
        }
    
    base_params = {
        'key': GOOGLE_API_KEY,
        'cx': GOOGLE_CSE_ID,
        'q': company_name,
        'num': 1 # 只获取一个搜索结果
    }
    
    results = {
        "company_name": company_name,
        "website": "未找到",
        "revenue": "未找到",
        "business": "未找到",
        "security_incident": "未找到相关信息"
    }
    
    # 定义摘要的最大显示长度，限制过长文本
    MAX_SNIPPET_LENGTH = 150 
    
    # 辅助函数：限制摘要长度，并添加省略号
    def format_snippet(snippet):
        if len(snippet) > MAX_SNIPPET_LENGTH:
            return snippet[:MAX_SNIPPET_LENGTH] + "..."
        return snippet

    # --- 搜索 1: 查找官方网站和业务描述 ---
    try:
        search_q = f'"{company_name}" 官网 业务介绍'
        response = requests.get(SEARCH_URL, params={**base_params, 'q': search_q})
        response.raise_for_status() 
        
        search_data = response.json()
        if search_data.get('items'):
            item = search_data['items'][0]
            results['website'] = item.get('displayLink', item.get('link', '未找到'))
            # 应用长度限制
            results['business'] = format_snippet(item.get('snippet', '从搜索摘要中提取业务描述...'))

    except requests.exceptions.RequestException as e:
        print(f"Website/Business search failed: {e}")

    # --- 搜索 2: 查找营收数据 ---
    try:
        search_q = f'"{company_name}" 最新年度营收'
        response = requests.get(SEARCH_URL, params={**base_params, 'q': search_q})
        response.raise_for_status()
        
        search_data = response.json()
        if search_data.get('items'):
            # 应用长度限制
            results['revenue'] = format_snippet(search_data['items'][0].get('snippet', '尝试从摘要中提取营收数据...'))
            
    except requests.exceptions.RequestException as e:
        print(f"Revenue search failed: {e}")


    # --- 搜索 3: 查找安全事件 ---
    try:
        search_q = f'"{company_name}" 数据泄露 OR 安全事件'
        response = requests.get(SEARCH_URL, params={**base_params, 'q': search_q})
        response.raise_for_status()
        
        search_data = response.json()
        if search_data.get('items'):
            first_incident_snippet = format_snippet(search_data['items'][0].get('snippet', '发生安全事件！请点击链接查看详情。'))
            results['security_incident'] = f"**可能发生过**。第一个相关结果摘要：{first_incident_snippet}"
            
    except requests.exceptions.RequestException as e:
        print(f"Security search failed: {e}")
        
    
    return results

# 定义 API 路由 (Endpoint)
@app.route('/api/search', methods=['GET'])
def search():
    company_name = request.args.get('name', '')
    
    if not company_name:
        return jsonify({"error": "请输入公司名称"}), 400

    # 调用真正的搜索函数
    result = search_company_info_real(company_name)
    
    # Flask 会自动将 Python 字典转换为 JSON 响应
    return jsonify(result)

if __name__ == '__main__':
    # 在本地环境中运行时，使用默认端口
    app.run(debug=True, port=5000)
