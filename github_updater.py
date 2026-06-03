"""
GitHub 项目更新工具
功能：一键 Pull（同步远程到本地）或 Push（提交并推送到远程）
依赖：Python 内置库（tkinter、subprocess、os、threading）
打包：pyinstaller --onefile --windowed github_updater.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import os
import threading
import json

CONFIG_FILE = "github_updater_config.json"

DEFAULT_GITIGNORE = """.Rhistory
.DS_Store
"""

# ────────────────────────────────────────────────────────────────────────────
# 配置持久化
# ────────────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(data: dict):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ────────────────────────────────────────────────────────────────────────────
# Git 工具函数
# ────────────────────────────────────────────────────────────────────────────

def build_remote_url(user: str, repo: str, token: str) -> str:
    """构造带 token 的 HTTPS 远程地址（格式与 bash 脚本一致）。"""
    repo = repo.strip().rstrip("/")
    if not repo.endswith(".git"):
        repo += ".git"
    return f"https://{user.strip()}:{token.strip()}@github.com/{user.strip()}/{repo}"


def build_clean_url(user: str, repo: str) -> str:
    """不含 token 的干净远程地址（push 后用于还原，避免 token 残留）。"""
    repo = repo.strip().rstrip("/")
    if not repo.endswith(".git"):
        repo += ".git"
    return f"https://github.com/{user.strip()}/{repo}"


def run_git(args: list[str], cwd: str) -> tuple[int, str]:
    """执行 git 命令，返回 (returncode, output)。"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=os.environ.copy(),
        )
        return result.returncode, result.stdout + result.stderr
    except FileNotFoundError:
        return -1, "错误：未找到 git 命令，请确保已安装 Git 并加入 PATH。"
    except Exception as e:
        return -1, f"执行出错：{e}"


# ────────────────────────────────────────────────────────────────────────────
# 主窗口
# ────────────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GitHub 项目更新工具")
        self.resizable(True, True)
        self.minsize(660, 600)

        self._build_ui()
        self._load_saved_config()

    # ── UI 构建 ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 10, "pady": 4}

        # ── 账号配置 ──
        acct_frame = ttk.LabelFrame(self, text="GitHub 账号配置")
        acct_frame.pack(fill="x", **pad)

        # 用户名
        ttk.Label(acct_frame, text="GitHub 用户名：").grid(row=0, column=0, sticky="w", **pad)
        self.github_user = tk.StringVar()
        ttk.Entry(acct_frame, textvariable=self.github_user, width=30).grid(
            row=0, column=1, sticky="ew", **pad)

        # 仓库名
        ttk.Label(acct_frame, text="仓库名（Repo）：").grid(row=1, column=0, sticky="w", **pad)
        self.repo_name = tk.StringVar()
        ttk.Entry(acct_frame, textvariable=self.repo_name, width=30).grid(
            row=1, column=1, sticky="ew", **pad)

        # Token
        ttk.Label(acct_frame, text="Personal Access Token：").grid(row=2, column=0, sticky="w", **pad)
        self.token = tk.StringVar()
        self.token_entry = ttk.Entry(acct_frame, textvariable=self.token, width=50, show="*")
        self.token_entry.grid(row=2, column=1, sticky="ew", **pad)
        self.show_token = tk.BooleanVar(value=False)
        ttk.Checkbutton(acct_frame, text="显示", variable=self.show_token,
                        command=self._toggle_token).grid(row=2, column=2, **pad)

        acct_frame.columnconfigure(1, weight=1)

        # ── 本地项目配置 ──
        proj_frame = ttk.LabelFrame(self, text="本地项目配置")
        proj_frame.pack(fill="x", **pad)

        # 本地目录
        ttk.Label(proj_frame, text="本地项目目录：").grid(row=0, column=0, sticky="w", **pad)
        self.local_dir = tk.StringVar()
        ttk.Entry(proj_frame, textvariable=self.local_dir, width=48).grid(
            row=0, column=1, sticky="ew", **pad)
        ttk.Button(proj_frame, text="浏览…", command=self._browse_dir).grid(row=0, column=2, **pad)

        # 分支
        ttk.Label(proj_frame, text="分支名称：").grid(row=1, column=0, sticky="w", **pad)
        self.branch = tk.StringVar(value="master")
        ttk.Entry(proj_frame, textvariable=self.branch, width=20).grid(
            row=1, column=1, sticky="w", **pad)

        proj_frame.columnconfigure(1, weight=1)

        # ── Push 选项 ──
        push_frame = ttk.LabelFrame(self, text="Push 选项")
        push_frame.pack(fill="x", **pad)

        ttk.Label(push_frame, text="提交说明（Commit message）：").grid(row=0, column=0, sticky="w", **pad)
        self.commit_msg = tk.StringVar(value="update")
        ttk.Entry(push_frame, textvariable=self.commit_msg, width=45).grid(
            row=0, column=1, sticky="ew", **pad)

        self.auto_init = tk.BooleanVar(value=True)
        ttk.Checkbutton(push_frame, text="目录非 git 仓库时自动 git init",
                        variable=self.auto_init).grid(row=1, column=1, sticky="w", **pad)

        self.auto_gitignore = tk.BooleanVar(value=True)
        ttk.Checkbutton(push_frame, text="不存在 .gitignore 时自动创建",
                        variable=self.auto_gitignore).grid(row=2, column=1, sticky="w", **pad)

        # .gitignore 内容编辑
        ttk.Label(push_frame, text=".gitignore 内容：").grid(row=3, column=0, sticky="nw", **pad)
        self.gitignore_text = tk.Text(push_frame, height=4, width=45, font=("Consolas", 9))
        self.gitignore_text.insert("1.0", DEFAULT_GITIGNORE)
        self.gitignore_text.grid(row=3, column=1, sticky="ew", **pad)

        self.clean_token = tk.BooleanVar(value=True)
        ttk.Checkbutton(push_frame, text="Push 后从 git 配置中移除 token（推荐）",
                        variable=self.clean_token).grid(row=4, column=1, sticky="w", **pad)

        push_frame.columnconfigure(1, weight=1)

        # ── 记住配置 ──
        misc_frame = ttk.Frame(self)
        misc_frame.pack(fill="x", padx=10, pady=2)
        self.remember = tk.BooleanVar(value=True)
        ttk.Checkbutton(misc_frame, text="记住配置（保存到 github_updater_config.json）",
                        variable=self.remember).pack(side="left")

        # ── 按钮区 ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=6)

        ttk.Button(btn_frame, text="⬆  Push（提交推送）", width=22,
                   command=self._on_push).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="⬇  Pull（拉取更新）", width=22,
                   command=self._on_pull).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="🔄  Clone（初次克隆）", width=22,
                   command=self._on_clone).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="清空日志", width=10,
                   command=self._clear_log).pack(side="right", padx=6)

        # ── 日志区 ──
        log_frame = ttk.LabelFrame(self, text="操作日志")
        log_frame.pack(fill="both", expand=True, padx=10, pady=4)

        self.log_box = scrolledtext.ScrolledText(
            log_frame, state="disabled", height=12,
            font=("Consolas", 9), wrap="word"
        )
        self.log_box.pack(fill="both", expand=True, padx=6, pady=6)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var, anchor="w",
                  relief="sunken").pack(fill="x", side="bottom")

    # ── UI 辅助 ──────────────────────────────────────────────────────────────

    def _browse_dir(self):
        d = filedialog.askdirectory(title="选择本地项目目录")
        if d:
            self.local_dir.set(d)

    def _toggle_token(self):
        self.token_entry.config(show="" if self.show_token.get() else "*")

    def _log(self, text: str):
        def _append():
            self.log_box.config(state="normal")
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _append)

    def _clear_log(self):
        self.log_box.config(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.config(state="disabled")

    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))

    # ── 配置持久化 ────────────────────────────────────────────────────────────

    def _load_saved_config(self):
        cfg = load_config()
        for key, var in [
            ("github_user", self.github_user),
            ("repo_name",   self.repo_name),
            ("token",       self.token),
            ("branch",      self.branch),
            ("commit_msg",  self.commit_msg),
            ("local_dir",   self.local_dir),
        ]:
            if cfg.get(key):
                var.set(cfg[key])
        if cfg.get("gitignore_content"):
            self.gitignore_text.delete("1.0", "end")
            self.gitignore_text.insert("1.0", cfg["gitignore_content"])

    def _maybe_save_config(self):
        if self.remember.get():
            save_config({
                "github_user":      self.github_user.get(),
                "repo_name":        self.repo_name.get(),
                "token":            self.token.get(),
                "branch":           self.branch.get(),
                "commit_msg":       self.commit_msg.get(),
                "local_dir":        self.local_dir.get(),
                "gitignore_content": self.gitignore_text.get("1.0", "end"),
            })

    # ── 输入校验 ──────────────────────────────────────────────────────────────

    def _validate(self, need_local=True) -> bool:
        if not self.github_user.get().strip():
            messagebox.showwarning("提示", "请填写 GitHub 用户名。")
            return False
        if not self.repo_name.get().strip():
            messagebox.showwarning("提示", "请填写仓库名（Repo）。")
            return False
        if not self.token.get().strip():
            messagebox.showwarning("提示", "请填写 Personal Access Token。")
            return False
        if need_local and not self.local_dir.get().strip():
            messagebox.showwarning("提示", "请先选择本地项目目录。")
            return False
        return True

    # ── 共用：初始化本地仓库 ──────────────────────────────────────────────────

    def _ensure_git_repo(self, local: str) -> bool:
        """若目录不是 git 仓库且勾选了自动 init，则执行 git init。"""
        if os.path.isdir(os.path.join(local, ".git")):
            return True
        if self.auto_init.get():
            self._log("[init] 检测到非 git 仓库，正在执行 git init…")
            code, out = run_git(["init"], cwd=local)
            self._log(out.strip())
            if code != 0:
                self._log("❌ git init 失败。")
                return False
            # 设置默认分支名
            branch = self.branch.get().strip() or "master"
            run_git(["checkout", "-b", branch], cwd=local)
            return True
        else:
            self._log('❌ 该目录不是 git 仓库，请先使用【Clone】或勾选"自动 git init"。')
            return False

    def _ensure_gitignore(self, local: str):
        """若不存在 .gitignore 且勾选了自动创建，则写入。"""
        path = os.path.join(local, ".gitignore")
        if not os.path.exists(path) and self.auto_gitignore.get():
            content = self.gitignore_text.get("1.0", "end")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self._log("[.gitignore] 已自动创建 .gitignore")

    def _setup_remote(self, local: str, remote_url: str):
        """移除旧 origin 再添加新 origin（含 token）。"""
        run_git(["remote", "remove", "origin"], cwd=local)
        code, out = run_git(["remote", "add", "origin", remote_url], cwd=local)
        if code != 0:
            self._log(f"[警告] 设置 remote 失败：{out.strip()}")

    # ── 操作：Push ────────────────────────────────────────────────────────────

    def _on_push(self):
        if not self._validate():
            return
        if not self.commit_msg.get().strip():
            messagebox.showwarning("提示", "请填写提交说明（Commit message）。")
            return
        self._maybe_save_config()
        threading.Thread(target=self._push_task, daemon=True).start()

    def _push_task(self):
        local  = self.local_dir.get().strip()
        branch = self.branch.get().strip() or "master"
        msg    = self.commit_msg.get().strip()
        user   = self.github_user.get().strip()
        repo   = self.repo_name.get().strip()
        token  = self.token.get().strip()

        remote_url = build_remote_url(user, repo, token)
        clean_url  = build_clean_url(user, repo)

        self._set_status("正在推送…")
        self._log(f"\n{'='*50}")
        self._log(f"[Push] 目录：{local}  分支：{branch}  提交说明：{msg}")

        # 1. 确保是 git 仓库
        if not self._ensure_git_repo(local):
            self._set_status("Push 失败")
            return

        # 2. 自动创建 .gitignore
        self._ensure_gitignore(local)

        # 3. 设置 remote
        self._setup_remote(local, remote_url)

        # 4. git add .
        code, out = run_git(["add", "."], cwd=local)
        self._log(out.strip() if out.strip() else "[add] 已暂存所有改动")
        if code != 0:
            self._log("❌ git add 失败。")
            self._set_status("Push 失败")
            return

        # 5. 检查是否有改动（git diff --cached --quiet）
        check_code, _ = run_git(["diff", "--cached", "--quiet"], cwd=local)
        if check_code == 0:
            self._log("⚠️ 没有新文件需要提交（工作区与最后一次提交相同）。")
            self._set_status("无改动，跳过提交")
        else:
            # 6. git commit
            code, out = run_git(["commit", "-m", msg], cwd=local)
            self._log(out.strip() if out.strip() else "(无 commit 输出)")
            if code != 0:
                self._log("❌ git commit 失败，请查看上方日志。")
                self._set_status("Push 失败")
                return

        # 7. git push -u origin branch
        code, out = run_git(["push", "-u", "origin", branch], cwd=local)
        self._log(out.strip() if out.strip() else "(无 push 输出)")

        # 8. Push 后清除 token（安全措施）
        if self.clean_token.get():
            run_git(["remote", "set-url", "origin", clean_url], cwd=local)
            self._log(f"[安全] token 已从 git 配置中移除，远程地址已还原为：{clean_url}")

        if code == 0:
            self._log("✅ Push 成功！")
            self._log("⚠️  建议在 GitHub 设置中定期轮换（regenerate）此 token。")
            self._set_status("Push 完成")
        else:
            self._log("❌ Push 失败，请查看上方日志。")
            self._set_status("Push 失败")

    # ── 操作：Pull ────────────────────────────────────────────────────────────

    def _on_pull(self):
        if not self._validate():
            return
        self._maybe_save_config()
        threading.Thread(target=self._pull_task, daemon=True).start()

    def _pull_task(self):
        local  = self.local_dir.get().strip()
        branch = self.branch.get().strip() or "master"
        user   = self.github_user.get().strip()
        repo   = self.repo_name.get().strip()
        token  = self.token.get().strip()

        remote_url = build_remote_url(user, repo, token)
        clean_url  = build_clean_url(user, repo)

        self._set_status("正在拉取…")
        self._log(f"\n{'='*50}")
        self._log(f"[Pull] 目录：{local}  分支：{branch}")

        if not os.path.isdir(os.path.join(local, ".git")):
            self._log("❌ 该目录不是 git 仓库，请先使用【Clone】按钮初始化。")
            self._set_status("Pull 失败")
            return

        self._setup_remote(local, remote_url)

        code, out = run_git(["pull", "origin", branch], cwd=local)
        self._log(out.strip() if out.strip() else "(无输出)")

        # 还原 remote（移除 token）
        if self.clean_token.get():
            run_git(["remote", "set-url", "origin", clean_url], cwd=local)
            self._log(f"[安全] token 已从 git 配置中移除。")

        if code == 0:
            self._log("✅ Pull 成功！")
            self._set_status("Pull 完成")
        else:
            self._log("❌ Pull 失败，请查看上方日志。")
            self._set_status("Pull 失败")

    # ── 操作：Clone ───────────────────────────────────────────────────────────

    def _on_clone(self):
        if not self._validate(need_local=False):
            return
        parent = filedialog.askdirectory(title="选择克隆到哪个父目录")
        if not parent:
            return
        self._maybe_save_config()
        threading.Thread(target=self._clone_task, args=(parent,), daemon=True).start()

    def _clone_task(self, parent: str):
        user   = self.github_user.get().strip()
        repo   = self.repo_name.get().strip()
        token  = self.token.get().strip()
        branch = self.branch.get().strip()

        remote_url = build_remote_url(user, repo, token)
        repo_name  = repo.replace(".git", "")
        target_dir = os.path.join(parent, repo_name)

        self._set_status("正在克隆…")
        self._log(f"\n{'='*50}")

        # 先尝试指定分支，失败则克隆默认分支
        if branch:
            self._log(f"[Clone] 目标目录：{target_dir}  分支：{branch}")
            code, out = run_git(["clone", "-b", branch, remote_url], cwd=parent)
            if code != 0:
                self._log(f"[警告] 分支 '{branch}' 不存在，改为克隆默认分支…")
                code, out = run_git(["clone", remote_url], cwd=parent)
        else:
            self._log(f"[Clone] 目标目录：{target_dir}  使用仓库默认分支")
            code, out = run_git(["clone", remote_url], cwd=parent)

        self._log(out.strip() if out.strip() else "(无输出)")

        if code == 0:
            # 检测实际分支（symbolic-ref 在空仓库也可用）
            b_code, b_out = run_git(["symbolic-ref", "--short", "HEAD"], cwd=target_dir)
            actual = b_out.strip() if b_code == 0 and b_out.strip() else (branch or "master")
            self._log(f"✅ Clone 成功！当前分支：{actual}")
            self._set_status("Clone 完成")
            self.after(0, lambda: self.branch.set(actual))
            self.after(0, lambda: self.local_dir.set(target_dir))
        else:
            self._log("❌ Clone 失败，请查看上方日志。")
            self._set_status("Clone 失败")


# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = App()
    app.mainloop()
