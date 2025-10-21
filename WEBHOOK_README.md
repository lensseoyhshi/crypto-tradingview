# TradingView Webhook 交易机器人

这个脚本用于接收 TradingView 的 webhook 回调，并在 Gate.io 交易所执行自动交易。

## 功能特性

- 接收 TradingView webhook 信号
- 固定本金 30U 开仓
- 3倍杠杆交易
- 自动关闭现有持仓后开新仓
- 飞书通知集成
- 完整的日志记录

## 配置要求

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置 config.json
在 `config.json` 文件中添加你的 Gate.io API 配置：

```json
{
    "gateio": {
        "apiKey": "你的API密钥",
        "secret": "你的API密钥密码",
        "leverage": 3.0,
        "stop_loss_pct": 2,
        "low_trail_stop_loss_pct": 0.2,
        "trail_stop_loss_pct": 0.2,
        "higher_trail_stop_loss_pct": 0.25,
        "low_trail_profit_threshold": 0.3,
        "first_trail_profit_threshold": 1.0,
        "second_trail_profit_threshold": 3.0,
        "blacklist": []
    },
    "feishu_webhook": "你的飞书机器人webhook地址"
}
```

### 3. API 权限设置
确保你的 Gate.io API 具有以下权限：
- 期货交易权限
- 读取账户信息权限
- 读取持仓信息权限

## 使用方法

### 1. 启动服务器
```bash
python tradingview_webhook.py
```

服务器将在 `http://localhost:5000` 启动

### 2. 配置 TradingView
在 TradingView 的策略中，设置 webhook URL 为：
```
http://你的服务器IP:5000/webhook
```

### 3. TradingView 信号格式
TradingView 需要发送以下格式的 JSON 数据：
```json
{
  "action": "{{strategy.order.action}}",
  "symbol": "{{ticker}}",
  "price": {{close}},
  "timestamp": "{{timenow}}"
}
```

支持的 action 值：
- `buy` 或 `long`: 开多仓
- `sell` 或 `short`: 开空仓

## API 接口

### 1. Webhook 接收
- **URL**: `POST /webhook`
- **功能**: 接收 TradingView 信号并执行交易

### 2. 健康检查
- **URL**: `GET /health`
- **功能**: 检查服务器状态

### 3. 状态查询
- **URL**: `GET /status`
- **功能**: 查询机器人状态和账户余额

## 交易逻辑

1. **接收信号**: 接收 TradingView webhook 信号
2. **验证数据**: 验证必要字段是否存在
3. **设置杠杆**: 为交易对设置 3倍杠杆
4. **关闭现有持仓**: 如果有现有持仓，先关闭
5. **计算持仓数量**: 基于 30U 本金和 3倍杠杆计算
6. **执行交易**: 使用市价单开仓
7. **发送通知**: 通过飞书发送交易结果通知

## 风险提示

⚠️ **重要提醒**：
- 这是一个自动交易系统，请确保充分理解风险
- 建议先在测试环境中验证
- 确保 API 密钥安全，不要泄露给他人
- 定期检查日志文件，监控交易情况
- 建议设置合理的止损策略

## 日志文件

日志文件存储在 `log/tradingview_webhook.log`，包含：
- 接收到的信号记录
- 交易执行结果
- 错误信息
- 系统状态信息

## 故障排除

1. **配置文件错误**: 检查 `config.json` 格式和内容
2. **API 连接失败**: 验证 API 密钥和网络连接
3. **交易失败**: 检查账户余额和交易对有效性
4. **Webhook 接收失败**: 确认服务器端口开放和防火墙设置

## 技术支持

如有问题，请查看日志文件获取详细错误信息。

