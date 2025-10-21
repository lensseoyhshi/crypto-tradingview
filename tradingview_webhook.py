# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify
import json
import logging
from datetime import datetime
import ccxt
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('webhook.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局配置
CAPITAL = None
LEVERAGE = None
exchange = None
WECHAT_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=83dd158e-e006-4c8f-b2b4-679a21da892e"


def init_exchange():
    """初始化交易所"""
    global exchange, CAPITAL, LEVERAGE
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)

        gateio_config = config['gateio']

        # 从配置文件读取本金和杠杆
        CAPITAL = gateio_config.get('capital', 30)
        LEVERAGE = gateio_config.get('leverage', 3)

        exchange = ccxt.gateio({
            'apiKey': gateio_config['apiKey'],
            'secret': gateio_config['secret'],
            'options': {'defaultType': 'swap'},  # 使用永续合约，最小数量更小
        })

        logger.info(f"交易所初始化成功 - 本金: {CAPITAL}U, 杠杆: {LEVERAGE}x")
        return True
    except Exception as e:
        logger.error(f"初始化交易所失败: {e}")
        return False


def send_wechat(message):
    """发送企业微信通知"""
    try:
        requests.post(WECHAT_WEBHOOK_URL, json={
            "msgtype": "text",
            "text": {
                "content": message
            }
        })
        logger.info("企业微信通知发送成功")
    except Exception as e:
        logger.error(f"企业微信通知失败: {e}")


def close_position(symbol):
    """平仓"""
    try:
        positions = exchange.fetch_positions([symbol])
        for pos in positions:
            # Gate.io 使用 'contracts' 字段表示持仓数量
            contracts = float(pos.get('contracts', 0))
            if contracts != 0:
                side = 'sell' if pos['side'] == 'long' else 'buy'
                amount = abs(contracts)

                exchange.create_order(symbol, 'market', side, amount)
                logger.info(f"平仓成功: {symbol}, 方向: {pos['side']}, 数量: {amount}")
                send_wechat(f"平仓: {symbol} {pos['side']} {amount}")
                return True
        return False
    except Exception as e:
        logger.error(f"平仓失败: {e}")
        return False


def open_position(action, symbol):
    """开仓"""
    try:
        # 1. 设置杠杆
        exchange.set_leverage(LEVERAGE, symbol)

        # 2. 平掉现有持仓
        close_position(symbol)

        # 3. 获取当前市价
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']

        # 4. 计算持仓数量
        amount = (CAPITAL * LEVERAGE) / current_price

        # 精度调整 - 使用交易所的精度格式化方法
        amount = float(exchange.amount_to_precision(symbol, amount))

        # 检查最小交易数量
        markets = exchange.load_markets()
        min_amount = markets[symbol].get('limits', {}).get('amount', {}).get('min', 0)
        if min_amount > 0 and amount < min_amount:
            need_capital = min_amount * current_price / LEVERAGE
            error_msg = f"数量不足: {amount:.4f} < {min_amount}，需要至少 {need_capital:.2f}U 本金"
            logger.error(error_msg)
            send_wechat(f"⚠️ {error_msg}")
            return False

        # 5. 开仓
        if action == 'buy':
            order = exchange.create_market_buy_order(symbol, amount)
            side = 'buy'
        else:
            order = exchange.create_market_sell_order(symbol, amount)
            side = 'sell'

        logger.info(f"开仓成功: {symbol} {side} {amount} @ {current_price}")

        msg = f"""交易执行成功:
{symbol}
方向: {side}
市价: {current_price}
数量: {amount}
杠杆: {LEVERAGE}x
本金: {CAPITAL}U"""
        send_wechat(msg)

        return True

    except Exception as e:
        logger.error(f"开仓失败: {e}")
        send_wechat(f"交易失败: {symbol} {action} - {e}")
        return False


@app.route('/webhook', methods=['POST'])
def webhook():
    """接收TradingView信号"""
    try:
        data = request.get_json()
        logger.info(f"收到信号: {data}")

        # 只需要 action 和 symbol
        action = data.get('action')  # buy 或 sell
        symbol = 'ETH/USDT:USDT'  # 如: BTCUSDT 或 BTC/USDT:USDT

        if not action or not symbol:
            return jsonify({'error': '缺少action或symbol参数'}), 400

        # 只处理ETH的单子
        if 'ETH' not in symbol.upper():
            logger.info(f"忽略非ETH信号: {symbol}")
            return jsonify({'status': 'ignored', 'message': '只接受ETH交易信号'}), 200

        # 转换symbol格式：ETHUSDT -> ETH/USDT:USDT
        if '/' not in symbol:
            # 处理 TradingView 的 ticker 格式，如 ETHUSDT
            if symbol.endswith('USDT'):
                base = symbol[:-4]  # 去掉 USDT
                symbol = f"{base}/USDT:USDT"
            else:
                symbol = f"{symbol}/USDT:USDT"

        # 执行交易（使用市价）
        success = open_position(action, symbol)

        if success:
            return jsonify({'status': 'success'}), 200
        else:
            return jsonify({'status': 'error'}), 500

    except Exception as e:
        logger.error(f"处理失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'time': datetime.now().isoformat()}), 200


if __name__ == '__main__':
    if init_exchange():
        logger.info("Webhook服务启动...")
        logger.info("地址: http://0.0.0.0:8000/webhook")
        app.run(host='0.0.0.0', port=8000, debug=False)
    else:
        logger.error("启动失败")
