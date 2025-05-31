import React, { useState } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import './App.css'; // Your main CSS file
import ResultsPage from './ResultsPage';
import DetailPage from './DetailPage';
import axios from 'axios'; // Import axios for cleaner HTTP requests

function HomePage() {
  const [query, setQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState(null); // State for the selected file
  const navigate = useNavigate();

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:5000';

  // Handles basic keyword search
  const handleSearch = () => {
    if (!query.trim()) return;
    navigate(`/results?q=${encodeURIComponent(query.trim())}`);
  };

  // Handles Enter key press for search
  const handleKeyPress = (e) => {
    if (e.key === 'Enter') handleSearch();
  };

  // Handles file selection for upload
  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
  };

  // Handles uploading a file and searching for similar cases
  const handleUploadAndSearch = async () => {
    if (!selectedFile) {
      alert('请先选择一个案例文件！');
      return;
    }

    if (selectedFile.type !== 'application/json') {
      alert('请上传有效的 JSON 文件！');
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    // 定义 page 和 size （你可以从状态或props中获取）
    const page = 1; // 默认第一页
    const size = 10; // 默认每页10个结果

    try {
      // **关键修改：在 URL 中添加 page 和 size 作为查询参数**
      const response = await axios.post(
        `${BACKEND_URL}/upload_similar_cases?page=${page}&size=${size}`, // URL 变为这样
        formData,
        {
          headers: {
            // 'Content-Type': 'multipart/form-data', // Axios 会自动设置这个，无需手动指定
          },
        }
      );

      console.log("HomePage 接收到的后端响应数据:", response.data);
      console.log("准备传递到 ResultsPage 的状态：",{
          searchResults: response.data.results || [],
          total: response.data.total || 0,
          searchType: 'uploadFile',
          fileName: selectedFile.name,
        },
      );

      navigate('/results', {
        state: {
          searchResults: response.data.results || [],
          total: response.data.total || 0,
          searchType: 'uploadFile',
          fileName: selectedFile.name,
        },
      });

    } catch (error) {
      console.error('上传文件查找相似案例出错:', error);
      alert('上传文件查找相似案例出错: ' + (error.response?.data?.error || error.message));
    }
  };

  return (
    <div className="container home-page"> {/* Added home-page class for specific styling */}
      <h1 className="title">司法搜索引擎</h1>
      <div className="search-bar">
        <input
          type="text"
          className="search-input"
          placeholder="请输入关键词" // Changed placeholder for clarity
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button className="search-button" onClick={handleSearch}>搜索</button>
      </div>

      <div className="divider"><span>或</span></div> {/* Added a separator */}

      <div className="upload-section">
        <h2 className="upload-title">通过案例文件查找相似案例</h2>
        <input
          type="file"
          accept=".json" // Restrict to JSON files
          onChange={handleFileChange}
          className="file-input"
        />
        <button
          className="upload-button"
          onClick={handleUploadAndSearch}
          disabled={!selectedFile} // Disable button if no file is selected
        >
          上传并查找相似案例
        </button>
        {selectedFile && <p className="selected-file-info">已选择文件: <strong>{selectedFile.name}</strong></p>}
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/results" element={<ResultsPage />} />
      <Route path="/detail/:docId" element={<DetailPage />} />
    </Routes>
  );
}

export default App;