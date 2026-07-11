# TeX environment acceptance report

验收时间：2026-07-11 08:56（Asia/Shanghai）  
结论：**passed**。TeX Live 2026 full scheme 已安装，中文、公式、booktabs 表格和实际生成图片通过 `latexmk -xelatex` 真实编译。

## 安装来源与方式

- 官方安装器来源：`https://mirror.ctan.org/systems/texlive/tlnet/install-tl-windows.exe`。
- 官方 `install-tl.zip.sha512` 校验通过；期望值与实际值均为 `b43dc5a4ab9d7e3696d67b776021bfbd66a47ff90ff667f454d06558d06fa0d533627ae0ad52f783c5e269bc4cb2a828446bdeeaec37b7ca3558420831c432de`。
- 实际安装仓库：USTC CTAN 镜像 `https://mirrors.ustc.edu.cn/CTAN/systems/texlive/tlnet`。
- 安装目录：`D:/texlive/2026`。
- profile：`artifacts/environment_check/installer/texlive.profile`，其中 `selected_scheme scheme-full`、`instopt_adjustpath 0`。
- 安装命令使用官方 `install-tl-windows.bat --profile ... --repository ... --non-admin`，退出码 `0`，耗时 `4192.431` 秒。
- 未持久化修改系统 PATH；验收仅为当前进程设置 `MMAGENT_TEX_BIN` 和 PATH 前缀。

安装证据见：

- `artifacts/environment_check/installer/download.json`
- `artifacts/environment_check/installer/installer-verification.json`
- `artifacts/environment_check/logs/texlive-install-ustc.json`
- `artifacts/environment_check/logs/texlive-install-ustc.log`

## 工具与宏包检查

实际运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\artifacts\environment_check\check_tex_environment.ps1 -TexBin D:\texlive\2026\bin\windows
```

所有验收命令退出码均为 `0`：

- `where.exe xelatex`：解析到 `D:\texlive\2026\bin\windows\xelatex.exe`。
- `xelatex --version`：XeTeX `3.141592653-2.6-0.999998`，TeX Live 2026，kpathsea 6.4.2。
- `where.exe latexmk`：解析到 `D:\texlive\2026\bin\windows\latexmk.exe`。
- `latexmk -v`：Latexmk 4.88（2026-03-09）。
- `tlmgr info --only-installed scheme-full`：`installed: Yes`。
- `kpsewhich ctexart.cls`：`d:/texlive/2026/texmf-dist/tex/latex/ctex/ctexart.cls`。
- `kpsewhich booktabs.sty`：`d:/texlive/2026/texmf-dist/tex/latex/booktabs/booktabs.sty`。
- `kpsewhich graphicx.sty`：`d:/texlive/2026/texmf-dist/tex/latex/graphics/graphicx.sty`。
- `kpsewhich amsmath.sty`：`d:/texlive/2026/texmf-dist/tex/latex/amsmath/amsmath.sty`。

逐命令 stdout、stderr、时间和退出码保存在 `artifacts/environment_check/tex_environment_results.json` 与 `artifacts/environment_check/logs/`。`tlmgr` 在当前 Windows locale 下产生 Perl locale warning，但本地已安装 scheme 查询成功，不影响验收结果。

## 中文编译验收

源文件 `artifacts/environment_check/source/main.tex` 使用 `ctexart`、`amsmath`、`booktabs`、`graphicx`，包含中文标题和正文、数学公式、表格及实际生成的 `acceptance-image.png`。实际编译命令为：

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

结果：

- PDF：`artifacts/environment_check/pdf/xelatex_chinese_acceptance.pdf`
- 大小：109,232 bytes
- 文件头：`%PDF-`
- SHA-256：`65de5846b4cd61df9750e3fa3dab99f5dba46bfc51cbd73c348305c696679036`
- latexmk 退出码：`0`
- 底层 XeLaTeX 日志：`artifacts/environment_check/logs/chinese-acceptance-xelatex.log`
- 完整命令日志：`artifacts/environment_check/logs/latexmk-chinese-acceptance.stdout.log` 与 `.stderr.log`

该 PDF 只用于工具链验收，不是竞赛论文或正式报告。
