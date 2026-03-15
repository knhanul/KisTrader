import requests
import sys

# ETF 구성종목 테스트
def test_etf_constituents(symbol):
    print(f"ETF 구성종목 테스트: {symbol}")
    
    try:
        response = requests.get(f'http://localhost:8000/api/etf-constituents?symbol={symbol}')
        print(f"상태 코드: {response.status_code}")
        data = response.json()
        print(f"응답: {data}")
        
        if data.get('error'):
            print(f"오류: {data['error']}")
        else:
            print(f"성공: {data['count']}개 구성종목")
            
    except Exception as e:
        print(f"예외: {e}")

if __name__ == "__main__":
    # KODEX 200 (069500) 테스트
    test_etf_constituents("069500")
    
    # 다른 ETF도 테스트
    test_etf_constituents("102780")  # KODEX 삼성그룹
