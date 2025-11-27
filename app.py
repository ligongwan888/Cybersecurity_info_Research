from flask import Flask, request, jsonify
from flask_cors import CORS

# 初始化 Flask 应用
app = Flask(__name__)

# 启用 CORS (跨域资源共享)，允许前端页面访问这个 API
# 生产环境中建议只允许特定的前端域名访问
CORS(app)

# 模拟数据库或爬虫功能
def search_company_info(company_name):
    """
    根据公司名称，返回一个模拟的公司信息字典。
    在实际项目中，这里需要替换为真实的爬虫或API调用逻辑。
    """
    # 将公司名转换为小写以便于简单的模拟匹配
    name_lower = company_name.lower()

    # --- 模拟数据 ---
    if "google" in name_lower or "谷歌" in name_lower:
        return {
            "company_name": "Alphabet Inc. (Google)",
            "website": "https://www.google.com/",
            "revenue": "$282.8 Billion (2023)",
            "business": "互联网搜索、云计算、人工智能、广告技术等。",
            "security_incident": "是。历史上发生过多次用户数据泄露和隐私违规事件，需定期关注其安全报告。"
        }
    elif "apple" in name_lower or "苹果" in name_lower:
        return {
            "company_name": "Apple Inc.",
            "website": "https://www.apple.com/",
            "revenue": "$383.3 Billion (2023)",
            "business": "设计、制造和销售智能手机、个人电脑、平板电脑、可穿戴设备和配件，并销售各种服务。",
            "security_incident": "否。未发生大规模数据泄露事件，但在iOS和macOS上偶尔出现系统漏洞，会及时修补。"
        }
    else:
        return {
            "company_name": company_name,
            "website": "未找到",
            "revenue": "正在搜索中...",
            "business": "信息不足，请尝试更精确的名称。",
            "security_incident": "未找到相关公开记录。"
        }

# 定义 API 路由 (Endpoint)
@app.route('/api/search', methods=['GET'])
def search():
    # 从 URL 参数中获取 'name' 字段 (即公司名)
    company_name = request.args.get('name', '')
    
    if not company_name:
        return jsonify({"error": "请输入公司名称"}), 400

    # 调用模拟搜索函数
    result = search_company_info(company_name)
    
    # 返回 JSON 格式的结果
    return jsonify(result)

# 部署平台需要知道如何启动应用，所以需要添加这一行
# 但在部署时，通常使用 gunicorn 或其他 WSGI 服务器启动
if __name__ == '__main__':
    # 在本地运行时，使用默认端口
    app.run(debug=True, port=5000)
