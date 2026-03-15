import requests
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

def test_kis_api():
    print("KIS API 테스트")
    
    # 설정 확인
    app_key = os.getenv("KIS_APP_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    base_url = os.getenv("KIS_BASE_URL")
    
    print(f"APP_KEY: {app_key[:10]}..." if app_key else "APP_KEY: None")
    print(f"APP_SECRET: {app_secret[:10]}..." if app_secret else "APP_SECRET: None")
    print(f"BASE_URL: {base_url}")
    
    if not all([app_key, app_secret, base_url]):
        print("환경변수 설정 필요")
        return
    
    # 토큰 발급
    token_url = f"{base_url}/oauth2/tokenP"
    token_headers = {
        "content-type": "application/json",
    }
    token_data = {
        "grant_type": "client_credentials",
        "appkey": app_key,
        "appsecret": app_secret,
    }
    
    try:
        print("\n1. 토큰 발급 시도...")
        token_response = requests.post(token_url, headers=token_headers, json=token_data)
        print(f"토큰 응답 상태: {token_response.status_code}")
        
        if token_response.status_code == 200:
            token_data = token_response.json()
            access_token = token_data.get("access_token")
            print(f"토큰 발급 성공: {access_token[:20]}...")
            
            # ETF 구성종목 조회
            print("\n2. ETF 구성종목 조회 시도...")
            etf_url = f"{base_url}/uapi/etfetn/fund-finder/fund-detail"
            etf_headers = {
                "content-type": "application/json; charset=utf-8",
                "authorization": f"Bearer {access_token}",
                "appkey": app_key,
                "appsecret": app_secret,
                "tr_id": "FHPST02400000",
            }
            etf_params = {"fid_input_iscd": "069500"}
            
            etf_response = requests.get(etf_url, headers=etf_headers, params=etf_params)
            print(f"ETF 응답 상태: {etf_response.status_code}")
            
            if etf_response.status_code == 200:
                etf_data = etf_response.json()
                print(f"ETF 응답 키: {list(etf_data.keys())}")
                print(f"rt_cd: {etf_data.get('rt_cd')}")
                print(f"msg_cd: {etf_data.get('msg_cd')}")
                print(f"msg1: {etf_data.get('msg1')}")
                
                output1 = etf_data.get("output1", [])
                print(f"output1 개수: {len(output1)}")
                
                if output1:
                    print(f"첫 번째 구성종목: {output1[0]}")
            else:
                print(f"ETF 응답 실패: {etf_response.text}")
        else:
            print(f"토큰 발급 실패: {token_response.text}")
            
    except Exception as e:
        print(f"예외: {e}")

if __name__ == "__main__":
    test_kis_api()
