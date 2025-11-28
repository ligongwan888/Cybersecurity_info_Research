from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
import os 
import json
import re  
import urllib.parse 

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)

# 简化初始化：只定义一个全局变量来存储 API Key，而不是在启动时初始化客户端
# 客户端的初始化转移到 search_company_info_gemini 函数内部（如果需要）或保持简单
API_KEY_NAME = "GOOGLE_API_KEY" # 确保读取的键名是这个

# 定义我们期望的 JSON 格式字符串
JSON_FORMAT_STRING = """
{
    "company_name": "公司名称",
    "website": "官方网站",
    "revenue": "最新年度营收",
    "business": "核心业务范围",
    "security_incident": "已公开的安全事件或数据泄露记录"
}
"""

def extract_json(text):
    """
    使用正则表达式从包含杂乱文本的字符串中提取最外层的 JSON 对象。
    """
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None

def search_company_info_gemini(company_name, company_url=None): 
    """
    使用 Gemini 模型和 Google Search Tool/Website Tool 搜索信息。
    """
    # 核心修正：在每次调用前获取 API Key 并尝试初始化客户端
    gemini_api_key = os.environ.get(API_KEY_NAME)
    
    if not gemini_api_key:
        return {
            "error": "后端配置错误：Gemini API 客户端未初始化。",
            "details": f"请在 Render 中设置 {API_KEY_NAME} 环境变量。"
        }
        
    try:
        # 每次调用时初始化客户端，确保使用最新的 API Key
        client = genai.Client(api_key=gemini_api_key) 
    except Exception as e:
         return {"error": f"调用 Gemini API 客户端初始化失败: {str(e)}"}
         
    # --- 构造工具列表和用户提示 ---
    
    tools = [types.Tool.google_search] 
    user_prompt = f"请为我查询公司 '{company_name}' 的信息，包括：官方网站、最新年度营收、核心业务范围和已公开的安全事件或数据泄露记录。确保所有信息都是最新的。"
    
    if company_url:
        cleaned_url = urllib.parse.unquote(company_url).strip() 
        tools.append(types.Tool.url_fetcher) 
        
        user_prompt += f"\n\n此外，请访问这个网址：{cleaned_url}。请结合该网址提供的内容，尤其是补充或验证公司的核心业务范围，并将其总结到 'business' 字段中。如果网址抓取失败，请使用 Google Search Tool 的结果。"
        
    # 系统提示：强烈要求 JSON 格式
    system_prompt = (
        "你是一个专业的华泰网络安全客户信息查询助手。你的核心任务是利用所有可用的工具，"
        "以最准确、最新、最全面的信息来回答用户对指定公司信息的查询。"
        "如果某个信息在搜索中无法找到，请使用 '信息不足，无法确认。' 来代替。"
        "你的响应中必须且只能包含一个符合以下格式的 JSON 结构，不得有任何其他文字、解释或警告：\n\n"
        f"JSON 格式:\n{JSON_FORMAT_STRING}\n\n"
    )

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools, 
                temperature=0.0 
            )
        )
        
        # --- JSON 提取容错处理 (保持不变) ---
        if response.text:
            raw_text = response.text.strip()
            
            try:
                data = json.loads(raw_text)
                return data
            except json.JSONDecodeError:
                pass 
            
            json_string = extract_json(raw_text)
            
            if json_string:
                try:
                    data = json.loads(json_string)
                    if all(key in data for key in ["company_name", "website"]):
                        return data
                except json.JSONDecodeError:
                    pass

        return {
            "error": "Gemini API 返回了非结构化响应，可能包含错误或信息不足。",
            "details": f"API 原始响应（或部分）：{response.text[:500] if response.text else '空响应'}...",
            "reason": "请检查公司名称是否存在，或API Key是否存在配额/内容限制。"
        }

    except Exception as e:
        return {"error": f"调用 Gemini API 失败: {str(e)}"}


# 定义 API 路由 (Endpoint)
@app.route('/api/search', methods=['GET'])
def search():
    company_name = request.args.get('name', '')
    company_url = request.args.get('url', '') 
    
    if not company_name:
        return jsonify({"error": "请输入公司名称"}), 400

    result = search_company_info_gemini(company_name, company_url) 
    
    return jsonify(result)

# 定义根路径路由 (用于检查服务状态)
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "status": "Service is running",
        "message": "Access the API endpoint at /api/search?name=...",
        "tip": "This confirms the Render backend is online and responsive."
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
