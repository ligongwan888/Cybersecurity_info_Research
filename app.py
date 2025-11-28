from flask import Flask, request, jsonify
from flask_cors import CORS
from google import genai
from google.genai import types
from pydantic import BaseModel
import os 
import json

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

# 定义输出结构
class CompanyInfo(BaseModel): 
    """用于结构化输出的公司信息"""
    company_name: str
    website: str
    revenue: str
    business: str
    security_incident: str

def search_company_info_gemini(company_name):
    """
    使用 Gemini 模型和 Google Search Tool 搜索并结构化公司信息。
    """
    if not client:
        return {
            "error": "后端配置错误：Gemini API 客户端未初始化。",
            "details": "请在 Render 中设置 GEMINI_API_KEY 环境变量。"
        }

    # --- 构造模型提示和配置 ---
    # !!! 关键修正：在 system_prompt 中添加绝对指令，确保只输出 JSON !!!
    system_prompt = (
        "你是一个专业的华泰网络安全客户信息查询助手。你的核心任务是利用内置的 Google 搜索工具，"
        "以最准确、最新、最全面的信息来回答用户对指定公司信息的查询。"
        "你需要提供公司名称、官方网站、最新年度营收、核心业务范围和已公开的安全事件信息。"
        "如果某个信息在搜索中无法找到，请明确回复 '信息不足，无法确认。' 或 '未找到相关公开记录。' 而不是猜测。"
        "请确保最终输出严格遵循提供的 JSON 结构。"
        "**你的响应中只能包含符合 CompanyInfo schema 的 JSON 文本，不得包含任何额外的文字、解释或警告。**" 
    )

    user_prompt = f"请为我查询公司 '{company_name}' 的信息，包括：官方网站、最新年度营收、核心业务范围和已公开的安全事件或数据泄露记录。确保所有信息都是最新的。"

    try:
        # 调用 Gemini API
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[{"google_search": {}}],  # 启用 Google Search Tool
                response_schema=CompanyInfo, 
                temperature=0.0 
            )
        )
        
        # --- 增强的错误处理和 JSON 解析 ---
        if response.text:
            try:
                # 尝试解析模型返回的文本为JSON
                data = json.loads(response.text)
                return data
            except json.JSONDecodeError as json_e:
                # 如果解析失败，返回详细错误信息
                return {
                    "error": "Gemini API 返回了非 JSON 格式的文本。",
                    "details": f"API 响应文本（可能包含错误或非结构化输出）：{response.text[:500]}...",
                    "reason": "这可能是模型在未找到信息时返回的非结构化提示，或 API 调用配额已用尽。"
                }
        
        # 如果 response.text 为空
        return {"error": "Gemini API 返回了空响应，请检查配额或稍后再试。"}

    except Exception as e:
        # 捕获其他所有 API 异常
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
