# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mcpAI.router import router as mcpRouter, lifespan  # 从 router.py 导入 router 和 lifespan
from py_planx_ad.router import router as adRouter
# 创建 FastAPI 应用并绑定 lifespan
app = FastAPI(lifespan=lifespan)

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载 router，添加前缀（可选）
app.include_router(mcpRouter)
app.include_router(adRouter)

# 可选：添加一个根路由用于测试
@app.get("/")
async def root():
    return {"message": "Welcome to the AI Assistant API"}

# 定义 main 函数
def main():
    """启动 FastAPI 应用的主函数"""
    uvicorn.run(
        "backend:app",  # 模块名:应用实例名
        host="0.0.0.0",  # 监听所有 IP
        port=59006,       # 默认端口
        reload=True      # 开发模式，启用热重载
    )

if __name__ == "__main__":
    import uvicorn
    main()