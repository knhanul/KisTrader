from typing import List, Dict, Any, Optional
from datetime import date

from app.database import execute_query, execute_update, execute_single_query


def upsert_stock_master(symbol: str, name: str, market: str, instrument_type: str = "STOCK", is_active: bool = True, source: str = "NAVER") -> int:
    """종목 마스터 upsert"""
    query = """
    INSERT INTO stock_master (symbol, name, market, instrument_type, is_active, source, created_at, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
    ON CONFLICT (symbol) 
    DO UPDATE SET 
        name = EXCLUDED.name,
        market = EXCLUDED.market,
        instrument_type = EXCLUDED.instrument_type,
        is_active = EXCLUDED.is_active,
        source = EXCLUDED.source,
        updated_at = NOW()
    """
    return execute_update(query, (symbol, name, market, instrument_type, is_active, source))


def insert_listing_history(symbol: str, name: str, market: str, instrument_type: str, is_active: bool, effective_date: date, source: str = "NAVER") -> int:
    """종목 상장 이력 추가"""
    query = """
    INSERT INTO instrument_listing_history (symbol, name, market, instrument_type, is_active, effective_date, source, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
    """
    return execute_update(query, (symbol, name, market, instrument_type, is_active, effective_date, source))


def get_all_active_stocks() -> List[Dict[str, Any]]:
    """활성화된 모든 종목 조회"""
    query = """
    SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
    FROM stock_master
    WHERE is_active = true
    ORDER BY market, symbol
    """
    return execute_query(query)


def search_stocks_by_name(keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """종목명으로 검색"""
    words = keyword.strip().split()
    
    if len(words) == 1:
        # 단어 1개: 앞뒤에 % 붙이기
        search_pattern = f"%{words[0]}%"
        query = """
        SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
        FROM stock_master
        WHERE is_active = true AND name ILIKE %s
        ORDER BY 
            CASE WHEN name = %s THEN 1 ELSE 2 END,
            CASE WHEN name ILIKE %s THEN 2 ELSE 3 END,
            name
        LIMIT %s
        """
        params = (search_pattern, words[0], f"{words[0]}%", limit)
        print(f"[DB 검색] 단어 1개: '{keyword}' -> pattern: '{search_pattern}'")
    else:
        # 단어 2개 이상: 단어 사이에 % 붙이기
        search_pattern = f"%{'%'.join(words)}%"
        query = """
        SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
        FROM stock_master
        WHERE is_active = true AND name ILIKE %s
        ORDER BY 
            CASE WHEN name = %s THEN 1 ELSE 2 END,
            CASE WHEN name ILIKE %s THEN 2 ELSE 3 END,
            name
        LIMIT %s
        """
        params = (search_pattern, keyword, f"{keyword}%", limit)
        print(f"[DB 검색] 단어 {len(words)}개: '{keyword}' -> pattern: '{search_pattern}'")
    
    result = execute_query(query, params)
    print(f"[DB 검색] 결과: {len(result)}개")
    return result


def get_stock_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """종목코드로 종목 조회"""
    query = """
    SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
    FROM stock_master
    WHERE symbol = %s
    """
    return execute_single_query(query, (symbol,))


def get_stocks_by_market(market: str) -> List[Dict[str, Any]]:
    """시장별 종목 조회"""
    query = """
    SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
    FROM stock_master
    WHERE is_active = true AND market = %s
    ORDER BY symbol
    """
    return execute_query(query, (market,))


def get_etf_stocks() -> List[Dict[str, Any]]:
    """ETF 종목만 조회"""
    query = """
    SELECT symbol, name, market, instrument_type, is_active, source, created_at, updated_at
    FROM stock_master
    WHERE is_active = true AND instrument_type = 'ETF'
    ORDER BY symbol
    """
    return execute_query(query)


def update_stock_status(symbol: str, is_active: bool) -> int:
    """종목 활성 상태 업데이트"""
    query = """
    UPDATE stock_master
    SET is_active = %s, updated_at = NOW()
    WHERE symbol = %s
    """
    return execute_update(query, (is_active, symbol))
