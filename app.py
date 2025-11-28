from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types # 保持导入，但不再用于 BaseModel
import os 
import json
import re  # 导入正则表达式库，继续用于提取 JSON

# 初始化 Flask 应用
app = Flask(__name__)
CORS(app)

# --- 1. 从环境变量中读取 Gemini Key ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Gemini 客户端
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Gemini client initialized successfully.")
    except Exception as e:
        print(f"Error initializing Gemini client: {e}")

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
    # 查找以 '{' 开头，以 '}' 结尾的、最长的匹配
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None

def search_company_info_gemini(company_name):
    """
    使用 Gemini 模型和 Google Search Tool 搜索信息，并强制模型返回 JSON 文本。
    """
    if not client:
        return {
            "error": "后端配置错误：Gemini API 客户端未初始化。",
            "details": "请在 Render 中设置 GEMINI_API_KEY 环境变量。"
        }

    # --- 构造模型提示：直接要求 JSON 格式 ---
    
    # 系统提示：强烈要求 JSON 格式
    system_prompt = (
        "你是一个专业的华泰网络安全客户信息查询助手。你的核心任务是利用内置的 Google 搜索工具，"
        "以最准确、最新、最全面的信息来回答用户对指定公司信息的查询。"
        "如果某个信息在搜索中无法找到，请使用 '信息不足，无法确认。' 来代替。"
        "你的响应中必须且只能包含一个符合以下格式的 JSON 结构，不得有任何其他文字、解释或警告：\n\n"
        f"JSON 格式:\n{JSON_FORMAT_STRING}\n\n"
    )

    # 用户的查询
    user_prompt = f"请为我查询公司 '{company_name}' 的信息。"

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[{"google_search": {}}],  # 启用 Google Search Tool
                # 关键：移除 response_schema 和 BaseModel，依赖提示词工程
                temperature=0.0 
            )
        )
        
        # --- JSON 提取容错处理 ---
        if response.text:
            raw_text = response.text.strip()
            
            # 1. 尝试使用正则表达式提取 JSON 结构
            json_string = extract_json(raw_text)
            
            if json_string:
                try:
                    data = json.loads(json_string)
                    # 检查返回的 JSON 结构是否完整
                    if all(key in data for key in ["company_name", "website"]):
                        return data
                    else:
                        # 即使解析成功，如果结构不完整也认为失败
                        raise json.JSONDecodeError("Incomplete JSON structure.", json_string, 0)
                except json.JSONDecodeError as e:
                    pass # 忽略，返回错误详情

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
    
    if not company_name:
        return jsonify({"error": "请输入公司名称"}), 400

    result = search_company_info_gemini(company_name)
    
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
