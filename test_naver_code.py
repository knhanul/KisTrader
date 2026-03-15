import requests
from bs4 import BeautifulSoup
import re

def test_naver_etf_with_code(symbol):
    print(f"네이버 금융 ETF 구성종목 테스트 (종목코드 포함): {symbol}")
    
    url = f"https://finance.naver.com/item/main.naver?code={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        constituents_table = soup.find('table', class_='tb_type1 tb_type1_a')
        
        if not constituents_table:
            print("구성종목 테이블을 찾지 못함")
            return []
        
        result = []
        rows = constituents_table.find_all('tr')
        
        for row in rows:
            if row.find('th'):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 3:
                continue
            
            # 종목명 (첫 번째 td) - 종목코드 추출 시도
            stock_name_cell = cells[0]
            stock_name = stock_name_cell.get_text(strip=True)
            
            # 종목명 링크에서 종목코드 추출 시도
            stock_code = ""
            link = stock_name_cell.find('a')
            if link and link.get('href'):
                href = link.get('href')
                # 네이버 금융 링크에서 종목코드 추출: /item/main.naver?code=005930
                code_match = re.search(r'code=([0-9]+)', href)
                if code_match:
                    stock_code = code_match.group(1)
            
            # 구성비중 (%) (세 번째 td)
            weight_cell = cells[2]
            weight_text = weight_cell.get_text(strip=True)
            
            try:
                weight_str = weight_text.replace('%', '').replace(',', '').strip()
                weight = float(weight_str) if weight_str else 0.0
            except ValueError:
                continue
            
            if stock_name and weight > 0:
                result.append({
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "weight": round(weight, 2)
                })
                print(f"  {len(result)}. {stock_name} ({stock_code}): {weight}%")
        
        print(f"최종 결과: {len(result)}개 종목")
        return result
        
    except Exception as e:
        print(f"예외: {e}")
        return []

if __name__ == "__main__":
    test_naver_etf_with_code("069500")
