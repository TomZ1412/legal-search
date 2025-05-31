import json
import os
from elasticsearch import Elasticsearch, helpers
import logging
import re
from collections import defaultdict

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Elasticsearch 配置 (不变)
ES_HOST = "localhost"
ES_PORT = 9200
ES_INDEX_NAME = "legal_documents"

# LeCaRD 数据集路径 (不变)
LECA_RD_PATH = "../LeCaRD/LeCaRD-main"
CANDIDATES_PATH = os.path.join(LECA_RD_PATH, "data", "candidates", "candidates1").replace("\\", "/")
QUERIES_PATH = os.path.join(LECA_RD_PATH, "data", "query").replace("\\", "/")


def connect_es():
    """连接 Elasticsearch"""
    es = Elasticsearch(f"http://{ES_HOST}:{ES_PORT}")
    if not es.ping():
        raise ValueError("Connection to Elasticsearch failed!")
    print("Successfully connected to Elasticsearch.")
    return es

def create_index_mapping(es_client):
    """创建 Elasticsearch 索引及映射 (不变)"""
    if es_client.indices.exists(index=ES_INDEX_NAME):
        print(f"Index '{ES_INDEX_NAME}' already exists. Deleting and recreating...")
        es_client.indices.delete(index=ES_INDEX_NAME)

    body = {
        "settings": {
            "analysis": {
                "analyzer": {
                    "ik_smart_analyzer": {
                        "type": "custom",
                        "tokenizer": "ik_smart"
                    },
                    "ik_max_word_analyzer": {
                        "type": "custom",
                        "tokenizer": "ik_max_word"
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "ajId": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "ik_max_word_analyzer"},
                "abstract": {"type": "text", "analyzer": "ik_max_word_analyzer"},
                "content": {"type": "text", "analyzer": "ik_max_word_analyzer"},
                "analysis": {"type": "keyword"},
                "result": {"type": "keyword"},
                "tags": {
                    "type": "text",
                    "fields": {
                        "keyword": {
                            "type": "keyword",
                            "ignore_above": 256
                        }
                    }
                }
            }
        }
    }
    es_client.indices.create(index=ES_INDEX_NAME, body=body)
    print(f"Index '{ES_INDEX_NAME}' created with custom analyzer.")

# --- 批量提取标签的修改 ---
def extract_legal_tags(title, abstract):
    """
    从案件标题和摘要中提取法律标签
    
    参数:
        title (str): 案件标题
        abstract (str): 案件摘要
        
    返回:
        list: 提取出的前3个法律标签，按相关性排序
    """
    # 定义法律标签及其关键词映射 (可根据实际需求扩展)
    tag_keywords = {
        '合同纠纷': [
            '合同纠纷', '合同', '违约', '缔约', '合同法', '合同履行', '合同解除', '合同终止', '协议', '约定', '买卖合同', '租赁合同'
        ],
        '侵权责任': [
            '侵权责任', '侵权', '损害赔偿', '损害', '赔偿', '侵害', '人身权', '名誉权', '人格权', '财产权', '精神损害'
        ],
        '劳动争议': [
            '劳动争议', '劳动', '劳动合同', '雇佣', '工资', '加班', '解雇', '工伤', '社保', '社会保险', '劳动法', '劳动关系'
        ],
        '婚姻家庭': [
            '婚姻家庭', '离婚', '婚姻', '抚养', '赡养', '继承', '财产分割', '家庭暴力', '子女抚养', '婚姻法', '夫妻财产', '抚养费'
        ],
        '知识产权': [
            '知识产权', '专利', '商标', '著作权', '版权', '盗版', '侵权', '发明', '商标权', '专利权', '版权法', '知识产权法'
        ],
        '金融借贷': [
            '金融借贷', '贷款', '借贷', '债务', '债权', '利息', '担保', '抵押', '借款合同', '放贷', '借款', '债权转让'
        ],
        '房产纠纷': [
            '房产纠纷', '房产', '房屋', '租赁', '产权', '物业', '拆迁', '房屋买卖合同', '房地产', '土地使用权'
        ],
        '交通事故': [
            '交通事故', '肇事', '交通违章', '交通安全法', '车祸'
        ],
        '刑事案件': [
            '刑事案件', '刑事', '犯罪', '盗窃', '抢劫', '诈骗', '故意伤害', '杀人', '刑法', '拘留', '判刑', '刑事诉讼'
        ],
        '行政诉讼': [
            '行政诉讼', '行政', '政府', '处罚', '许可', '复议', '强制', '执法', '行政处罚', '行政复议', '行政许可', '行政诉讼法'
        ]
    }

    
    # 预处理文本
    text = (title + ' ' + abstract).lower()
    
    # 统计关键词出现次数
    tag_scores = defaultdict(int)
    
    for tag, keywords in tag_keywords.items():
        for keyword in keywords:
            # 使用正则匹配单词边界，避免部分匹配
            tag_scores[tag] += text.count(keyword.lower())
    # 按匹配次数排序
    sorted_tags = sorted(tag_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 提取前3个标签
    top_tags = [tag for tag, score in sorted_tags[:3] if score > 0]
    
    # 如果匹配不足3个，补充默认标签
    if len(top_tags) < 3:
        return top_tags
    elif len(top_tags) == 0:
        return ['其他']
    else:
        return top_tags[:3]

def index_documents(es_client):
    """读取LeCaRD的candidates数据并索引到Elasticsearch"""
    print(f"Indexing documents from {CANDIDATES_PATH}...")
    actions = []
    doc_count = 0

    for dir_name in os.listdir(CANDIDATES_PATH):
        current_dir_path = os.path.join(CANDIDATES_PATH, dir_name)
        if os.path.isdir(current_dir_path):
            for file_name in os.listdir(current_dir_path):
                if file_name.endswith(".json"):
                    file_path = os.path.join(current_dir_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            doc_data = json.load(f)
                            # 提取所需字段
                            doc_id = file_name.split('.')[0] # doc_id 对应文件名 (candidate id)
                            ajid = doc_data.get('ajId')
                            title = doc_data.get('ajName', '')
                            abstract = doc_data.get('ajjbqk', '')
                            content = doc_data.get('qw', '')
                            analysis = doc_data.get('cpfxgc', '')
                            result = doc_data.get('pjjg', '')

                            # 简易标签抽取
                            extracted_tags = extract_legal_tags(title,abstract)

                            action = {
                                "_index": ES_INDEX_NAME,
                                "_id": doc_id,
                                "_source": {
                                    "ajId": ajid,
                                    "title": title,
                                    "content": content,
                                    "abstract": abstract,
                                    "analysis": analysis,
                                    "result": result,
                                    "tags": extracted_tags
                                }
                            }
                            actions.append(action)
                            doc_count += 1
                            if len(actions) >= 100: # 每1000条批量提交
                                helpers.bulk(es_client, actions)
                                actions = []
                        except json.JSONDecodeError as e:
                            print(f"Error decoding JSON from {file_path}: {e}")
                        except Exception as e:
                            print(f"Error processing {file_path}: {e}")

    if actions: # 提交剩余的文档
        helpers.bulk(es_client, actions)
    print(f"Finished indexing. Total documents indexed: {doc_count}")

# 其他函数 (build_id_mappings, main) 保持不变
def build_id_mappings():
    """构建 ajId 到 doc_id (文件名) 的映射，用于评测"""
    doc2id = {} # ajId -> doc_id
    id2doc = {} # doc_id -> ajId
    print("Building ID mappings...")
    for dir_name in os.listdir(CANDIDATES_PATH):
        current_dir_path = os.path.join(CANDIDATES_PATH, dir_name)
        if os.path.isdir(current_dir_path):
            for file_name in os.listdir(current_dir_path):
                if file_name.endswith(".json"):
                    file_path = os.path.join(current_dir_path, file_name)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        try:
                            info = json.load(f)
                            ajid = info.get('ajId')
                            doc_id = file_name.split('.')[0]
                            if ajid:
                                doc2id[ajid] = doc_id
                                id2doc[doc_id] = ajid
                        except json.JSONDecodeError:
                            print(f"Warning: Could not decode JSON from {file_path}")
    print("ID mappings built.")
    return doc2id, id2doc

if __name__ == "__main__":
    es = connect_es()
    create_index_mapping(es)
    index_documents(es)
    doc2id, id2doc = build_id_mappings()
    with open("id_mappings.json", "w", encoding='utf-8') as f:
        json.dump({"doc2id": doc2id, "id2doc": id2doc}, f, ensure_ascii=False, indent=4)
    print("ID mappings saved to id_mappings.json")