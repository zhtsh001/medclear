# MedClear

Experimental Python code for extracting university immunization policies and reviewing user-supplied PDFs with Google's Gemini API. This is a research prototype, not medical advice, a diagnostic tool, or an authoritative university compliance decision.

## Privacy-first public source

This public repository starts from a clean code snapshot. It does not include patient records, vaccination PDFs, audit outputs, case registries, credentials, or the previous private repository's commit history. Do not upload real medical data to GitHub.

The bundled university policy files are historical development inputs, not a statement of current requirements. Verify the applicable rules independently before using this prototype. Model outputs and inferred dates require qualified human review.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY='your-own-key'
```

`GEMINI_MODEL` optionally overrides the model name. Provider access, model availability, pricing and data processing terms must be checked for your account. This code sends supplied PDFs and policy text to Google's API; only use documents you are authorized to process and after reviewing the provider's privacy terms.

## Command-line usage

Supply your own authorized documents outside the repository, and run from a private working directory because audit results are written into the current directory:

```sh
python /path/to/medclear/main.py --pdf /private/path/input.pdf --policy /path/to/policy.json --age 25
python /path/to/medclear/re_audit.py --original /private/path/input.pdf --supplement /private/path/supplement.pdf --policy /path/to/policy.json --age 25
```

The age above is a fictional command example, not a bundled patient case. Policy extraction is available through `python Policy_Extraction/policy_extraction.py`; its paths resolve relative to the script instead of a developer's home directory.

The `demo-ui-flow` branch preserves the local Flask demo's source. It begins with an empty case registry and no sample medical reports. It is a local prototype without production authentication or a privacy/compliance hardening review; do not expose it to the Internet. Removed sample reports cannot be used as fallbacks.

## 中文说明

本仓库仅公开净化后的实验代码，不包含医疗 PDF、接种记录、审查结果、案例登记数据、API 密钥或旧私有仓库的提交历史。密钥通过 `GEMINI_API_KEY` 环境变量提供，真实资料和生成结果请保存在私有位置。

程序会将你提供的文件提交给 Google Gemini API。请先确认有权处理相关资料并了解服务商的数据政策。它不是医疗建议，也不能替代学校或专业人员的审核；内置政策仅为历史开发输入。`demo-ui-flow` 分支保留本地演示页面代码，不应直接部署到公网。
