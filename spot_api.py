import time
import hmac
import hashlib
import requests
import json
import os
from datetime import datetime

from localdata.config.setting import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_BASE_URL, PROXY_URL, BASE_DIR


def get_signature(query_string: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def get_account(
    omitZeroBalances: bool = False,
    recvWindow: int = 5000,
):
    """
    获取账户信息

    Args:
        omitZeroBalances: 是否省略余额为零的资产 (默认 False)
        recvWindow: 接收窗口时间，单位毫秒，最大 60000 (默认 5000)
    """
    timestamp = int(time.time() * 1000)

    params = [f"timestamp={timestamp}"]

    if omitZeroBalances:
        params.append("omitZeroBalances=true")
    if recvWindow != 5000:
        params.append(f"recvWindow={recvWindow}")

    query_string = "&".join(params)
    signature = get_signature(query_string, BINANCE_API_SECRET)

    url = f"{BINANCE_BASE_URL}/api/v3/account?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    response = requests.get(url, headers=headers, proxies={"http": PROXY_URL, "https": PROXY_URL})
    print(f"Status: {response.status_code}")

    ts = datetime.now().strftime("%y%m%d_%H%M%S")
    filename = f"localdata/data/account/spot_account_{ts}.json"
    with open(filename, "w") as f:
        f.write(response.text)
    print(f"Saved to {filename}")


def get_order(
    symbol: str,
    orderId: int = None,
    origClientOrderId: str = None,
    recvWindow: int = 5000,
):
    """
    查询订单状态

    Args:
        symbol: 交易对，如 'BTCUSDT'
        orderId: 订单ID
        origClientOrderId: 客户端订单ID
        recvWindow: 接收窗口时间，单位毫秒，最大 60000 (默认 5000)

    Returns:
        订单信息
    """
    if not orderId and not origClientOrderId:
        raise ValueError("必须提供 orderId 或 origClientOrderId 之一")

    timestamp = int(time.time() * 1000)

    params = [f"symbol={symbol}", f"timestamp={timestamp}"]

    if orderId:
        params.append(f"orderId={orderId}")
    if origClientOrderId:
        params.append(f"origClientOrderId={origClientOrderId}")
    if recvWindow != 5000:
        params.append(f"recvWindow={recvWindow}")

    query_string = "&".join(params)
    signature = get_signature(query_string, BINANCE_API_SECRET)

    url = f"{BINANCE_BASE_URL}/api/v3/order?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    response = requests.get(url, headers=headers, proxies={"http": PROXY_URL, "https": PROXY_URL})
    return response.json()


def all_orders(
    symbol: str,
    orderId: int = None,
    startTime: int = None,
    endTime: int = None,
    limit: int = 500,
    recvWindow: int = 5000,
):
    """
    获取所有订单（包含历史订单）

    Args:
        symbol: 交易对，如 'BTCUSDT'
        orderId: 订单ID
        startTime: 开始时间（毫秒时间戳）
        endTime: 结束时间（毫秒时间戳）
        limit: 返回数量限制，默认 500，最大 1000
        recvWindow: 接收窗口时间，单位毫秒，最大 60000 (默认 5000)

    Returns:
        订单列表
    """
    timestamp = int(time.time() * 1000)

    params = [f"symbol={symbol}", f"timestamp={timestamp}"]

    if orderId:
        params.append(f"orderId={orderId}")
    if startTime:
        params.append(f"startTime={startTime}")
    if endTime:
        params.append(f"endTime={endTime}")
    if limit != 500:
        params.append(f"limit={limit}")
    if recvWindow != 5000:
        params.append(f"recvWindow={recvWindow}")

    query_string = "&".join(params)
    signature = get_signature(query_string, BINANCE_API_SECRET)

    url = f"{BINANCE_BASE_URL}/api/v3/allOrders?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    response = requests.get(url, headers=headers, proxies={"http": PROXY_URL, "https": PROXY_URL})
    return response.json()


def get_order_details_for_all_orders(symbol: str, limit: int = 100):
    """
    获取所有订单并逐个查询订单详情，保存到 order/ 目录

    Args:
        symbol: 交易对，如 'BTCUSDT'
        limit: 获取订单数量限制，默认 100

    Returns:
        所有订单的详细信息列表
    """
    order_dir = BASE_DIR / "data" / "order"
    order_dir.mkdir(parents=True, exist_ok=True)

    print(f"正在获取 {symbol} 的所有订单...")
    orders = all_orders(symbol=symbol, limit=limit)

    if isinstance(orders, dict) and "code" in orders:
        print(f"获取订单失败: {orders}")
        return []

    print(f"共获取到 {len(orders)} 个订单，开始逐个查询详情...")

    detailed_orders = []
    for i, order in enumerate(orders):
        order_id = order.get("orderId")
        print(f"[{i+1}/{len(orders)}] 查询订单详情, orderId: {order_id}")
        detail = get_order(symbol=symbol, orderId=order_id)
        detailed_orders.append(detail)

        # 保存每个订单详情到单独文件
        ts = datetime.now().strftime("%y%m%d_%H%M%S")
        filename = order_dir / f"{symbol}_order_{order_id}_{ts}.json"
        with open(filename, "w") as f:
            json.dump(detail, f, indent=2, ensure_ascii=False)
        print(f"  已保存: {filename}")

    # 保存所有订单详情汇总
    summary_file = order_dir / f"{symbol}_orders_summary_{datetime.now().strftime('%y%m%d_%H%M%S')}.json"
    with open(summary_file, "w") as f:
        json.dump(detailed_orders, f, indent=2, ensure_ascii=False)
    print(f"汇总已保存: {summary_file}")

    print(f"完成！共查询 {len(detailed_orders)} 个订单详情")
    return detailed_orders


def my_trades(
    symbol: str,
    orderId: int = None,
    startTime: int = None,
    endTime: int = None,
    fromId: int = None,
    limit: int = 500,
    recvWindow: int = 5000,
    save_to_file: bool = False,
):
    """
    获取成交记录（包含手续费信息）

    Args:
        symbol: 交易对，如 'BTCUSDT'
        orderId: 订单ID（可选，传入后只返回该订单的成交记录）
        startTime: 开始时间（毫秒时间戳）
        endTime: 结束时间（毫秒时间戳）
        fromId: 起始成交ID
        limit: 返回数量限制，默认 500，最大 1000
        recvWindow: 接收窗口时间，单位毫秒，最大 60000 (默认 5000)
        save_to_file: 是否保存到文件（默认 False）

    Returns:
        成交记录列表，包含 commission 和 commissionAsset 字段
    """
    timestamp = int(time.time() * 1000)

    params = [f"symbol={symbol}", f"timestamp={timestamp}"]

    if orderId:
        params.append(f"orderId={orderId}")
    if startTime:
        params.append(f"startTime={startTime}")
    if endTime:
        params.append(f"endTime={endTime}")
    if fromId:
        params.append(f"fromId={fromId}")
    if limit != 500:
        params.append(f"limit={limit}")
    if recvWindow != 5000:
        params.append(f"recvWindow={recvWindow}")

    query_string = "&".join(params)
    signature = get_signature(query_string, BINANCE_API_SECRET)

    url = f"{BINANCE_BASE_URL}/api/v3/myTrades?{query_string}&signature={signature}"
    headers = {"X-MBX-APIKEY": BINANCE_API_KEY}

    response = requests.get(url, headers=headers, proxies={"http": PROXY_URL, "https": PROXY_URL})
    trades = response.json()

    if save_to_file and trades:
        trade_dir = BASE_DIR / "data" / "order"
        trade_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%y%m%d_%H%M%S")
        if orderId:
            filename = trade_dir / f"{symbol}_trades_order_{orderId}_{ts}.json"
        else:
            filename = trade_dir / f"{symbol}_trades_{ts}.json"

        with open(filename, "w") as f:
            json.dump(trades, f, indent=2, ensure_ascii=False)
        print(f"成交记录已保存: {filename}")

    return trades


if __name__ == "__main__":
    # 获取所有订单
    orders = all_orders(symbol="BTCUSDT", limit=10)
    print(f"获取到 {len(orders)} 个订单")

    # 从订单列表中提取 orderId
    if orders and isinstance(orders, list) and len(orders) > 0:
        order_id = orders[0].get("orderId")
        print(f"使用 orderId: {order_id} 查询成交记录")

        # 查询该订单的成交记录（包含手续费），并保存到文件
        trades = my_trades(symbol="BTCUSDT", orderId=order_id, save_to_file=True)
        print(f"成交记录: {trades}")
    else:
        print("未获取到订单")
