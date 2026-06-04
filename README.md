# GitHub 项目同步工具  
**一键 Pull / Push / Clone，简单高效的 Git 图形化工具**  

![界面截图]([屏幕截图 2026-06-04 080358.png](https://github.com/tianjinwolaile/Github-Gitee-/blob/main/%E5%B1%8F%E5%B9%95%E6%88%AA%E5%9B%BE%202026-06-04%20080358.png))  

---

## 📦 功能特性  
- **三种核心操作**  
  - ✅ `Push`：提交本地修改并推送到 GitHub  
  - ✅ `Pull`：从远程仓库拉取最新代码  
  - ✅ `Clone`：首次下载仓库到本地  

- **智能辅助功能**  
  - 🔒 自动移除敏感 Token（推送后清理）  
  - 📝 自动生成/管理 `.gitignore`  
  - 🚀 非 Git 仓库自动初始化  

- **兼容性**  
  - 支持所有 Git 托管平台（GitHub/GitLab/Gitee）  
  - 支持二进制文件（如 `.exe`、`.zip`）  

---

## 🛠️ 快速开始  

### 第一步：获取 GitHub Token  
1. 访问 `GitHub → Settings → Developer Settings → Personal Access Tokens`  
2. 生成新 Token，勾选 `repo` 权限  
3. 复制 Token 字符串（此工具仅需此一次）  

### 第二步：运行工具  
#### 方法 1 - 直接运行（推荐小白）  
👉 [下载最新版 EXE 文件]([https://github.com/your-repo/releases](https://github.com/tianjinwolaile/Github-Gitee-/releases/tag/v1))  

#### 方法 2 - 从源代码运行  
```bash
git clone [https://github.com/your-repo/github-updater.git](https://github.com/tianjinwolaile/Github-Gitee-.git)
cd Github-Gitee-
python github_updater.py
