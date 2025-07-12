"""
키움증권 API Mock 클라이언트
"""
import asyncio
import json
import logging
import random
from typing import Any, AsyncGenerator, Dict, List, Optional

from .kiwoom_api_client import APIError, KiwoomAPIClient

logger = logging.getLogger(__name__)


class MockKiwoomAPIClient(KiwoomAPIClient):
    """키움증권 API Mock 클라이언트 (테스트용)"""
    
    def __init__(self, **kwargs):
        """
        Mock 클라이언트 초기화
        
        Args:
            **kwargs: KiwoomAPIClient와 동일한 파라미터
        """
        # 부모 클래스 초기화를 건너뛰고 기본 속성만 설정
        self.base_url = kwargs.get('base_url', 'https://mock.api.com')
        self.rate_limit = kwargs.get('rate_limit', 10)
        self.cache_ttl = kwargs.get('cache_ttl', 300)
        self.max_retries = kwargs.get('max_retries', 3)
        self.timeout = kwargs.get('timeout', 30)
        
        # Mock 데이터 저장소
        self._mock_data = self._load_mock_data()
        self._request_count = 0
        self._error_simulation = False
        
        logger.info("MockKiwoomAPIClient initialized")
    
    def _load_mock_data(self) -> Dict[str, Any]:
        """Mock 데이터 로드"""
        return {
            # 주식 현재가 조회 (ka10001)
            "ka10001": {
                "rt_cd": "0",
                "msg_cd": "000000",
                "msg1": "SUCCESS",
                "output": {
                    "hts_kor_isnm": "삼성전자",
                    "stck_prpr": str(random.randint(65000, 75000)),  # 현재가
                    "prdy_vrss": str(random.randint(-2000, 2000)),   # 전일대비
                    "prdy_vrss_sign": str(random.choice([1, 2, 3, 4, 5])),  # 부호
                    "prdy_ctrt": f"{random.uniform(-3.0, 3.0):.2f}",  # 전일대비율
                    "stck_oprc": str(random.randint(65000, 75000)),   # 시가
                    "stck_hgpr": str(random.randint(70000, 80000)),   # 고가
                    "stck_lwpr": str(random.randint(60000, 70000)),   # 저가
                    "acml_vol": str(random.randint(1000000, 10000000)),  # 누적거래량
                    "acml_tr_pbmn": str(random.randint(100000000, 1000000000))  # 누적거래대금
                }
            },
            
            # 일봉차트 조회 (ka10002)
            "ka10002": {
                "rt_cd": "0",
                "msg_cd": "000000",
                "msg1": "SUCCESS",
                "output": [
                    {
                        "stck_bsop_date": "20231201",
                        "stck_clpr": str(random.randint(65000, 75000)),
                        "stck_oprc": str(random.randint(65000, 75000)),
                        "stck_hgpr": str(random.randint(70000, 80000)),
                        "stck_lwpr": str(random.randint(60000, 70000)),
                        "acml_vol": str(random.randint(1000000, 10000000))
                    } for _ in range(30)  # 30일 데이터
                ],
                "ctx_area_fk100": "",
                "ctx_area_nk100": ""
            },
            
            # 주문 (kt10001)
            "kt10001": {
                "rt_cd": "0",
                "msg_cd": "000000",
                "msg1": "SUCCESS",
                "output": {
                    "odno": str(random.randint(100000, 999999)),  # 주문번호
                    "ord_tmd": "153000"  # 주문시각
                }
            },
            
            # 잔고조회 (ka00001)
            "ka00001": {
                "rt_cd": "0",
                "msg_cd": "000000",
                "msg1": "SUCCESS",
                "output": [
                    {
                        "pdno": "005930",  # 종목코드
                        "prdt_name": "삼성전자",
                        "hldg_qty": str(random.randint(10, 100)),  # 보유수량
                        "pchs_avg_pric": str(random.randint(65000, 75000)),  # 매입평균가
                        "evlu_amt": str(random.randint(1000000, 10000000)),  # 평가금액
                        "evlu_pfls_amt": str(random.randint(-500000, 500000))  # 평가손익
                    }
                ]
            }
        }
    
    async def initialize(self):
        """Mock 클라이언트 초기화 (빠른 초기화)"""
        await asyncio.sleep(0.001)  # 최소 대기
        logger.info("MockKiwoomAPIClient initialized successfully")
    
    async def close(self):
        """Mock 클라이언트 종료"""
        await asyncio.sleep(0.001)  # 최소 대기
        logger.info("MockKiwoomAPIClient closed")
    
    async def request(
        self,
        api_id: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Mock API 요청
        
        Args:
            api_id: API ID
            params: 요청 파라미터
            headers: 요청 헤더
            use_cache: 캐시 사용 여부
            
        Returns:
            Mock 응답 데이터
        """
        self._request_count += 1
        
        # 에러 시뮬레이션
        if self._error_simulation and random.random() < 0.1:  # 10% 확률로 에러
            raise APIError("Simulated API error", "999999")
        
        # 응답 지연 시뮬레이션
        await asyncio.sleep(random.uniform(0.01, 0.1))
        
        # Mock 데이터 반환
        if api_id in self._mock_data:
            mock_response = self._mock_data[api_id].copy()
            
            # 동적 데이터 생성 (현재가 등)
            if api_id == "ka10001" and "output" in mock_response:
                mock_response["output"]["stck_prpr"] = str(random.randint(65000, 75000))
                mock_response["output"]["prdy_vrss"] = str(random.randint(-2000, 2000))
            
            logger.debug(f"Mock API request for {api_id} completed")
            return mock_response
        else:
            # 알 수 없는 API ID
            raise APIError(f"Unknown API ID: {api_id}", "000404")
    
    async def continuous_request(
        self,
        api_id: str,
        params: Dict[str, Any],
        max_pages: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Mock 연속조회"""
        pages = min(random.randint(1, 5), max_pages)  # 1-5 페이지 랜덤
        
        for page in range(pages):
            response = await self.request(api_id, params)
            
            # 마지막 페이지가 아니면 다음 키 설정
            if page < pages - 1:
                response["ctx_area_fk100"] = f"next_key_{page + 1}"
                response["ctx_area_nk100"] = f"next_key_{page + 1}"
            else:
                response["ctx_area_fk100"] = ""
                response["ctx_area_nk100"] = ""
            
            yield response
    
    async def batch_request(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """Mock 배치 요청"""
        results = []
        
        for req in requests:
            try:
                response = await self.request(
                    api_id=req["api_id"],
                    params=req["params"],
                    headers=req.get("headers"),
                    use_cache=req.get("use_cache", False)
                )
                results.append(response)
            except Exception as e:
                results.append({
                    "rt_cd": "1",
                    "msg1": f"Request failed: {e}",
                    "error": True
                })
        
        return results
    
    async def websocket_connect(self):
        """Mock WebSocket 연결"""
        return MockWebSocket()
    
    async def health_check(self) -> bool:
        """Mock 헬스 체크"""
        await asyncio.sleep(0.01)
        return not self._error_simulation
    
    def get_stats(self) -> Dict[str, Any]:
        """Mock 클라이언트 통계"""
        return {
            "total_requests": self._request_count,
            "error_simulation": self._error_simulation,
            "available_apis": list(self._mock_data.keys()),
            "client_type": "mock"
        }
    
    def set_error_simulation(self, enabled: bool):
        """에러 시뮬레이션 설정"""
        self._error_simulation = enabled
        logger.info(f"Error simulation {'enabled' if enabled else 'disabled'}")
    
    def add_mock_data(self, api_id: str, response_data: Dict[str, Any]):
        """Mock 데이터 추가"""
        self._mock_data[api_id] = response_data
        logger.info(f"Mock data added for API {api_id}")
    
    def get_request_count(self) -> int:
        """요청 횟수 조회"""
        return self._request_count
    
    def reset_stats(self):
        """통계 리셋"""
        self._request_count = 0
        logger.info("Mock client stats reset")


class MockWebSocket:
    """Mock WebSocket 클래스"""
    
    def __init__(self):
        self._messages = []
    
    async def send_str(self, data: str):
        """메시지 전송 시뮬레이션"""
        await asyncio.sleep(0.001)
        self._messages.append(data)
    
    async def receive_str(self) -> str:
        """메시지 수신 시뮬레이션"""
        await asyncio.sleep(0.01)
        
        # 간단한 Echo 응답
        mock_response = {
            "rt_cd": "0",
            "msg1": "SUCCESS",
            "timestamp": "20231201153000"
        }
        return json.dumps(mock_response)
    
    async def close(self):
        """연결 종료 시뮬레이션"""
        await asyncio.sleep(0.001)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()