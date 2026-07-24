import re


class ErrorParser:
    ERROR_PATTERNS = {
        "missing_module": {
            "pattern": r"ModuleNotFoundError|ImportError.*No module named",
            "solution": "请确保已安装缺失的依赖包，或在依赖列表中添加该模块"
        },
        "hidden_import": {
            "pattern": r"hiddenimport.*missing|not found in frozen",
            "solution": "在依赖管理中添加缺失的hiddenimports"
        },
        "icon_error": {
            "pattern": r"Unable to load icon|icon.*not found",
            "solution": "请检查图标文件路径是否正确，确保图标为有效的.ico格式"
        },
        "permission_error": {
            "pattern": r"PermissionError|Access is denied",
            "solution": "权限不足或文件被占用！\n1. 请关闭正在运行的同名程序\n2. 尝试以管理员身份运行本程序\n3. 检查输出目录是否有写入权限\n4. 尝试更换输出目录或输出文件名"
        },
        "file_not_found": {
            "pattern": r"FileNotFoundError|No such file or directory",
            "solution": "请检查源码文件路径是否正确"
        },
        "syntax_error": {
            "pattern": r"SyntaxError",
            "solution": "请检查Python源码是否有语法错误"
        },
        "upx_error": {
            "pattern": r"upx.*error|UPX is not available",
            "solution": "请检查UPX路径是否正确，或禁用UPX压缩"
        },
        "python_version": {
            "pattern": r"Python version.*not supported|incompatible Python",
            "solution": "请使用PyInstaller支持的Python版本（建议3.8-3.12）"
        },
        "memory_error": {
            "pattern": r"MemoryError",
            "solution": "打包过程内存不足，请尝试减少依赖或使用多文件模式"
        },
        "encoding_error": {
            "pattern": r"UnicodeEncodeError|encoding",
            "solution": "请确保文件路径和内容使用UTF-8编码"
        }
    }

    @staticmethod
    def parse_error(error_message):
        results = []
        for error_type, info in ErrorParser.ERROR_PATTERNS.items():
            if re.search(info["pattern"], error_message, re.IGNORECASE):
                results.append({
                    "type": error_type,
                    "pattern": info["pattern"],
                    "solution": info["solution"]
                })
        return results

    @staticmethod
    def get_solution(error_message):
        results = ErrorParser.parse_error(error_message)
        if results:
            return results[0]["solution"]
        return None

    @staticmethod
    def format_error_report(error_message):
        results = ErrorParser.parse_error(error_message)
        if not results:
            return "无法识别的错误，请查看详细日志"

        report = "错误诊断结果:\n"
        report += "=" * 50 + "\n"
        for i, result in enumerate(results, 1):
            report += f"\n[{i}] 错误类型: {result['type']}\n"
            report += f"   解决方案: {result['solution']}\n"
        report += "\n" + "=" * 50
        return report