# 如何配置 .agent 目录：Git 忽略但 IDE 可见

本文档记录了如何配置项目，使得 `.agent` 目录被 Git 忽略（不上传），但在 VS Code IDE 中完全可见且可用（支持 Slash Commands `/`）。

## 核心原理

1.  **Git 忽略**：使用 `.git/info/exclude` 替代 `.gitignore`。这两个文件都能让 Git 忽略文件，但 `.gitignore` 通常会被 IDE 和工具扫描以确定"排除范围"，而 `.git/info/exclude` 是本地的、隐蔽的。
2.  **IDE 强制可见**：在 `.vscode/settings.json` 中显式配置不排除该目录，并强制文件监听器工作。

---

## 步骤 1：Git 配置 (实现隐私)

目标：确保 Git 不追踪 `.agent` 目录，也不将其上传。

1.  **清理 `.gitignore`**
    *   打开项目根目录下的 `.gitignore` 文件。
    *   **删除**其中关于 `.agent` 的行（例如 `.agent` 或 `.agent/*`）。
    *   保存文件。

2.  **设置本地排除**
    *   打开（或创建）文件：`.git/info/exclude` (这是个隐藏目录)。
    *   在文件末尾添加一行：
        ```text
        .agent
        ```
    *   保存文件。

    > **验证**：在终端运行 `git check-ignore -v .agent/some_file`，应该显示 `.git/info/exclude` 来源。

---

## 步骤 2：VS Code 配置 (实现可见性)

目标：确保 VS Code 的资源管理器、搜索和文件监听器能正常处理该目录。

1.  **创建/编辑配置**
    *   确认目录 `.vscode` 存在（如果是文件则删除并新建为目录）。
    *   打开 `.vscode/settings.json`。

2.  **添加以下配置**
    复制并合并到你的 json 文件中：

    ```json
    {
        "search.useIgnoreFiles": false,
        "files.exclude": {
            "**/.agent": false
        },
        "search.exclude": {
            "**/.agent": false
        },
        "files.watcherExclude": {
            "**/.agent": false
        }
    }
    ```

    *   `files.exclude`: `false` 确保在左侧资源管理器中显示。
    *   `search.useIgnoreFiles`: `false` 允许搜索器搜索被 Git 忽略的文件。
    *   `files.watcherExclude`: `false` **(关键)** 强制 VS Code 的文件监听器监视该目录。这对于依赖文件索引的工具（如 Slash Commands）至关重要。

---

## 步骤 3：重启 IDE

1.  修改 `files.watcherExclude` 后，必须**重启窗口**才能生效。
2.  快捷键：`Cmd + Shift + P` -> 输入 `Reload Window` -> 回车。

---

## 结果验证

*   ✅ **Git**: 运行 `git status`，不应看到 `.agent` 目录。
*   ✅ **IDE**: 在 VS Code 左侧能看到 `.agent` 目录。
*   ✅ **工具**: 在输入框键入 `/`，应该能看到 `brainstorm`、`plan` 等工作流命令。
