import requests
from bs4 import BeautifulSoup

def test_naver_etf_constituents_fixed(symbol):
    print(f"네이버 금융 ETF 구성종목 테스트 (수정): {symbol}")
    
    url = f"https://finance.naver.com/item/main.naver?code={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        print(f"요청: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"응답 상태: {response.status_code}")
        
        # HTML 파싱
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 구성종목 테이블 찾기 (클래스: tb_type1 tb_type1_a)
        constituents_table = soup.find('table', class_='tb_type1 tb_type1_a')
        
        if not constituents_table:
            print("구성종목 테이블을 찾지 못함")
            return []
        
        print("구성종목 테이블 찾음!")
        
        # 헤더 확인
        headers = constituents_table.find_all('th')
        header_texts = [th.get_text(strip=True) for th in headers]
        print(f"헤더: {header_texts}")
        
        # 데이터 행 파싱
        result = []
        rows = constituents_table.find_all('tr')
        print(f"전체 행 개수: {len(rows)}")
        
        for i, row in enumerate(rows):
            # 헤더 행 건너뛰기
            if row.find('th'):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 3:  # 구성종목, 주식수, 구성비중 최소 3개 필요
                continue
            
            # 종목명 (첫 번째 td)
            stock_name = cells[0].get_text(strip=True)
            
            # 구성비중 (%) (세 번째 td)
            weight_cell = cells[2]
            weight_text = weight_cell.get_text(strip=True)
            
            # 비중 파싱
            try:
                weight_str = weight_text.replace('%', '').replace(',', '').strip()
                weight = float(weight_str) if weight_str else 0.0
            except ValueError:
                print(f"비중 파싱 실패: {weight_text}")
                continue
            
            if stock_name and weight > 0:
                result.append({
                    "stock_code": "",
                    "stock_name": stock_name,
                    "weight": round(weight, 2)
                })
                print(f"  {len(result)}. {stock_name}: {weight}%")
        
        print(f"최종 결과: {len(result)}개 종목")
        return result
        
    except Exception as e:
        print(f"예외: {e}")
        return []

if __name__ == "__main__":
    # KODEX 200 (069500) 테스트
    test_naver_etf_constituents_fixed("069500")
