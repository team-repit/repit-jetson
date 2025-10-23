import requests
import json
from typing import Dict, Optional, Any
import os

class RepitAPIClient:
    """Repit API 클라이언트"""
    
    def __init__(self, base_url: str = "https://api.repit.life", access_token: Optional[str] = None):
        """
        API 클라이언트 초기화
        
        Args:
            base_url (str): API 서버 기본 URL
            access_token (str, optional): 액세스 토큰
        """
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.session = requests.Session()
        
        # 기본 헤더 설정
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # 액세스 토큰이 있으면 Authorization 헤더 설정
        if self.access_token:
            self.set_access_token(access_token)
    
    def set_access_token(self, access_token: str):
        """액세스 토큰 설정"""
        self.access_token = access_token
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}'
        })
    
    def health_check(self) -> Dict[str, Any]:
        """헬스체크 API 호출"""
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "API 서버가 정상적으로 작동 중입니다.",
                    "data": response.text
                }
            else:
                return {
                    "success": False,
                    "message": f"헬스체크 실패: HTTP {response.status_code}",
                    "data": None
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"헬스체크 중 오류 발생: {str(e)}",
                "data": None
            }
    
    def create_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        운동 기록 생성
        
        Args:
            record_data (dict): 운동 기록 데이터
                - pose_type (str): 운동 타입 (SQUAT, LUNGE, PLANK, PUSH_UP)
                - duration (int): 운동 지속 시간 (초)
                - reps (int): 운동 횟수
                - total_score (str): 전체 점수 (A~F)
                - video_path (str, optional): 영상 파일 경로
                - analysis_text (str, optional): 분석 결과 텍스트
                - score_details (list, optional): 부위별 점수 배열
        
        Returns:
            dict: API 응답 결과
        """
        if not self.access_token:
            return {
                "success": False,
                "message": "액세스 토큰이 설정되지 않았습니다.",
                "data": None
            }
        
        try:
            # API 엔드포인트
            url = f"{self.base_url}/api/record"
            
            # 요청 데이터 검증
            required_fields = ['pose_type', 'duration', 'reps', 'total_score']
            for field in required_fields:
                if field not in record_data:
                    return {
                        "success": False,
                        "message": f"필수 필드 '{field}'가 누락되었습니다.",
                        "data": None
                    }
            
            # API 요청
            response = self.session.post(url, json=record_data)
            
            if response.status_code == 201:
                response_data = response.json()
                return {
                    "success": True,
                    "message": "운동 기록이 성공적으로 저장되었습니다.",
                    "data": response_data
                }
            else:
                try:
                    error_data = response.json()
                    return {
                        "success": False,
                        "message": f"운동 기록 저장 실패: {error_data.get('message', '알 수 없는 오류')}",
                        "data": error_data
                    }
                except:
                    return {
                        "success": False,
                        "message": f"운동 기록 저장 실패: HTTP {response.status_code}",
                        "data": None
                    }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"API 요청 중 오류 발생: {str(e)}",
                "data": None
            }
    
    def get_record(self, record_id: int) -> Dict[str, Any]:
        """
        운동 기록 상세 조회
        
        Args:
            record_id (int): 레코드 ID
        
        Returns:
            dict: API 응답 결과
        """
        if not self.access_token:
            return {
                "success": False,
                "message": "액세스 토큰이 설정되지 않았습니다.",
                "data": None
            }
        
        try:
            url = f"{self.base_url}/api/record/{record_id}"
            response = self.session.get(url)
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True,
                    "message": "운동 기록을 성공적으로 조회했습니다.",
                    "data": response_data
                }
            else:
                try:
                    error_data = response.json()
                    return {
                        "success": False,
                        "message": f"운동 기록 조회 실패: {error_data.get('message', '알 수 없는 오류')}",
                        "data": error_data
                    }
                except:
                    return {
                        "success": False,
                        "message": f"운동 기록 조회 실패: HTTP {response.status_code}",
                        "data": None
                    }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"API 요청 중 오류 발생: {str(e)}",
                "data": None
            }
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        액세스 토큰 갱신
        
        Args:
            refresh_token (str): 리프레시 토큰
        
        Returns:
            dict: API 응답 결과
        """
        try:
            url = f"{self.base_url}/api/auth/refresh"
            payload = {"refreshToken": refresh_token}
            
            # 토큰 갱신 시에는 Authorization 헤더를 제거
            headers = self.session.headers.copy()
            if 'Authorization' in headers:
                del headers['Authorization']
            
            response = requests.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('is_success') and response_data.get('result', {}).get('accessToken'):
                    new_access_token = response_data['result']['accessToken']
                    # "Bearer " 접두사 제거
                    if new_access_token.startswith('Bearer '):
                        new_access_token = new_access_token[7:]
                    self.set_access_token(new_access_token)
                    
                    return {
                        "success": True,
                        "message": "토큰이 성공적으로 갱신되었습니다.",
                        "data": response_data
                    }
                else:
                    return {
                        "success": False,
                        "message": "토큰 갱신 응답 형식이 올바르지 않습니다.",
                        "data": response_data
                    }
            else:
                try:
                    error_data = response.json()
                    return {
                        "success": False,
                        "message": f"토큰 갱신 실패: {error_data.get('message', '알 수 없는 오류')}",
                        "data": error_data
                    }
                except:
                    return {
                        "success": False,
                        "message": f"토큰 갱신 실패: HTTP {response.status_code}",
                        "data": None
                    }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"토큰 갱신 중 오류 발생: {str(e)}",
                "data": None
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """API 연결 테스트"""
        print("API 연결 테스트를 시작합니다...")
        
        # 1. 헬스체크
        print("1. 헬스체크 테스트...")
        health_result = self.health_check()
        if not health_result["success"]:
            return health_result
        
        print(f"   ✓ 헬스체크 성공: {health_result['message']}")
        
        # 2. 액세스 토큰 확인
        if not self.access_token:
            return {
                "success": False,
                "message": "액세스 토큰이 설정되지 않았습니다. 토큰을 설정한 후 다시 시도해주세요.",
                "data": None
            }
        
        print("2. 액세스 토큰 확인...")
        print(f"   ✓ 액세스 토큰 설정됨: {self.access_token[:10]}...")
        
        return {
            "success": True,
            "message": "API 연결 테스트가 성공적으로 완료되었습니다.",
            "data": {
                "base_url": self.base_url,
                "token_set": bool(self.access_token)
            }
        }

def create_api_client_from_token_file(token_file_path: str = ".token_cache") -> Optional[RepitAPIClient]:
    """
    토큰 파일에서 API 클라이언트 생성
    
    Args:
        token_file_path (str): 토큰 파일 경로
    
    Returns:
        RepitAPIClient or None: API 클라이언트 또는 None
    """
    try:
        if os.path.exists(token_file_path):
            with open(token_file_path, 'r', encoding='utf-8') as f:
                token_data = json.load(f)
            
            access_token = token_data.get('access_token')
            if access_token:
                client = RepitAPIClient(access_token=access_token)
                print(f"토큰 파일에서 API 클라이언트를 생성했습니다.")
                return client
            else:
                print("토큰 파일에 액세스 토큰이 없습니다.")
                return None
        else:
            print(f"토큰 파일을 찾을 수 없습니다: {token_file_path}")
            return None
    
    except Exception as e:
        print(f"토큰 파일 읽기 중 오류 발생: {str(e)}")
        return None

def save_token_to_file(access_token: str, refresh_token: str = None, token_file_path: str = ".token_cache"):
    """
    토큰을 파일에 저장
    
    Args:
        access_token (str): 액세스 토큰
        refresh_token (str, optional): 리프레시 토큰
        token_file_path (str): 토큰 파일 경로
    """
    try:
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token
        }
        
        with open(token_file_path, 'w', encoding='utf-8') as f:
            json.dump(token_data, f, ensure_ascii=False, indent=2)
        
        print(f"토큰이 파일에 저장되었습니다: {token_file_path}")
    
    except Exception as e:
        print(f"토큰 저장 중 오류 발생: {str(e)}")

# 사용 예시
if __name__ == "__main__":
    # API 클라이언트 생성 및 테스트
    client = RepitAPIClient()
    
    # 연결 테스트
    result = client.test_connection()
    print(f"연결 테스트 결과: {result}")
    
    # 액세스 토큰 설정 예시
    # client.set_access_token("your-access-token-here")
    
    # 운동 기록 생성 예시
    # record_data = {
    #     "pose_type": "SQUAT",
    #     "duration": 120,
    #     "reps": 10,
    #     "total_score": "B",
    #     "video_path": None,
    #     "analysis_text": "스쿼트 분석 결과...",
    #     "score_details": [
    #         {"body_part": "허리", "detail_score": "A"},
    #         {"body_part": "무릎", "detail_score": "B"}
    #     ]
    # }
    # result = client.create_record(record_data)
    # print(f"기록 생성 결과: {result}")