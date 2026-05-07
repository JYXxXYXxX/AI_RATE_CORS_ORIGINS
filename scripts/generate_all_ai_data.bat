@echo off
chcp 65001 >nul
echo ============================================
echo AI 训练数据批量生成脚本
echo ============================================
echo.

setlocal enabledelayedexpansion

:: 创建输出目录
if not exist data\training mkdir data\training

:: 统计现有数据
echo [检查现有数据...]
set /a total=0
for %%f in (ai_zhipu.jsonl ai_tongyi.jsonl ai_yunwu.jsonl ai_ollama.jsonl ai_combined.jsonl) do (
    if exist data\training\%%f (
        for /f %%c in ('type data\training\%%f ^| find /c /v ""') do (
            echo   %%f: %%c 条
            set /a total+=%%c
        )
    )
)
echo 当前总计: %total% 条
echo.

:: 设置生成数量
set GEN_COUNT=300
set DELAY=1.0

echo [开始生成数据...]
echo 每个提供商生成 %GEN_COUNT% 条，延迟 %DELAY% 秒
echo.

:: 1. Yunwu (gpt-4o-mini) - 通常最稳定
echo [1/3] 正在使用 Yunwu (gpt-4o-mini) 生成数据...
set AI_GEN_API_KEY=sk-rjZc2w75YjjjDXjmADQS5bIqL2gAsbj0gB2RggsSpr1bff9F
set AI_GEN_BASE_URL=https://api.yunwu.ai/v1
set AI_GEN_MODEL=gpt-4o-mini
start /B cmd /c "python scripts/generate_ai_training_data.py --count %GEN_COUNT% --delay %DELAY% --output data/training/ai_yunwu.jsonl > data/training/log_yunwu.txt 2>&1"

:: 2. Ollama 本地 (如果运行中)
echo [2/3] 正在使用 Ollama (qwen2.5:7b) 生成数据...
set AI_GEN_BASE_URL=http://127.0.0.1:11434/v1
set AI_GEN_MODEL=qwen2.5:7b
start /B cmd /c "python scripts/generate_ai_training_data.py --count %GEN_COUNT% --delay 0.5 --output data/training/ai_ollama.jsonl > data/training/log_ollama.txt 2>&1"

:: 3. 智谱 AI
echo [3/3] 正在使用 Zhipu (glm-4-plus) 生成数据...
set AI_GEN_API_KEY=9a963fc602bf467a8d807bf61f648b92.C3ZdihQVUmEoekLq
set AI_GEN_BASE_URL=https://open.bigmodel.cn/api/paas/v4
set AI_GEN_MODEL=glm-4-plus
start /B cmd /c "python scripts/generate_ai_training_data.py --count %GEN_COUNT% --delay %DELAY% --output data/training/ai_zhipu.jsonl > data/training/log_zhipu.txt 2>&1"

echo.
echo ============================================
echo 所有生成任务已在后台启动！
echo ============================================
echo.
echo 查看进度:
echo   - 日志文件: data/training/log_*.txt
echo   - 数据文件: data/training/ai_*.jsonl
echo.
echo 合并数据命令:
echo   type data\training\ai_*.jsonl ^> data\training\ai_all.jsonl
echo.
echo 训练模型命令:
echo   python scripts/train_aigc_model.py
echo.

pause
