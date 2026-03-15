from app.main import STOCK_INDEX, get_investor_intraday, initialize_stock_data
from batch.batch_utils import now_text


if __name__ == "__main__":
    initialize_stock_data()
    success_count = 0
    for stock in STOCK_INDEX[:10]:
        try:
            get_investor_intraday(stock["symbol"])
            success_count += 1
        except Exception:
            continue
    print(f"[{now_text()}] evening batch completed: {success_count} symbols")
