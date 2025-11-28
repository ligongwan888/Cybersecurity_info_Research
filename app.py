from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
# from pydantic import BaseModel  <-- 删除了导致冲突的导入
import os 
import json
import re  
import urllib.parse 

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)

# --- 1. 从环境变量中读取 Gemini Key ---
# 注意：您的 Render 环境变量中键名是 GOOGLE_API_KEY，这里使用该名称更安全
GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY") 

# 初始化 Gemini 客户端
client = None
if GEMINI_API_KEY:
    try:
        # 使用 os.environ.get("GOOGLE_API_KEY") 作为 client 初始化参数
        client = genai.Client(api_key=GEMINI_API_KEY) 
        print("Gemini client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")

# 定义我们期望的 JSON 格式字符串 (保留，用于系统提示)
JSON_FORMAT_STRING = """
{
    "company_name": "公司名称",
    "website": "官方网站",
    "revenue": "最新年度营收",
    "business": "核心业务范围",
    "security_incident": "已公开的安全事件或数据泄露记录"
}
"""
# 删除了 class CompanyInfo(types.BaseModel): 定义，因为它是错误的来源

def extract_json(text):
    """
    使用正则表达式从包含杂乱文本的字符串中提取最外层的 JSON 对象。
    """
    # 查找以 '{' 开头，以 '}' 结尾的、最长的匹配
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None

def search_company_info_gemini(company_name, company_url=None): 
    """
    使用 Gemini 模型和 Google Search Tool/Website Tool 搜索信息。
    """
    # 检查 API Key 名称是否正确 (您的 Render 使用 GOOGLE_API_KEY)
    if not client:
        return {
            "error": "后端配置错误：Gemini API 客户端未初始化。",
            "details": "请在 Render 中设置 GOOGLE_API_KEY 环境变量。"
        }

    # --- 构造工具列表和用户提示 ---
    
    # 关键修正: 使用 types.Tool 启用内置工具
    tools = [types.Tool.google_search] # 默认启用 Google 搜索工具
    
    # 基础用户查询
    user_prompt = f"请为我查询公司 '{company_name}' 的信息，包括：官方网站、最新年度营收、核心业务范围和已公开的安全事件或数据泄露记录。确保所有信息都是最新的。"
    
    # 如果用户提供了网址，添加额外的指令和工具
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
                tools=tools, # <-- 使用修正后的工具列表
                temperature=0.0 
            )
        )
        
        # --- JSON 提取容错处理 ---
        if response.text:
            raw_text = response.text.strip()
            
            # 1. 尝试直接解析
            try:
                data = json.loads(raw_text)
                return data
            except json.JSONDecodeError:
                pass 
            
            # 2. 如果直接解析失败，使用正则表达式提取 JSON 结构
            json_string = extract_json(raw_text)
            
            if json_string:
                try:
                    data = json.loads(json_string)
                    # 检查返回的 JSON 结构是否完整
                    if all(key in data for key in ["company_name", "website"]):
                        return data
                except json.JSONDecodeError:
                    pass

        # 如果提取和解析都失败
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
