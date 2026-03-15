import datetime
import json
import sys
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from app.config import settings
from app.naver_service import fetch_etf_items

app = FastAPI(title="KIS FastAPI Server")
BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_FILE = BASE_DIR / "index.html"
STOCK_CACHE_FILE = Path(settings.stock_cache_file)
TOKEN_CACHE_FILE = Path(settings.token_cache_file)
TOKEN_CACHE: dict[str, Any] = {}
STOCK_INDEX: list[dict[str, str]] = []
STOCK_NAME_LOOKUP: dict[str, list[dict[str, str]]] = {}

# 로그 출력 설정
def log_print(message: str) -> None:
    """강제 로그 출력"""
    print(message, flush=True)
    sys.stdout.flush()


def validate_settings() -> None:
    if not settings.kis_app_key or not settings.kis_app_secret:
        raise HTTPException(status_code=500, detail="KIS_APP_KEY 또는 KIS_APP_SECRET 환경변수가 설정되지 않았습니다.")


def save_token_cache(token: str, timestamp: float) -> None:
    try:
        cache_data = {"access_token": token, "timestamp": timestamp}
        TOKEN_CACHE_FILE.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except (OSError, IOError):
        TOKEN_CACHE["access_token"] = token


def load_token_cache() -> tuple[str | None, float | None]:
    try:
        if not TOKEN_CACHE_FILE.exists():
            return None, None
        data = json.loads(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
        token = data.get("access_token")
        timestamp = data.get("timestamp")
        if isinstance(token, str) and isinstance(timestamp, (int, float)):
            return token, float(timestamp)
        return None, None
    except (json.JSONDecodeError, OSError, IOError, KeyError, TypeError):
        return None, None


def is_token_valid(timestamp: float) -> bool:
    current_time = datetime.datetime.now().timestamp()
    return (current_time - timestamp) < (23 * 60 * 60)


def parse_int(value: Any) -> int:
    text = str(value or "0").replace(",", "").strip()
    if text == "":
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def save_stock_cache(stocks: list[dict[str, str]]) -> None:
    STOCK_CACHE_FILE.write_text(json.dumps(stocks, ensure_ascii=False, indent=2), encoding="utf-8")


def load_stock_cache() -> list[dict[str, str]]:
    if not STOCK_CACHE_FILE.exists():
        return []
    try:
        data = json.loads(STOCK_CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def parse_kind_stock_rows(html: str, market_label: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        return []
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    if not headers:
        return []

    rows: list[dict[str, str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) != len(headers):
            continue
        values = {headers[index]: cells[index].get_text(strip=True) for index in range(len(headers))}
        name = values.get("회사명", "").strip()
        symbol = values.get("종목코드", "").strip().zfill(6)
        if not name or not symbol:
            continue
        rows.append({"symbol": symbol, "name": name, "market": market_label})
    return rows


def fetch_kind_market_stocks(market_type: str, market_label: str) -> list[dict[str, str]]:
    url = "https://kind.krx.co.kr/corpgeneral/corpList.do"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://kind.krx.co.kr/"}
    payload = {"method": "download", "searchType": "13", "marketType": market_type}
    response = requests.post(url, data=payload, headers=headers, timeout=20)
    response.raise_for_status()
    return parse_kind_stock_rows(response.text, market_label)


def fetch_etf_stocks() -> list[dict[str, str]]:
    try:
        etf_list = fetch_etf_items()
        print(f"네이버 금융 API에서 {len(etf_list)}개 ETF 로드 완료")
        return etf_list
    except requests.RequestException as exc:
        print(f"네이버 금융 ETF API 호출 실패: {exc}")
        return []
    except Exception as exc:
        print(f"ETF 데이터 처리 중 오류: {exc}")
        return []


def build_stock_index() -> list[dict[str, str]]:
    try:
        stocks = (
            fetch_kind_market_stocks("stockMkt", "KOSPI")
            + fetch_kind_market_stocks("kosdaqMkt", "KOSDAQ")
            + fetch_etf_stocks()
        )
        if stocks:
            save_stock_cache(stocks)
            return stocks
    except requests.RequestException:
        pass

    cached = load_stock_cache()
    if cached:
        return cached

    return [
        {"symbol": "005930", "name": "삼성전자", "market": "KOSPI"},
        {"symbol": "000660", "name": "SK하이닉스", "market": "KOSPI"},
        {"symbol": "035420", "name": "NAVER", "market": "KOSPI"},
        {"symbol": "035720", "name": "카카오", "market": "KOSPI"},
    ]


def rebuild_stock_name_lookup(stocks: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    lookup: dict[str, list[dict[str, str]]] = {}
    for stock in stocks:
        normalized = stock["name"].strip().lower()
        lookup.setdefault(normalized, []).append(stock)
    return lookup


def initialize_stock_data() -> None:
    global STOCK_INDEX, STOCK_NAME_LOOKUP
    
    try:
        # DB에서 모든 활성 종목 가져오기
        from app.stock_repository import get_all_active_stocks
        db_stocks = get_all_active_stocks()
        
        if db_stocks:
            # DB 데이터를 기존 형식으로 변환
            STOCK_INDEX = [
                {
                    "symbol": stock["symbol"],
                    "name": stock["name"],
                    "market": stock["market"]
                }
                for stock in db_stocks
            ]
            print(f"DB에서 {len(STOCK_INDEX)}개 종목 로드 완료")
        else:
            # DB에 데이터가 없을 경우에만 API 호출 (최초 실행 시)
            print("DB에 종목 데이터가 없어 API에서 가져옵니다...")
            STOCK_INDEX = build_stock_index()
            print(f"API에서 {len(STOCK_INDEX)}개 종목 로드 완료")
            
    except Exception as e:
        print(f"DB 로드 실패: {e}")
        print("캐시 또는 API에서 데이터를 가져옵니다...")
        STOCK_INDEX = build_stock_index()
    
    STOCK_NAME_LOOKUP = rebuild_stock_name_lookup(STOCK_INDEX)


def issue_access_token() -> str:
    cached_token, cached_timestamp = load_token_cache()
    if cached_token and cached_timestamp and is_token_valid(cached_timestamp):
        TOKEN_CACHE["access_token"] = cached_token
        return cached_token

    validate_settings()
    url = f"{settings.kis_base_url}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": settings.kis_app_key,
        "appsecret": settings.kis_app_secret,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 요청에 실패했습니다: {exc}") from exc

    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail=f"KIS 토큰 발급 응답이 올바르지 않습니다: {data}")

    current_timestamp = datetime.datetime.now().timestamp()
    save_token_cache(access_token, current_timestamp)
    TOKEN_CACHE["access_token"] = access_token
    return access_token


def get_current_price(symbol: str) -> dict[str, Any]:
    access_token = issue_access_token()
    url = f"{settings.kis_base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.kis_app_key,
        "appsecret": settings.kis_app_secret,
        "tr_id": "FHKST01010100",
    }
    params = {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"KIS 현재가 조회 요청에 실패했습니다: {exc}") from exc

    data = response.json()
    output = data.get("output") or {}
    stock_name = output.get("hts_kor_isnm") or output.get("bstp_kor_isnm") or ""
    open_price = parse_int(output.get("stck_oprc"))
    current_price = parse_int(output.get("stck_prpr"))
    if current_price == 0:
        raise HTTPException(status_code=502, detail=f"KIS 현재가 응답이 올바르지 않습니다: {data}")
    return {"symbol": symbol, "name": stock_name, "current_price": current_price, "open_price": open_price}


def search_stocks_by_name(name: str) -> list[dict[str, str]]:
    from app.stock_repository import search_stocks_by_name as db_search_stocks_by_name
    
    keyword = name.strip()
    if not keyword:
        log_print(f"[ETF 검색] 빈 검색어: '{name}'")
        return []
    
    log_print(f"[ETF 검색] 검색 시작: '{keyword}'")
    
    try:
        # DB에서 검색
        log_print(f"[ETF 검색] DB에서 검색 중...")
        db_results = db_search_stocks_by_name(keyword, limit=20)
        log_print(f"[ETF 검색] DB 검색 결과: {len(db_results)}개")
        
        # API 형식으로 변환
        results = [
            {
                "symbol": item["symbol"],
                "name": item["name"],
                "market": item["market"]
            }
            for item in db_results
        ]
        
        # ETF만 필터링하여 로그 출력
        etf_count = sum(1 for item in results if item["market"] == "ETF")
        stock_count = sum(1 for item in results if item["market"] != "ETF")
        
        log_print(f"[ETF 검색] 최종 결과: 총 {len(results)}개 (ETF: {etf_count}개, 주식: {stock_count}개)")
        
        # 상위 5개 결과 출력
        if results:
            log_print(f"[ETF 검색] 상위 결과: {results[:5]}")
        
        return results
        
    except Exception as e:
        log_print(f"[ETF 검색] DB 검색 실패: {e}")
        log_print(f"[ETF 검색] 캐시 방식으로 fallback")
        
        # DB 실패 시 기존 캐시 방식으로 fallback
        keyword_lower = keyword.lower()
        partial_matches = [stock for stock in STOCK_INDEX if keyword_lower in stock["name"].lower()]
        if partial_matches:
            log_print(f"[ETF 검색] 캐시 부분 일치: {len(partial_matches)}개")
            return partial_matches[:20]
        
        exact_matches = STOCK_NAME_LOOKUP.get(keyword_lower, [])
        if exact_matches:
            log_print(f"[ETF 검색] 캐시 정확 일치: {len(exact_matches)}개")
            return exact_matches[:20]
        
        log_print(f"[ETF 검색] 결과 없음")
        return []


def parse_investor_rows(data: dict[str, Any], symbol: str) -> list[dict[str, Any]]:
    candidate_rows = data.get("output2") or data.get("output1") or data.get("output") or []
    if isinstance(candidate_rows, dict):
        candidate_rows = [candidate_rows]
    
    result: list[dict[str, Any]] = []
    for row in candidate_rows:
        if not isinstance(row, dict):
            continue
        date = row.get("stck_bsop_date") or row.get("bsop_date") or row.get("date") or row.get("trad_dt") or row.get("trade_date") or ""
        if not date:
            continue
        close_price = parse_int(row.get("stck_clpr") or row.get("stck_prpr") or 0)
        open_price = parse_int(row.get("stck_oprc") or 0)
        
        # 총 거래량 계산: 매수량 + 매도량
        personal_buy = parse_int(row.get("prsn_ntby_qty") or 0)
        foreign_buy = parse_int(row.get("frgn_ntby_qty") or 0)
        institution_buy = parse_int(row.get("orgn_ntby_qty") or 0)
        
        personal_sell = parse_int(row.get("prsn_seln_vol") or 0)
        foreign_sell = parse_int(row.get("frgn_seln_vol") or 0)
        institution_sell = parse_int(row.get("orgn_seln_vol") or 0)
        
        # 총 거래량 = 모든 매수량 + 모든 매도량
        total_volume = personal_buy + foreign_buy + institution_buy + personal_sell + foreign_sell + institution_sell
        
        result.append({
            "date": str(date),
            "symbol": symbol,
            "open_price": open_price,
            "close_price": close_price,
            "personal_net_buy": personal_buy,
            "foreign_net_buy": foreign_buy,
            "institution_net_buy": institution_buy,
            "volume": total_volume,
        })
    return result


def get_investor_trend(symbol: str) -> dict[str, Any]:
    access_token = issue_access_token()
    candidates = [
        {
            "url": f"{settings.kis_base_url}/uapi/domestic-stock/v1/quotations/inquire-investor",
            "tr_id": "FHKST01010900",
            "params": {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol},
        },
        {
            "url": f"{settings.kis_base_url}/uapi/domestic-stock/v1/quotations/foreign-institution-total",
            "tr_id": "FHPTJ04400000",
            "params": {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": symbol},
        },
    ]
    last_error: Any = None
    for candidate in candidates:
        headers = {
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {access_token}",
            "appkey": settings.kis_app_key,
            "appsecret": settings.kis_app_secret,
            "tr_id": candidate["tr_id"],
        }
        try:
            response = requests.get(candidate["url"], headers=headers, params=candidate["params"], timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        trends = parse_investor_rows(data, symbol)
        if trends:
            return {"symbol": symbol, "data": trends}
        last_error = data
    raise HTTPException(status_code=502, detail=f"KIS 투자자 동향 응답을 해석하지 못했습니다: {last_error}")


def get_etf_constituents(symbol: str) -> list[dict[str, Any]]:
    url = f"https://finance.naver.com/item/main.naver?code={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 다양한 테이블 클래스 시도
        possible_tables = [
            soup.find('table', class_='tb_type1 tb_type1_a'),
            soup.find('table', class_='tb_type1'),
            soup.find('table', {'summary': '편입종목'}),
            soup.find('table', {'summary': '구성종목'}),
        ]
        
        constituents_table = None
        for table in possible_tables:
            if table:
                constituents_table = table
                break
        
        if not constituents_table:
            # 디버깅: 페이지의 모든 테이블 출력
            tables = soup.find_all('table')
            print(f"[DEBUG] Found {len(tables)} tables on page")
            for i, table in enumerate(tables):
                print(f"[DEBUG] Table {i}: class={table.get('class')}, summary={table.get('summary')}")
                # 첫 몇 행 출력
                rows = table.find_all('tr')[:3]
                for j, row in enumerate(rows):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = [cell.text.strip() for cell in cells]
                    print(f"[DEBUG]   Row {j}: {cell_texts}")
            return []
        
        print(f"[DEBUG] Using table: class={constituents_table.get('class')}")
        
        # 데이터 행 파싱
        result: list[dict[str, Any]] = []
        rows = constituents_table.find_all('tr')[1:]  # 헤더 제외
        
        print(f"[DEBUG] Found {len(rows)} data rows")
        
        for row_idx, row in enumerate(rows):
            cells = row.find_all('td')
            if len(cells) >= 2:
                print(f"[DEBUG] Row {row_idx}: {len(cells)} cells")
                for i, cell in enumerate(cells):
                    print(f"[DEBUG]   Cell {i}: '{cell.text.strip()}' (link: {'yes' if cell.find('a') else 'no'})")
                
                # 첫 번째 셀에서 종목명과 종목코드 추출
                stock_name = ""
                stock_code = ""
                first_cell = cells[0]
                
                # 링크 태그가 있는 경우 링크 텍스트와 URL에서 정보 추출
                link_tag = first_cell.find('a')
                if link_tag and link_tag.get('href'):
                    href = link_tag.get('href', '')
                    stock_name = link_tag.text.strip()
                    print(f"[DEBUG] Found link: {href}, name: '{stock_name}'")
                    
                    # /item/main.naver?code=006800 형식에서 코드 추출
                    import re
                    code_match = re.search(r'code=(\d{6})', href)
                    if code_match:
                        stock_code = code_match.group(1)
                        print(f"[DEBUG] Extracted code from URL: {stock_code}")
                    else:
                        # 다른 형식의 링크에서도 시도
                        code_match = re.search(r'(\d{6})', href)
                        if code_match:
                            stock_code = code_match.group(1)
                            print(f"[DEBUG] Extracted code from link: {stock_code}")
                else:
                    # 링크가 없는 경우 텍스트에서 종목명과 종목코드 추출 시도
                    text = first_cell.text.strip()
                    print(f"[DEBUG] No link found, text: '{text}'")
                    
                    # 텍스트에 6자리 숫자가 있는지 확인
                    import re
                    code_match = re.search(r'(\d{6})', text)
                    if code_match:
                        stock_code = code_match.group(1)
                        stock_name = text.replace(stock_code, '').strip()
                        print(f"[DEBUG] Extracted code from text: {stock_code}, name: '{stock_name}'")
                    else:
                        stock_name = text
                
                # 두 번째 셀은 주가 정보이므로 무시
                # 세 번째 셀에서 비중 추출
                weight_text = cells[2].text.strip() if len(cells) > 2 else "0"
                print(f"[DEBUG] Weight text: '{weight_text}'")
                
                # 비중 파싱
                try:
                    weight_str = weight_text.replace('%', '').replace(',', '').strip()
                    weight = float(weight_str) if weight_str else 0.0
                    print(f"[DEBUG] Parsed weight: {weight}")
                except ValueError:
                    print(f"[DEBUG] Failed to parse weight: '{weight_text}'")
                    weight = 0.0
                
                # 종목명 정제: 숫자나 특수문자만 있는 경우 필터링
                if stock_name:
                    import re
                    if re.match(r'^[\d\s\-\.]+$', stock_name):
                        print(f"[DEBUG] Filtering numeric name: '{stock_name}'")
                        stock_name = ""
                    elif len(stock_name) < 2:
                        print(f"[DEBUG] Filtering too short name: '{stock_name}'")
                        stock_name = ""
                
                # 유효한 데이터만 추가
                if stock_name and weight > 0:
                    # 현재가와 전일대비 정보 추출 (4번째 셀: 현재가, 5번째 셀: 전일대비, 6번째 셀: 등락률)
                    current_price_text = cells[3].text.strip() if len(cells) > 3 else "0"
                    change_text = cells[4].text.strip() if len(cells) > 4 else "0"
                    change_rate_text = cells[5].text.strip() if len(cells) > 5 else "0"
                    
                    # 현재가 파싱
                    try:
                        current_price = int(current_price_text.replace(',', '').replace('원', '').strip())
                    except ValueError:
                        current_price = 0
                    
                    # 전일대비 파싱
                    try:
                        # "하향 900" 또는 "상향 500" 형식 처리
                        import re
                        change_match = re.search(r'([상하]향)?\s*([\d,]+)', change_text)
                        if change_match:
                            change_value = int(change_match.group(2).replace(',', ''))
                            if change_match.group(1) == '하향':
                                change = -change_value
                            elif change_match.group(1) == '상향':
                                change = change_value
                            else:
                                change = change_value
                        else:
                            change = int(change_text.replace(',', '').replace('+', '').replace('-', '').strip()) if change_text else 0
                    except ValueError:
                        change = 0
                    
                    # 등락률 파싱
                    try:
                        change_rate = float(change_rate_text.replace('%', '').replace('+', '').replace('-', '').strip())
                        if '하향' in change_text or '-' in change_rate_text:
                            change_rate = -abs(change_rate)
                        elif '상향' in change_text or '+' in change_rate_text:
                            change_rate = abs(change_rate)
                    except ValueError:
                        change_rate = 0.0
                    
                    result.append({
                        "stock_code": stock_code,
                        "stock_name": stock_name,
                        "weight": round(weight, 2),
                        "current_price": current_price,
                        "change": change,
                        "change_rate": round(change_rate, 2)
                    })
                    print(f"[DEBUG] Added: {stock_code} - {stock_name} - {weight}% - {current_price}원 - {change}원 ({change_rate}%)")
                else:
                    print(f"[DEBUG] Skipped: name='{stock_name}', weight={weight}")
        
        print(f"[DEBUG] Final result: {len(result)} items")
        return result
        
    except requests.RequestException as e:
        print(f"[DEBUG] Request error: {e}")
        return []
    except Exception as e:
        print(f"[DEBUG] Parsing error: {e}")
        return []


def get_investor_intraday(symbol: str) -> dict[str, Any]:
    access_token = issue_access_token()
    url = f"{settings.kis_base_url}/uapi/domestic-stock/v1/quotations/inquire-investor-time-itemchartprice"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": settings.kis_app_key,
        "appsecret": settings.kis_app_secret,
        "tr_id": "FHKST01010600",
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": symbol,
        "fid_input_hour_1": "090000",
        "fid_pw_data_incu_yn": "Y",
    }
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"KIS 시간대별 투자자 동향 요청에 실패했습니다: {exc}") from exc
    candidate_rows = data.get("output2") or data.get("output1") or data.get("output") or []
    if isinstance(candidate_rows, dict):
        candidate_rows = [candidate_rows]
    raw_rows: list[dict[str, Any]] = []
    for row in candidate_rows:
        if not isinstance(row, dict):
            continue
        time_val = row.get("stck_cntg_hour") or row.get("bsop_hour") or row.get("hour") or ""
        if not time_val:
            continue
        time_str = str(time_val).strip()
        formatted_time = f"{time_str[:2]}:{time_str[2:4]}" if len(time_str) >= 4 else time_str
        personal = parse_int(row.get("prsn_ntby_qty") or row.get("indi_ntby_qty") or 0)
        foreign = parse_int(row.get("frgn_ntby_qty") or row.get("frgnr_ntby_qty") or 0)
        institution = parse_int(row.get("orgn_ntby_qty") or row.get("org_ntby_qty") or 0)
        raw_rows.append({"time": formatted_time, "personal_net_buy": personal, "foreign_net_buy": foreign, "institution_net_buy": institution})
    if not raw_rows:
        raise HTTPException(status_code=502, detail=f"KIS 시간대별 투자자 동향 응답을 해석하지 못했습니다: {data}")
    raw_rows.reverse()
    cum_personal = 0
    cum_foreign = 0
    cum_institution = 0
    result: list[dict[str, Any]] = []
    for row in raw_rows:
        cum_personal += row["personal_net_buy"]
        cum_foreign += row["foreign_net_buy"]
        cum_institution += row["institution_net_buy"]
        result.append({
            "time": row["time"],
            "personal_net_buy": cum_personal,
            "foreign_net_buy": cum_foreign,
            "institution_net_buy": cum_institution,
        })
    return {"symbol": symbol, "data": result}


@app.on_event("startup")
def on_startup() -> None:
    initialize_stock_data()


@app.get("/")
def read_index() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.get("/api/token")
def read_access_token() -> dict[str, str]:
    return {"access_token": issue_access_token()}


@app.get("/api/quote")
def read_quote(symbol: str = Query(..., min_length=1, max_length=12)) -> dict[str, Any]:
    try:
        return get_current_price(symbol)
    except HTTPException:
        return {"symbol": symbol, "name": "데이터 없음", "current_price": 0, "open_price": 0}


@app.get("/api/stocks/search")
def read_stock_search(name: str = Query(..., min_length=1, max_length=50)) -> dict[str, Any]:
    log_print(f"[API] 종목 검색 요청: '{name}'")
    
    matches = search_stocks_by_name(name)
    
    if not matches:
        log_print(f"[API] 검색 결과 없음: '{name}'")
        raise HTTPException(status_code=404, detail="일치하는 종목명을 찾지 못했습니다.")
    
    result = {"query": name, "count": len(matches), "items": matches}
    log_print(f"[API] 검색 응답: {len(matches)}개 결과 반환")
    
    return result


@app.get("/api/investor-trend")
def read_investor_trend(symbol: str = Query(..., min_length=6, max_length=6)) -> dict[str, Any]:
    try:
        return get_investor_trend(symbol)
    except HTTPException:
        sample_data = []
        for i in range(10):
            date = (datetime.datetime.now() - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            sample_data.append({
                "date": date.replace("-", ""),
                "symbol": symbol,
                "open_price": 0,
                "close_price": 0,
                "personal_net_buy": 0,
                "foreign_net_buy": 0,
                "institution_net_buy": 0,
                "volume": 0,
            })
        return {"symbol": symbol, "data": sample_data}


@app.get("/api/investor-intraday")
def read_investor_intraday(symbol: str = Query(..., min_length=6, max_length=6)) -> dict[str, Any]:
    try:
        return get_investor_intraday(symbol)
    except HTTPException:
        import random

        mock_data = []
        hours = ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30"]
        cum_personal = 0
        cum_foreign = 0
        cum_institution = 0
        for t in hours:
            cum_personal += random.randint(-500, 800)
            cum_foreign += random.randint(-600, 700)
            cum_institution += random.randint(-400, 600)
            mock_data.append({
                "time": t,
                "personal_net_buy": cum_personal,
                "foreign_net_buy": cum_foreign,
                "institution_net_buy": cum_institution,
            })
        return {"symbol": symbol, "data": mock_data}


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    from app.database import test_connection
    from app.stock_repository import get_all_active_stocks
    
    db_status = "connected" if test_connection() else "disconnected"
    
    try:
        stock_count = len(get_all_active_stocks())
    except Exception:
        stock_count = 0
    
    return {
        "status": "healthy",
        "database": db_status,
        "stocks_in_db": stock_count,
        "timestamp": datetime.datetime.now().isoformat()
    }


@app.get("/api/etf-constituents")
def read_etf_constituents(symbol: str = Query(..., min_length=6, max_length=6)) -> dict[str, Any]:
    constituents = get_etf_constituents(symbol)
    result = {"symbol": symbol, "count": len(constituents), "data": constituents}
    
    return result
