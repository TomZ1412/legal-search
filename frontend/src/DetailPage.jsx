import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './DetailPage.css'; // 确保引入了CSS文件

function DetailPage() {
  const { docId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(false);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

  useEffect(() => {
    setLoading(true);
    axios.get(`${BACKEND_URL}/document/${docId}`)
      .then(res => {
        setDetail(res.data);
      })
      .catch(err => {
        console.error('Failed to fetch detail:', err);
      })
      .finally(() => setLoading(false));
  }, [docId]);

  if (loading) return <p>加载中...</p>;
  if (!detail) return <p>未找到相关信息</p>;

  return (
    <div className="detail-page-wrapper"> {/* 新增一个最外层容器 */}
      <div className="detail-header"> {/* 标题和摘要放入头部区域 */}
        <h1 dangerouslySetInnerHTML={{ __html: detail.title }} />
      </div>

      <div className="detail-abstract-section"> {/* 正文部分 */}
        <h2>基本情况：</h2>
        <div className="content-scroll-area" dangerouslySetInnerHTML={{ __html: detail.abstract }} />
      </div>

      <div className="detail-content-section"> {/* 正文部分 */}
        <h2>全文：</h2>
        <div className="content-scroll-area" dangerouslySetInnerHTML={{ __html: detail.content }} />
      </div>

      <div className="detail-content-section"> {/* 分析 */}
        <h2>分析过程：</h2>
        <div className="content-scroll-area" dangerouslySetInnerHTML={{ __html: detail.analysis }} />
      </div>

      <div className="detail-content-section"> {/* 正文部分 */}
        <h2>判决结果：</h2>
        <div className="content-scroll-area" dangerouslySetInnerHTML={{ __html: detail.result }} />
      </div>

      <div className="detail-footer"> {/* 底部返回按钮 */}
        <button onClick={() => navigate(-1)} className="search-button">返回搜索结果</button>
      </div>
    </div>
  );
}

export default DetailPage;