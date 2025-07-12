"""
키움증권 API 클라이언트
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

import aiohttp
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..auth.authentication_service import AuthenticationService
from ..auth.credential_manager import Credentials

logger = logging.getLogger(__name__)


class APIError(Exception):
    """API 관련 에러"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code


class RateLimitError(APIError):
    """Rate Limit 관련 에러"""
    pass


class CacheError(Exception):
    """캐시 관련 에러"""
    pass


class KiwoomAPIClient:
    """키움증권 REST API 클라이언트"""
    
    def __init__(
        self,
        base_url: str,
        credentials: Credentials,
        rate_limit: int = 10,  # requests per second
        cache_ttl: int = 300,  # seconds
        max_retries: int = 3,
        timeout: int = 30
    ):
        """
        초기화
        
        Args:
            base_url: API 기본 URL
            credentials: 인증 자격증명
            rate_limit: 초당 요청 제한 (req/sec)
            cache_ttl: 캐시 유효시간 (초)
            max_retries: 최대 재시도 횟수
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url.rstrip('/')
        self.credentials = credentials
        self.rate_limit = rate_limit
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Rate limiting을 위한 요청 시간 추적
        self._request_times: List[float] = []
        self._rate_limit_lock = asyncio.Lock()
        
        # 캐시 시스템
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()
        
        # 인증 서비스
        self._auth_service: Optional[AuthenticationService] = None
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"KiwoomAPIClient initialized for {base_url}")
    
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()
    
    async def initialize(self):
        """클라이언트 초기화"""
        # 인증 서비스 초기화
        self._auth_service = AuthenticationService(
            base_url=self.base_url,
            storage_path=None  # 메모리에서만 사용
        )
        await self._auth_service.set_credentials(self.credentials)
        
        # HTTP 세션 생성
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._session = aiohttp.ClientSession(timeout=timeout)
        
        logger.info("KiwoomAPIClient initialized successfully")
    
    async def close(self):
        """리소스 정리"""
        if self._session:
            await self._session.close()
        
        if self._auth_service:
            await self._auth_service.clear_authentication()
        
        logger.info("KiwoomAPIClient closed")
    
    async def request(
        self,
        api_id: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """
        API 요청
        
        Args:
            api_id: API ID (예: ka10001)
            params: 요청 파라미터
            headers: 추가 헤더
            use_cache: 캐시 사용 여부
            
        Returns:
            API 응답 데이터
            
        Raises:
            APIError: API 요청 실패
            RateLimitError: Rate limit 초과
        """
        if not self._session or not self._auth_service:
            raise APIError("Client not initialized. Use 'async with' or call initialize()")
        
        # 캐시 확인
        if use_cache:
            cached_response = await self._get_cached_response(api_id, params)
            if cached_response:
                logger.debug(f"Cache hit for {api_id}")
                return cached_response
        
        # Rate limiting 적용
        await self._apply_rate_limit()
        
        # 요청 실행
        try:
            response = await self._execute_request(api_id, params, headers)
            
            # 캐시 저장
            if use_cache:
                await self._cache_response(api_id, params, response)
            
            return response
            
        except Exception as e:
            logger.error(f"API request failed for {api_id}: {e}")
            raise APIError(f"API request failed: {e}")
    
    @retry(
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _execute_request(
        self,
        api_id: str,
        params: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """재시도 로직이 포함된 요청 실행"""
        # 인증 헤더 생성
        auth_headers = await self._auth_service.get_authenticated_headers()
        
        # API별 헤더 생성
        api_headers = self._get_api_headers(api_id)
        
        # 사용자 정의 헤더 병합
        if headers:
            api_headers.update(headers)
        
        # 인증 헤더와 병합
        api_headers.update(auth_headers)
        
        # HTTP 요청 실행
        response = await self._make_http_request(
            method="POST",
            url=f"{self.base_url}/rest/uapi/domestic-stock/v1/quotations/inquire-price",
            headers=api_headers,
            json=params
        )
        
        # 응답 처리
        response_data = await response.json()
        
        # API 에러 확인
        if response_data.get("rt_cd") != "0":
            error_msg = response_data.get("msg1", "Unknown API error")
            error_code = response_data.get("msg_cd")
            raise APIError(error_msg, error_code)
        
        logger.debug(f"API request successful for {api_id}")
        return response_data
    
    async def _make_http_request(
        self,
        method: str,
        url: str,
        headers: Dict[str, str],
        **kwargs
    ) -> aiohttp.ClientResponse:
        """HTTP 요청 실행"""
        async with self._session.request(method, url, headers=headers, **kwargs) as response:
            if response.status >= 400:
                error_text = await response.text()
                logger.error(f"HTTP {response.status} error: {error_text}")
                response.raise_for_status()
            
            return response
    
    def _get_api_headers(
        self,
        api_id: str,
        tr_id: Optional[str] = None,
        cont_yn: str = "N",
        next_key: str = ""
    ) -> Dict[str, str]:
        """API별 헤더 생성"""
        headers = {
            "content-type": "application/json;charset=UTF-8",
            "api-id": api_id,
            "cont-yn": cont_yn,
        }
        
        if tr_id:
            headers["tr_id"] = tr_id
        
        if next_key:
            headers["ctx_area_fk100"] = next_key
            headers["ctx_area_nk100"] = next_key
        
        return headers
    
    async def _apply_rate_limit(self):
        """Rate limiting 적용"""
        async with self._rate_limit_lock:
            current_time = time.time()
            
            # 1초 이전 요청들 제거
            self._request_times = [
                req_time for req_time in self._request_times 
                if current_time - req_time < 1.0
            ]
            
            # Rate limit 확인
            if len(self._request_times) >= self.rate_limit:
                wait_time = 1.0 - (current_time - self._request_times[0])
                if wait_time > 0:
                    logger.debug(f"Rate limit hit, waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    
                    # 대기 후 다시 확인
                    current_time = time.time()
                    self._request_times = [
                        req_time for req_time in self._request_times 
                        if current_time - req_time < 1.0
                    ]
            
            # 현재 요청 시간 기록
            self._request_times.append(current_time)
    
    async def _get_cached_response(
        self,
        api_id: str,
        params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """캐시된 응답 조회"""
        cache_key = self._generate_cache_key(api_id, params)
        
        async with self._cache_lock:
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                
                # 캐시 만료 확인
                if time.time() - cache_entry["timestamp"] < self.cache_ttl:
                    return cache_entry["data"]
                else:
                    # 만료된 캐시 삭제
                    del self._cache[cache_key]
        
        return None
    
    async def _cache_response(
        self,
        api_id: str,
        params: Dict[str, Any],
        response: Dict[str, Any]
    ):
        """응답 캐시"""
        cache_key = self._generate_cache_key(api_id, params)
        
        async with self._cache_lock:
            self._cache[cache_key] = {
                "data": response,
                "timestamp": time.time()
            }
            
            # 캐시 크기 제한 (최대 1000개)
            if len(self._cache) > 1000:
                # 가장 오래된 항목 삭제
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k]["timestamp"]
                )
                del self._cache[oldest_key]
    
    def _generate_cache_key(self, api_id: str, params: Dict[str, Any]) -> str:
        """캐시 키 생성"""
        # 파라미터를 정렬하여 일관된 키 생성
        sorted_params = json.dumps(params, sort_keys=True)
        key_string = f"{api_id}:{sorted_params}"
        
        # SHA256 해시로 키 생성
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
    
    async def continuous_request(
        self,
        api_id: str,
        params: Dict[str, Any],
        max_pages: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        연속조회 요청
        
        Args:
            api_id: API ID
            params: 요청 파라미터
            max_pages: 최대 페이지 수
            
        Yields:
            페이지별 응답 데이터
        """
        page_count = 0
        next_key = ""
        
        while page_count < max_pages:
            # 연속조회 헤더 설정
            headers = {}
            if next_key:
                headers.update({
                    "cont-yn": "Y",
                    "ctx_area_fk100": next_key,
                    "ctx_area_nk100": next_key
                })
            
            # 요청 실행
            response = await self.request(api_id, params, headers)
            yield response
            
            # 다음 키 확인
            next_key = response.get("ctx_area_fk100", "")
            if not next_key:
                break
            
            page_count += 1
            logger.debug(f"Continuous request page {page_count}, next_key: {next_key}")
    
    async def batch_request(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> List[Dict[str, Any]]:
        """
        배치 요청
        
        Args:
            requests: 요청 목록 [{"api_id": "ka10001", "params": {...}}, ...]
            max_concurrent: 최대 동시 요청 수
            
        Returns:
            응답 목록
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def _single_request(req_data):
            async with semaphore:
                return await self.request(
                    api_id=req_data["api_id"],
                    params=req_data["params"],
                    headers=req_data.get("headers"),
                    use_cache=req_data.get("use_cache", False)
                )
        
        tasks = [_single_request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외를 에러 응답으로 변환
        results = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results.append({
                    "rt_cd": "1",
                    "msg1": f"Request failed: {response}",
                    "error": True
                })
            else:
                results.append(response)
        
        return results
    
    async def websocket_connect(self) -> aiohttp.ClientWebSocketResponse:
        """
        WebSocket 연결
        
        Returns:
            WebSocket 연결 객체
        """
        if not self._session:
            raise APIError("Client not initialized")
        
        # WebSocket URL 구성
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        ws_url += "/websocket"
        
        # 인증 헤더 생성
        headers = await self._auth_service.get_authenticated_headers()
        
        # WebSocket 연결
        return await self._session.ws_connect(ws_url, headers=headers)
    
    async def health_check(self) -> bool:
        """
        헬스 체크
        
        Returns:
            서비스 정상 여부
        """
        try:
            # 간단한 API 호출로 상태 확인
            await self.request(
                api_id="ka10001",
                params={"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": "005930"},
                use_cache=False
            )
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        클라이언트 통계 정보
        
        Returns:
            통계 정보 딕셔너리
        """
        current_time = time.time()
        recent_requests = [
            req_time for req_time in self._request_times
            if current_time - req_time < 60  # 최근 1분
        ]
        
        return {
            "total_cache_entries": len(self._cache),
            "recent_requests_1min": len(recent_requests),
            "current_rate_limit": self.rate_limit,
            "cache_ttl": self.cache_ttl,
            "max_retries": self.max_retries,
            "base_url": self.base_url
        }