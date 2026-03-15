from typing import List, Dict, Any, Optional
from datetime import date

from app.database import execute_query, execute_update, execute_single_query


def upsert_investor_intraday_trade(
    trade_date: date,
    symbol: str,
    market: str,
    time_slot: str,
    investor_type: str,
    net_buy_amount: int = None,
    net_buy_volume: int = None,
    buy_amount: int = None,
    sell_amount: int = None,
    buy_volume: int = None,
    sell_volume: int = None,
    source: str = "KIS"
) -> int:
    """시간대별 투자자 거래 데이터 upsert"""
    query = """
    INSERT INTO investor_intraday_trade (
        trade_date, symbol, market, time_slot, investor_type,
        net_buy_amount, net_buy_volume, buy_amount, sell_amount,
        buy_volume, sell_volume, source, created_at, updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (trade_date, symbol, time_slot, investor_type)
    DO UPDATE SET
        market = EXCLUDED.market,
        net_buy_amount = EXCLUDED.net_buy_amount,
        net_buy_volume = EXCLUDED.net_buy_volume,
        buy_amount = EXCLUDED.buy_amount,
        sell_amount = EXCLUDED.sell_amount,
        buy_volume = EXCLUDED.buy_volume,
        sell_volume = EXCLUDED.sell_volume,
        source = EXCLUDED.source,
        updated_at = NOW()
    """
    return execute_update(
        query,
        (
            trade_date, symbol, market, time_slot, investor_type,
            net_buy_amount, net_buy_volume, buy_amount, sell_amount,
            buy_volume, sell_volume, source
        )
    )


def get_investor_intraday_by_symbol_date(symbol: str, trade_date: date) -> List[Dict[str, Any]]:
    """종목별 날짜 시간대별 투자자 데이터 조회"""
    query = """
    SELECT trade_date, symbol, market, time_slot, investor_type,
           net_buy_amount, net_buy_volume, buy_amount, sell_amount,
           buy_volume, sell_volume, source, created_at, updated_at
    FROM investor_intraday_trade
    WHERE symbol = %s AND trade_date = %s
    ORDER BY time_slot, investor_type
    """
    return execute_query(query, (symbol, trade_date))


def get_investor_intraday_by_date(trade_date: date) -> List[Dict[str, Any]]:
    """날짜별 모든 시간대별 투자자 데이터 조회"""
    query = """
    SELECT trade_date, symbol, market, time_slot, investor_type,
           net_buy_amount, net_buy_volume, buy_amount, sell_amount,
           buy_volume, sell_volume, source, created_at, updated_at
    FROM investor_intraday_trade
    WHERE trade_date = %s
    ORDER BY symbol, time_slot, investor_type
    """
    return execute_query(query, (trade_date,))


def get_investor_summary_by_symbol_date(symbol: str, trade_date: date) -> List[Dict[str, Any]]:
    """종목별 날짜 투자자 요약 조회"""
    query = """
    SELECT 
        trade_date,
        symbol,
        investor_type,
        SUM(net_buy_amount) as total_net_buy_amount,
        SUM(net_buy_volume) as total_net_buy_volume,
        SUM(buy_amount) as total_buy_amount,
        SUM(sell_amount) as total_sell_amount,
        SUM(buy_volume) as total_buy_volume,
        SUM(sell_volume) as total_sell_volume
    FROM investor_intraday_trade
    WHERE symbol = %s AND trade_date = %s
    GROUP BY trade_date, symbol, investor_type
    ORDER BY investor_type
    """
    return execute_query(query, (symbol, trade_date))


def get_top_investor_trades_by_date(trade_date: date, investor_type: str, limit: int = 10) -> List[Dict[str, Any]]:
    """날짜별 특정 투자자 타입 순매수 상위 종목"""
    query = """
    SELECT 
        trade_date,
        symbol,
        market,
        SUM(net_buy_amount) as total_net_buy_amount,
        SUM(net_buy_volume) as total_net_buy_volume
    FROM investor_intraday_trade
    WHERE trade_date = %s AND investor_type = %s
    GROUP BY trade_date, symbol, market
    HAVING SUM(net_buy_amount) IS NOT NULL
    ORDER BY SUM(net_buy_amount) DESC
    LIMIT %s
    """
    return execute_query(query, (trade_date, investor_type, limit))


def delete_investor_intraday_by_date(trade_date: date) -> int:
    """날짜별 시간대별 투자자 데이터 삭제 (재실행용)"""
    query = """
    DELETE FROM investor_intraday_trade
    WHERE trade_date = %s
    """
    return execute_update(query, (trade_date,))


def get_latest_trade_date() -> Optional[date]:
    """가장 최신 거래일 조회"""
    query = """
    SELECT MAX(trade_date) as latest_date
    FROM investor_intraday_trade
    """
    result = execute_single_query(query)
    return result["latest_date"] if result and result["latest_date"] else None
