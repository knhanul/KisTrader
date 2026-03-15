import requests
from bs4 import BeautifulSoup

def debug_naver_page(symbol):
    print(f"네이버 금융 페이지 디버깅: {symbol}")
    
    url = f"https://finance.naver.com/item/main.naver?code={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 모든 테이블의 내용 확인
        all_tables = soup.find_all('table')
        print(f"전체 테이블 개수: {len(all_tables)}")
        
        for i, table in enumerate(all_tables):
            print(f"\n--- 테이블 {i+1} ---")
            
            # 테이블 클래스 확인
            if table.get('class'):
                print(f"클래스: {table.get('class')}")
            
            # 테이블 헤더 확인
            headers = table.find_all('th')
            if headers:
                header_texts = [th.get_text(strip=True) for th in headers]
                print(f"헤더: {header_texts}")
            
            # 테이블 내용 일부 확인
            table_text = table.get_text(strip=True)
            if len(table_text) > 200:
                table_text = table_text[:200] + "..."
            print(f"내용: {table_text}")
            
            # '구성종목'이나 '종목명'이 있는지 확인
            if '구성종목' in table_text or '종목명' in table_text:
                print(">>> 관련 테이블 발견!")
        
        # '구성종목' 텍스트가 있는 모든 요소 확인
        print(f"\n--- '구성종목' 텍스트 검색 ---")
        constituents_elements = soup.find_all(text=lambda text: text and '구성종목' in text)
        for elem in constituents_elements:
            parent = elem.parent
            print(f"부모 태그: {parent.name if parent else 'None'}")
            print(f"텍스트: {elem.strip()}")
            if parent:
                print(f"부모 클래스: {parent.get('class')}")
                print(f"부모 ID: {parent.get('id')}")
        
    except Exception as e:
        print(f"예외: {e}")

if __name__ == "__main__":
    debug_naver_page("069500")
