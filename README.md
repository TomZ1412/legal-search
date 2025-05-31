
---

## 代码结构

项目包含两个主体部分: `frontend` and `backend`.
```
├── search-engine-project/
│   ├── frontend/                        
│   │   ├── public/                    
│   │   ├── src/                  
│   │   │   ├── components/       
│   │   │   ├── App.css              
│   │   │   ├── App.js               # 主页面
│   │   │   ├── index.css            
│   │   │   |── index.js             
│   │   │   ├── resultPage.css
│   │   │   ├── resultPage.jsx       # 结果页面
│   │   │   ├── DetailPage.css 
│   │   │   ├── DetailPage.jsx       # 详情页面      
│   │   │   ..                 
│   │   ├── package.json          
│   │   |── package-lock.json 
│   │   └── README.md    
│   │
│   ├── backend/                  
│   │   ├── app.py                # 后端主文件
│   │   └── data_processor.py     # 索引构建
│   │
│   └── README.md                 
```
---

## 环境配置

### 前端

- Node.js (v14 or later)
- npm (v6 or later)
### 后端

- Python (v3.7 or later)

### 安装依赖

    ```bash
    # 前端
    cd search-engine-project/frontend
    npm install
    # 后端
    cd search-engine-project/backend
    pip install -r requirements.txt
    ```

## 运行项目


### 构建索引

    ```bash
    cd search-engine-project/backend
    python data_processor.py
    ```

### 运行后端

    ```bash
    cd search-engine-project/backend
    python app.py
    ```

### 运行前端

    ```bash
    cd search-engine-project/frontend
    npm start
    ```
---
