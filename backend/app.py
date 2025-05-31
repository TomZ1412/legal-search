import json
import os
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
from flask_cors import CORS
import logging
import re
from collections import defaultdict # 确保导入，尽管在你的后端代码中可能没有直接用到，但与数据处理代码一致

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app) # 允许所有来源的跨域请求

# Elasticsearch 配置
ES_HOST = "localhost"
ES_PORT = 9200
ES_INDEX_NAME = "legal_documents"

es_client = None # 在请求到来时懒加载或在应用启动时初始化

# 加载ID映射
DOC_ID_MAPPINGS = {}
try:
    # 假设 id_mappings.json 在项目根目录，如果后端代码放在子目录，需要调整路径
    current_dir = os.path.dirname(__file__)
    mappings_path = os.path.join(current_dir, "id_mappings.json")
    if not os.path.exists(mappings_path):
         # 如果在当前目录没找到，尝试上一级目录，以适应您的 LeCaRD 结构
        mappings_path = os.path.join(current_dir, "..", "id_mappings.json")

    with open(mappings_path, "r", encoding='utf-8') as f:
        DOC_ID_MAPPINGS = json.load(f)
    logging.info("ID mappings loaded successfully.")
except FileNotFoundError:
    logging.error(f"id_mappings.json not found at {mappings_path}. Please run data_processor.py first.")
    # 不强制退出，允许应用启动，但类似案例功能将受影响
    # exit(1) # 如果映射文件不存在，直接退出，这里改为不退出，让应用能跑起来

def get_es_client():
    """获取或初始化 Elasticsearch 客户端"""
    global es_client
    if es_client is None:
        try:
            # 增加超时时间和重试次数，以应对网络瞬时问题
            es_client = Elasticsearch(
                f"http://{ES_HOST}:{ES_PORT}",
                request_timeout=60,  # 将超时时间增加到 60 秒 (默认通常为 10 秒)
                max_retries=5, # 增加重试次数，例如 5 次
                retry_on_timeout=True # 确保在超时时进行重试
            )
            if not es_client.ping():
                raise ValueError("Connection to Elasticsearch failed!")
            logging.info("Elasticsearch client initialized.")
        except Exception as e:
            logging.error(f"Failed to connect to Elasticsearch: {e}")
            es_client = None # 重置为None，确保下次尝试重新连接
    return es_client

@app.route('/')
def home():
    return "司法搜索引擎后端 API 运行中！"

@app.route('/search', methods=['POST'])
def search_documents():
    """关键词检索接口"""
    es = get_es_client()
    if es is None:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    data = request.get_json()
    query_text = data.get('query', '')
    page = data.get('page', 1)
    size = data.get('size', 10)
    filters = data.get('filters', {}) # 额外过滤条件，如标签，案件类型等

    if not query_text:
        return jsonify({"results": [], "total": 0})

    from_ = (page - 1) * size

    # 构建查询体
    search_body = {
        "from": from_,
        "size": size,
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": ["title^3", "abstract^2", "content"], # 标题权重更高，增加摘要和内容
                            "type": "best_fields", # 匹配任一字段即可
                            "fuzziness": "AUTO", # 启用模糊查询
                            "minimum_should_match": "70%", # 所有词都必须匹配
                            "analyzer": "ik_max_word" # 使用IK分词器
                        }
                    }
                ],
                "filter": [] # 过滤器，不影响相关性得分
            }
        },
        "highlight": { # 高亮显示关键词
            "fields": {
                "title": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                "abstract": {"fragment_size": 200, "number_of_fragments": 1, "pre_tags": ["<em>"], "post_tags": ["</em>"]},
                "content": {"fragment_size": 200, "number_of_fragments": 1, "pre_tags": ["<em>"], "post_tags": ["</em>"]} # 新增内容高亮
            },
            "encoder": "html" # 确保高亮标签正确编码
        },
        "sort": [{"_score": {"order": "desc"}}] # 按相关性得分排序
    }

    # 添加过滤器
    if filters:
        if 'tags' in filters and filters['tags']:
            search_body['query']['bool']['filter'].append({
                "terms": {"tags.keyword": filters['tags']} # 标签是keyword类型
            })
        # 你的数据中没有 'case_type' 字段，如果需要，请在索引时添加
        # if 'case_type' in filters and filters['case_type']:
        #     search_body['query']['bool']['filter'].append({
        #         "term": {"case_type.keyword": filters['case_type']}
        #     })

    try:
        logging.info(f"Searching with query: '{query_text}', filters: {filters}")
        res = es.search(index=ES_INDEX_NAME, body=search_body)
        
        hits = res['hits']['hits']
        total_hits = res['hits']['total']['value']

        results = []
        for hit in hits:
            source = hit['_source']
            highlight = hit.get('highlight', {})
            # 返回前端所需的数据
            results.append({
                "ajId": source.get("ajId"),
                "docId": hit['_id'], # 用于评测和关联
                "title": highlight.get("title", [source.get("title", "")])[0], # 取高亮或原标题
                "abstract_snippet": highlight.get("abstract", [source.get("abstract", "")[:200] + "..."])[0], # 取高亮或内容片段
                "abstract": source.get("abstract", ""), # 案件摘要
                "content":source.get("content", ""), # 新增内容高亮
                "analysis": source.get("analysis", ""),
                "result": source.get("result", ""),
                "score": hit['_score'],
                "tags": source.get("tags", [])
            })
        
        logging.info(f"Found {total_hits} results for '{query_text}'.")
        return jsonify({"results": results, "total": total_hits})

    except Exception as e:
        logging.error(f"Elasticsearch search error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/upload_similar_cases', methods=['POST'])
def upload_similar_cases():
    es = get_es_client()
    if es is None:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    if 'file' not in request.files:
        logging.warning("请求中没有文件部分。")
        return jsonify({"error": "没有文件部分"}), 400

    file = request.files['file']
    if file.filename == '':
        logging.warning("没有选择文件。")
        return jsonify({"error": "没有选择文件"}), 400

    # --- **这里的修改是关键** ---
    # 从 URL 查询参数 (request.args) 中获取 page 和 size
    # 转换为整数，并提供默认值
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    # --- **修改结束** ---

    if file:
        try:
            file_content = file.read().decode('utf-8')
            uploaded_case_data = json.loads(file_content)

            source_title = uploaded_case_data.get('ajName', '')
            source_content = uploaded_case_data.get('qw', '')
            source_abstract = uploaded_case_data.get('ajjbqk', '')

            if not source_title and not source_content and not source_abstract:
                return jsonify({"error": "上传文件不包含用于相似性搜索的 'ajName'、'ajjbqk' 或 'qw' 字段"}), 400

            mlt_body = {
                "from": (page - 1) * size, # 现在使用正确获取到的 page 和 size
                "size": size,              # 现在使用正确获取到的 page 和 size
                "query": {
                    "more_like_this": {
                        "fields": ["title", "abstract", "content"],
                        "like": [f"{source_title} {source_abstract} {source_content}"],
                        "min_term_freq": 1,
                        "max_query_terms": 25,
                        "min_doc_freq": 1,
                        "minimum_should_match": "30%"
                    }
                },
                "highlight": {
                    "fields": {
                        "title": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                        "abstract": {"fragment_size": 200, "number_of_fragments": 1, "pre_tags": ["<em>"], "post_tags": ["</em>"]},
                        "content": {"fragment_size": 200, "number_of_fragments": 1, "pre_tags": ["<em>"], "post_tags": ["</em>"]}
                    },
                    "encoder": "html"
                }
            }

            logging.info(f"正在根据上传文件内容（标题：{source_title[:50]}...）搜索相似案例，page={page}，size={size}")
            res = es.search(index=ES_INDEX_NAME, body=mlt_body)

            hits = res['hits']['hits']
            total_hits = res['hits']['total']['value']

            results = []
            for hit in hits:
                source = hit['_source']
                highlight = hit.get('highlight', {})
                results.append({
                    "ajId": source.get("ajId"),
                    "docId": hit['_id'],
                    "title": highlight.get("title", [source.get("title", "")])[0],
                    "abstract_snippet": highlight.get("abstract", [source.get("abstract", "")[:200] + "..."])[0],
                    "abstract": source.get("abstract", ""),
                    "content":source.get("content", ""), # 新增内容高亮
                    "analysis": source.get("analysis", ""),
                    "result": source.get("result", ""),
                    "score": hit['_score'],
                    "tags": source.get("tags", [])
                })

            logging.info(f"为上传文件找到了 {total_hits} 个相似案例。")
            logging.info(f"后端准备返回的结果数量: {len(results)}, 总数: {total_hits}") # <-- 添加这一行
            return jsonify({"results": results, "total": total_hits})

        except json.JSONDecodeError as e:
            logging.error(f"上传的 JSON 文件无效: {e}", exc_info=True)
            return jsonify({"error": f"上传的 JSON 文件无效: {e}"}), 400
        except Exception as e:
            logging.error(f"处理上传文件以查找相似案例时出错: {e}", exc_info=True)
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "出了一些问题"}), 500

@app.route('/document/<doc_id>', methods=['GET'])
def get_document_details(doc_id):
    """根据 docId 获取单个文档的详细内容"""
    es = get_es_client()
    if es is None:
        return jsonify({"error": "Elasticsearch connection failed"}), 500

    try:
        res = es.get(index=ES_INDEX_NAME, id=doc_id)
        if res['found']:
            doc = res['_source']
            return jsonify(doc)
        else:
            return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        logging.error(f"Error fetching document {doc_id}: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    get_es_client()
    app.run(host='0.0.0.0', port=5000, debug=False) # debug=True 方便开发，生产环境请关闭