# Windows setup

## Python

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-cache-dir -e ".[dev]"
python -m pip check
```

## TeX Live 2026

本项目需要完整的 XeLaTeX 中文工具链。官方入口是 [TUG 网络安装页](https://tug.org/texlive/acquire-netinstall.html)提供的 `install-tl-windows.exe` 或 `install-tl.zip`；[官方安装器文档](https://tug.org/texlive/doc/install-tl.html)说明默认并推荐 `scheme-full`。本仓库环境验收采用 profile 无人值守安装到：

```text
D:\texlive\2026
```

profile 位于 `artifacts/environment_check/installer/texlive.profile`。它关闭 PATH 持久修改、桌面集成和文件关联，因此安装后需刷新当前会话：

```powershell
$env:MMAGENT_TEX_BIN = 'D:\texlive\2026\bin\windows'
$env:Path = "$env:MMAGENT_TEX_BIN;$env:Path"
```

验收命令：

```powershell
where.exe xelatex
xelatex --version
where.exe latexmk
latexmk -v
kpsewhich ctexart.cls
kpsewhich booktabs.sty
kpsewhich graphicx.sty
kpsewhich amsmath.sty
```

随后运行 `mmagent doctor` 和真实测试。安装器、压缩包和解压目录已加入 `.gitignore`；TeX Live 本体位于仓库外，不得提交。

仓库内的完整环境验收命令为：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\artifacts\environment_check\check_tex_environment.ps1 -TexBin D:\texlive\2026\bin\windows
```

`-ExecutionPolicy Bypass` 只作用于该子进程，不修改系统或用户级执行策略。当前实测结果、版本、逐命令日志和中文测试 PDF 见 [TeX 环境验收报告](tex_environment_report.md)。

网络安装仓库使用 [CTAN 官方镜像列表](https://ctan.org/mirrors)中的 HTTPS 镜像。安装器 zip 的 SHA-512 已与 CTAN 同目录校验文件核对，记录见 `artifacts/environment_check/installer/installer-verification.json`。

如果使用其他路径，不要修改业务代码；只需在当前会话设置 `MMAGENT_TEX_BIN` 和 PATH。不要把个人目录或学校身份写入论文源文件。
