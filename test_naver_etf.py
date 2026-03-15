import requests
from bs4 import BeautifulSoup

def test_naver_etf_constituents(symbol):
    print(f"네이버 금융 ETF 구성종목 테스트: {symbol}")
    
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
        
        # 페이지 제목 확인 (ETF인지 확인)
        title = soup.find('title')
        if title:
            print(f"페이지 제목: {title.get_text()}")
        
        # '구성종목' 테이블 찾기
        constituents_table = None
        
        # 방법 1: class="tb_type1 tb_num tb_type1_if" 인 테이블 찾기
        tables = soup.find_all('table', class_='tb_type1 tb_num tb_type1_if')
        print(f"tb_type1 테이블 개수: {len(tables)}")
        
        for i, table in enumerate(tables):
            first_th = table.find('th')
            if first_th:
                th_text = first_th.get_text(strip=True)
                print(f"테이블 {i+1} 첫 번째 th: '{th_text}'")
                if '종목명' in th_text:
                    constituents_table = table
                    print("구성종목 테이블 찾음!")
                    break
        
        # 방법 2: '구성종목' 텍스트가 포함된 테이블 찾기
        if not constituents_table:
            print("방법 1로 찾지 못함, 방법 2 시도...")
            all_tables = soup.find_all('table')
            print(f"전체 테이블 개수: {len(all_tables)}")
            
            for i, table in enumerate(all_tables):
                table_text = table.get_text(strip=True)
                if '구성종목' in table_text and '종목명' in table_text:
                    first_th = table.find('th')
                    if first_th and '종목명' in first_th.get_text(strip=True):
                        constituents_table = table
                        print(f"테이블 {i+1}에서 구성종목 찾음!")
                        break
        
        if not constituents_table:
            print("구성종목 테이블을 찾지 못함")
            return []
        
        # 데이터 행 파싱
        result = []
        rows = constituents_table.find_all('tr')
        print(f"전체 행 개수: {len(rows)}")
        
        for i, row in enumerate(rows):
            # 헤더 행 건너뛰기
            if row.find('th'):
                continue
            
            cells = row.find_all('td')
            if len(cells) < 2:
                continue
            
            # 종목명 (첫 번째 td)
            stock_name = cells[0].get_text(strip=True)
            
            # 비중 (%) 찾기
            weight_cell = None
            for j, cell in enumerate(cells):
                cell_text = cell.get_text(strip=True)
                if '%' in cell_text and ('비중' in cell_text or j == 1):
                    weight_cell = cell
                    break
            
            if not weight_cell:
                continue
            
            # 비중 파싱
            weight_text = weight_cell.get_text(strip=True)
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
    test_naver_etf_constituents("069500")
    
    print("\n" + "="*50 + "\n")
    
    # TIGER 200 (102110) 테스트
    test_naver_etf_constituents("102110")
