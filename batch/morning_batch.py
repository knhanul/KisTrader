import sys
from datetime import date, datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.main import fetch_etf_stocks, fetch_kind_market_stocks
from app.stock_repository import upsert_stock_master, insert_listing_history
from app.batch_repository import insert_batch_job_log, update_batch_job_log
from batch.batch_utils import now_text


def run_morning_batch():
    """아침 배치 실행: 종목 마스터 동기화"""
    job_name = "morning_master_sync"
    run_type = "SCHEDULED"
    started_at = datetime.now()
    
    # 배치 로그 시작
    log_id = insert_batch_job_log(job_name, run_type, started_at, "RUNNING", "종목 마스터 동기화 시작")
    
    total_count = 0
    success_count = 0
    fail_count = 0
    
    try:
        print(f"[{now_text()}] 아침 배치 시작: 종목 마스터 동기화")
        
        # 오늘 날짜
        today = date.today()
        
        # KOSPI 종목 수집
        print("[{now_text()}] KOSPI 종목 수집 중...")
        kospi_stocks = fetch_kind_market_stocks("stockMkt", "KOSPI")
        print(f"[{now_text()}] KOSPI 종목 {len(kospi_stocks)}개 수집 완료")
        
        # KOSDAQ 종목 수집
        print("[{now_text()}] KOSDAQ 종목 수집 중...")
        kosdaq_stocks = fetch_kind_market_stocks("kosdaqMkt", "KOSDAQ")
        print(f"[{now_text()}] KOSDAQ 종목 {len(kosdaq_stocks)}개 수집 완료")
        
        # ETF 종목 수집
        print("[{now_text()}] ETF 종목 수집 중...")
        etf_stocks = fetch_etf_stocks()
        print(f"[{now_text()}] ETF 종목 {len(etf_stocks)}개 수집 완료")
        
        # 모든 종목 합치기
        all_stocks = kospi_stocks + kosdaq_stocks + etf_stocks
        total_count = len(all_stocks)
        
        # DB에 저장
        print(f"[{now_text()}] DB 저장 시작: 총 {total_count}개 종목")
        
        for stock in all_stocks:
            try:
                symbol = stock["symbol"]
                name = stock["name"]
                market = stock["market"]
                instrument_type = "ETF" if market == "ETF" else "STOCK"
                
                # 종목 마스터 upsert
                upsert_stock_master(symbol, name, market, instrument_type, True, "NAVER")
                
                # 상장 이력 추가
                insert_listing_history(symbol, name, market, instrument_type, True, today, "NAVER")
                
                success_count += 1
                
                # 진행상황 출력 (100개마다)
                if success_count % 100 == 0:
                    print(f"[{now_text()}] {success_count}/{total_count} 처리 완료")
                    
            except Exception as e:
                print(f"[{now_text()}] 종목 저장 실패: {stock.get('symbol', 'unknown')} - {e}")
                fail_count += 1
        
        # 배치 로그 완료
        finished_at = datetime.now()
        message = f"종목 마스터 동기화 완료: 총 {total_count}개, 성공 {success_count}개, 실패 {fail_count}개"
        
        update_batch_job_log(
            log_id, finished_at, "SUCCESS", message,
            total_count, success_count, fail_count
        )
        
        print(f"[{now_text()}] {message}")
        return True
        
    except Exception as e:
        # 배치 로그 실패
        finished_at = datetime.now()
        error_message = f"종목 마스터 동기화 실패: {str(e)}"
        
        update_batch_job_log(log_id, finished_at, "FAILED", error_message, total_count, success_count, fail_count)
        
        print(f"[{now_text()}] {error_message}")
        return False


if __name__ == "__main__":
    success = run_morning_batch()
    sys.exit(0 if success else 1)
