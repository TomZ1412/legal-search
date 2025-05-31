import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

function useQuery() {
    return new URLSearchParams(useLocation().search);
}

function ResultsPage() {
    const queryParams = useQuery();
    const location = useLocation();
    const navigate = useNavigate();

    const [results, setResults] = useState([]);
    const [total, setTotal] = useState(0);
    const [loading, setLoading] = useState(false);
    const [currentPage, setCurrentPage] = useState(1);
    const [searchQuery, setSearchQuery] = useState('');
    const [searchType, setSearchType] = useState(''); // 'keyword', 'uploadFile', or '' (initial/no search)
    const [uploadedFileName, setUploadedFileName] = useState('');

    const itemsPerPage = 12;
    const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

    const createMarkup = (html) => ({ __html: html });

    const fetchKeywordResults = async (queryText, pageNum) => {
        if (!queryText) {
            setResults([]);
            setTotal(0);
            return;
        }
        setLoading(true);
        try {
            const res = await axios.post(`${BACKEND_URL}/search`, { query: queryText, page: pageNum, size: itemsPerPage });
            setResults(res.data.results || []);
            setTotal(res.data.total || 0);
            setSearchType('keyword'); // 确保这里设置为 'keyword'
        } catch (err) {
            console.error('关键词搜索失败:', err);
            setResults([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    };

    // Main effect to handle different search types
    useEffect(() => {
        // **优先级：先处理文件上传的数据，因为它是通过 state 一次性传入的**
        if (location.state && location.state.searchType === 'uploadFile') {
            console.log("从 HomePage 接收到的状态：", location.state);
            setResults(location.state.searchResults || []);
            setTotal(location.state.total || 0);
            setCurrentPage(1);
            setSearchType('uploadFile'); // 明确设置为 uploadFile
            setUploadedFileName(location.state.fileName || '');
            setSearchQuery(''); // 清除关键词
            // 立即清空 location state，防止下次渲染或刷新再次进入此分支
            // 这行是导致后面问题的原因，但是是正确的，为了防止刷新问题
            // 我们需要在 else 分支中加入更多条件
            navigate(location.pathname, { replace: true, state: {} });
            // console.log("setResults 后立即查看 results（可能是旧值）:", results); // 可以移除这行，因为它总是旧值
        } else {
            // **只有在当前 searchType 不是 'uploadFile' 时，才执行关键词或初始化逻辑**
            // 避免在文件上传后，由于 location.state 被清空而错误地进入此分支并清空结果
            if (searchType !== 'uploadFile') { // <--- 添加这个条件！
                const q = queryParams.get('q') || '';
                const page = parseInt(queryParams.get('page')) || 1;

                // 只有当查询参数有变化，或者组件是首次加载且没有searchType时才设置
                if (q !== searchQuery || page !== currentPage || searchType === '') {
                    setSearchQuery(q);
                    setCurrentPage(page);

                    if (q) {
                        fetchKeywordResults(q, page);
                    } else {
                        // 确保这里只在没有关键词且不是文件上传类型时才清空
                        setResults([]);
                        setTotal(0);
                        setSearchType('');
                        setUploadedFileName('');
                    }
                }
            }
        }
    }, [location.search, location.state, navigate, searchQuery, currentPage, searchType]); // 依赖项更新，增加了searchQuery, currentPage, searchType

    // Effect specifically for pagination for keyword search
    useEffect(() => {
        if (searchType === 'keyword' && searchQuery) {
            fetchKeywordResults(searchQuery, currentPage);
        }
    }, [currentPage, searchType, searchQuery]);

    // **🔥🔥🔥 关键的附加 useEffect：监听 results 和 total 的最终状态 🔥🔥🔥**
    useEffect(() => {
        console.log("--- Results 状态最终更新为 ---", results);
        console.log("--- Results 长度 ---", results.length);
        console.log("--- Total 状态最终更新为 ---", total);
    }, [results, total]); // 只有当 results 或 total 实际变化时才触发

    const totalPages = Math.ceil(total / itemsPerPage);

    const handlePageChange = (newPage) => {
        if (newPage > 0 && newPage <= totalPages) {
            setCurrentPage(newPage);
            if (searchType === 'keyword') {
                navigate(`/results?q=${encodeURIComponent(searchQuery)}&page=${newPage}`);
            }
            window.scrollTo(0, 0);
        }
    };

    const handleViewDetail = (docId) => {
        navigate(`/detail/${docId}`);
    };

    return (
        <div className="container results-page">
            <h1 className="title">搜索结果</h1>

            {searchType === 'keyword' && searchQuery && (
                <p className="search-info">关键词：<strong>{searchQuery}</strong></p>
            )}
            {searchType === 'uploadFile' && uploadedFileName && (
                <p className="search-info">通过文件 <strong>{uploadedFileName}</strong> 查找相似案例</p>
            )}
            {/* 只有在没有明确搜索类型时才显示此消息 */}
            {searchType === '' && !searchQuery && !uploadedFileName && <p className="search-info">请在首页输入关键词或上传文件进行搜索。</p>}

            {loading ? (
                <p className="loading-message">加载中...</p>
            ) : (
                <div className="results-list-section">
                    {/* 根据 searchType 和 total 来判断是否显示结果数量 */}
                    {(searchType === 'keyword' && total > 0) || (searchType === 'uploadFile' && total > 0) ? (
                        <p className="total-results-info">共找到 {total} 条结果：</p>
                    ) : (
                        // 只有在明确知道没有结果时才显示此消息
                        (searchType && total === 0) && <p className="no-results-message">没有找到相关结果。</p>
                    )}

                    {results.length > 0 ? (
                        <div className="results-grid">
                            {results.map(item => (
                                <div className="result-card" key={item.docId}>
                                    <h3
                                        className="result-title"
                                        onClick={() => handleViewDetail(item.docId)}
                                        dangerouslySetInnerHTML={createMarkup(item.title)}
                                    />
                                    <div
                                        className="snippet"
                                        dangerouslySetInnerHTML={createMarkup(item.abstract_snippet || '')}
                                    />
                                    {item.tags && item.tags.length > 0 && (
                                        <div className="result-tags">
                                            {item.tags.map(tag => (
                                                <span key={tag} className="tag">{tag}</span>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    ) : (
                        // 只有在明确没有结果，且不是在加载中，也不是首次无类型状态时才显示
                        !loading && searchType !== '' && <p className="no-results-message">没有找到相关结果。</p>
                    )}

                    {/* Pagination only for keyword search currently, or if backend supports upload pagination */}
                    {searchType === 'keyword' && total > 0 && totalPages > 1 && (
                        <div className="pagination">
                            <button
                                onClick={() => handlePageChange(currentPage - 1)}
                                disabled={currentPage === 1}
                                className="page-button"
                            >
                                上一页
                            </button>
                            <span className="page-info"> 第 {currentPage} / {totalPages} 页 </span>
                            <button
                                onClick={() => handlePageChange(currentPage + 1)}
                                disabled={currentPage === totalPages}
                                className="page-button"
                            >
                                下一页
                            </button>
                        </div>
                    )}
                </div>
            )}

            <button onClick={() => navigate('/')} className="search-button back-home">返回首页</button>
        </div>
    );
}

export default ResultsPage;