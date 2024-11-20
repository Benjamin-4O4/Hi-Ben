from fastapi import FastAPI
from services.dida365.auth.callback_handler import DidaCallbackHandler

app = FastAPI()

# 注册滴答清单回调处理器
dida_callback = DidaCallbackHandler(app)
