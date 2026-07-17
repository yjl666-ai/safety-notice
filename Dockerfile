FROM python:3.11-slim

WORKDIR /app

# 清华镜像加速 pip
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用文件
COPY app.py ./
COPY ai_suggest.py ./
COPY generate_notice.py ./
COPY notice.yaml.example ./

# HuggingFace Spaces 默认端口
ENV PORT=7860
ENV HOST=0.0.0.0
EXPOSE 7860

CMD ["python", "app.py"]
