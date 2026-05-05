# 公考面试AI测评 uni-app 小程序端

这是现有 `civil-interview-frontend` 的并行小程序前端，基于 uni-app + Vue 3 构建。网页端目录保持不变，小程序端默认复用 `civil-interview-backend` 的业务 API。

## 开发

```bash
cd civil-interview-miniprogram
npm install
cp .env.example .env
npm run dev:mp-weixin
```

将 `unpackage/dist/dev/mp-weixin` 导入微信开发者工具即可预览。

默认 API 地址为 `http://127.0.0.1:8050`。微信开发者工具运行在 Windows 时，`127.0.0.1` 指向 Windows 本机；如果后端跑在 WSL、虚拟机、远程服务器或另一台电脑上，请在 `.env` 中将 `VITE_API_BASE` 改成 Windows/手机可访问的地址，例如：

```env
VITE_API_BASE=http://192.168.1.23:8050
```

修改 `.env` 后必须重新构建：

```bash
npm run build:mp-weixin
```

然后把 `dist/build/mp-weixin` 导入微信开发者工具。不要导入 `civil-interview-miniprogram` 源码目录，否则微信工具会提示根目录找不到 `app.json`。

## 页面覆盖

- 登录 / 注册
- 首页数据概览
- 题库列表与题目详情
- 模考准备、录音 / 文本作答、评分结果
- 历史记录
- 定向备面与重点分析
- 专项训练
- 套餐演示与个人中心
