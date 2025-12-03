"""FastAPI 应用启动脚本

使用方法:
    python run_server.py

或者使用 uvicorn 直接启动:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

import uvicorn
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下自动重载
        log_level="info"
    )
