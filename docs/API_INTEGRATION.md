# 키움증권 REST API 통합 가이드

## 1. 개요

이 문서는 키움증권 REST API를 시스템에 통합하는 방법을 설명합니다. 추출된 API 명세서(`kiwoom_api_final.json`)를 기반으로 178개의 API를 효율적으로 활용하는 방법을 제공합니다.

## 2. API 구조 개요

### 2.1 API 카테고리

1. **인증 (OAuth2)** - 2개 API
   - `au10001`: 접근토큰 발급
   - `au10002`: 접근토큰 폐기

2. **국내주식** - 176개 API
   - 시세 조회 (ka10xxx)
   - 주문 실행 (kt10xxx)
   - 계좌 관리 (kt00xxx)
   - 실시간 데이터 (WebSocket)

### 2.2 공통 요청 구조

```python
# 모든 API 요청의 공통 헤더
headers = {
    "content-type": "application/json;charset=UTF-8",
    "authorization": f"Bearer {access_token}",
    "api-id": "ka10001",  # API별 고유 ID
    "cont-yn": "N",        # 연속조회 여부
    "next-key": ""         # 연속조회 키
}
```

## 3. 인증 시스템

### 3.1 OAuth2 토큰 발급

```python
class OAuth2Manager:
    """OAuth2 인증 관리자"""
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://api.kiwoom.com"
        self.token = None
        self.token_expires_at = None
    
    async def get_access_token(self) -> str:
        """접근 토큰 발급 (au10001)"""
        if self.token and self._is_token_valid():
            return self.token
        
        url = f"{self.base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.app_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                data = await response.json()
                
                self.token = data["token"]
                self.token_expires_at = datetime.fromisoformat(data["expires_dt"])
                
                return self.token
    
    def _is_token_valid(self) -> bool:
        """토큰 유효성 검사"""
        if not self.token_expires_at:
            return False
        
        # 만료 5분 전에 갱신
        buffer = timedelta(minutes=5)
        return datetime.now() < (self.token_expires_at - buffer)
```

### 3.2 토큰 자동 갱신

```python
class AutoRefreshToken:
    """자동 토큰 갱신 데코레이터"""
    
    def __init__(self, oauth_manager: OAuth2Manager):
        self.oauth_manager = oauth_manager
    
    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 토큰 갱신 확인
            await self.oauth_manager.get_access_token()
            
            try:
                return await func(*args, **kwargs)
            except APIError as e:
                if e.status_code == 401:
                    # 토큰 재발급 후 재시도
                    self.oauth_manager.token = None
                    await self.oauth_manager.get_access_token()
                    return await func(*args, **kwargs)
                raise
        
        return wrapper
```

## 4. API 클라이언트 구현

### 4.1 기본 클라이언트

```python
class KiwoomAPIClient:
    """키움 REST API 클라이언트"""
    
    def __init__(self, oauth_manager: OAuth2Manager):
        self.oauth_manager = oauth_manager
        self.base_url = "https://api.kiwoom.com"
        self.rate_limiter = RateLimiter(calls_per_second=10)
        
        # API 명세 로드
        with open("kiwoom_api_final.json", "r", encoding="utf-8") as f:
            self.api_spec = json.load(f)["apis"]
    
    @AutoRefreshToken
    async def request(
        self, 
        api_id: str, 
        params: Dict[str, Any],
        use_mock: bool = False
    ) -> Dict[str, Any]:
        """API 요청 실행"""
        # API 정보 조회
        api_info = self.api_spec.get(api_id)
        if not api_info:
            raise ValueError(f"Unknown API ID: {api_id}")
        
        # URL 구성
        url = f"{self.base_url}{api_info['url']}"
        if use_mock:
            url = url.replace("api.kiwoom.com", "mockapi.kiwoom.com")
        
        # 헤더 구성
        headers = await self._build_headers(api_id)
        
        # Rate Limiting
        async with self.rate_limiter:
            return await self._execute_request(
                method=api_info["method"],
                url=url,
                headers=headers,
                json=params
            )
    
    async def _build_headers(self, api_id: str) -> Dict[str, str]:
        """요청 헤더 구성"""
        token = await self.oauth_manager.get_access_token()
        
        return {
            "content-type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {token}",
            "api-id": api_id,
            "cont-yn": "N",
            "next-key": ""
        }
```

### 4.2 연속 조회 처리

```python
class ContinuousQueryHandler:
    """연속 조회 처리기"""
    
    def __init__(self, client: KiwoomAPIClient):
        self.client = client
    
    async def fetch_all(
        self, 
        api_id: str, 
        params: Dict[str, Any],
        max_pages: int = 100
    ) -> List[Dict]:
        """연속 조회로 모든 데이터 가져오기"""
        all_data = []
        next_key = ""
        cont_yn = "N"
        
        for page in range(max_pages):
            # 헤더에 연속조회 정보 추가
            headers_override = {
                "cont-yn": cont_yn,
                "next-key": next_key
            }
            
            response = await self.client.request(
                api_id, 
                params,
                headers_override=headers_override
            )
            
            # 데이터 추가
            if "data" in response:
                all_data.extend(response["data"])
            
            # 연속조회 정보 확인
            resp_headers = response.get("headers", {})
            cont_yn = resp_headers.get("cont-yn", "N")
            next_key = resp_headers.get("next-key", "")
            
            if cont_yn != "Y":
                break
        
        return all_data
```

## 5. 주요 API 사용 예시

### 5.1 시세 데이터 조회

```python
class MarketDataAPI:
    """시세 데이터 API"""
    
    def __init__(self, client: KiwoomAPIClient):
        self.client = client
    
    async def get_daily_ohlcv(
        self, 
        symbol: str, 
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """일봉 데이터 조회 (ka10081)"""
        params = {
            "stk_cd": symbol,
            "base_dt": end_date,
            "upd_stkpc_tp": "1"  # 수정주가
        }
        
        response = await self.client.request("ka10081", params)
        
        # DataFrame 변환
        data = response["body"]["stk_dt_pole_chart_qry"]
        df = pd.DataFrame(data)
        
        # 날짜 형식 변환
        df["date"] = pd.to_datetime(df["stk_dt"])
        df.set_index("date", inplace=True)
        
        # 필요한 컬럼만 선택
        df = df[["cur_prc", "opng_stk_prc", "hghst_stk_prc", 
                 "lwst_stk_prc", "trde_qty"]]
        df.columns = ["close", "open", "high", "low", "volume"]
        
        # 숫자 타입 변환
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df
    
    async def get_minute_data(
        self,
        symbol: str,
        interval: int = 1
    ) -> pd.DataFrame:
        """분봉 데이터 조회 (ka10080)"""
        params = {
            "stk_cd": symbol,
            "mnst_dvsn": str(interval),  # 1, 3, 5, 10, 30, 60
            "stnd_ymd": datetime.now().strftime("%Y%m%d")
        }
        
        return await self.client.request("ka10080", params)
```

### 5.2 주문 실행

```python
class OrderAPI:
    """주문 실행 API"""
    
    def __init__(self, client: KiwoomAPIClient):
        self.client = client
    
    async def buy_order(
        self,
        account_no: str,
        symbol: str,
        quantity: int,
        price: Optional[int] = None,
        order_type: str = "00"  # 00: 지정가, 01: 시장가
    ) -> Dict[str, str]:
        """매수 주문 (kt10000)"""
        params = {
            "dmst_stex_tp": "KRX",  # 거래소 구분
            "stk_cd": symbol,
            "ord_qty": str(quantity),
            "ord_uv": str(price) if price else "",
            "trde_tp": order_type,
            "cond_uv": ""
        }
        
        response = await self.client.request("kt10000", params)
        
        return {
            "order_no": response["body"]["ord_no"],
            "exchange": response["body"]["dmst_stex_tp"]
        }
    
    async def sell_order(
        self,
        account_no: str,
        symbol: str,
        quantity: int,
        price: Optional[int] = None,
        order_type: str = "00"
    ) -> Dict[str, str]:
        """매도 주문 (kt10001)"""
        # kt10000과 동일한 구조
        params = {
            "dmst_stex_tp": "KRX",
            "stk_cd": symbol,
            "ord_qty": str(quantity),
            "ord_uv": str(price) if price else "",
            "trde_tp": order_type,
            "cond_uv": ""
        }
        
        return await self.client.request("kt10001", params)
```

### 5.3 계좌 정보 조회

```python
class AccountAPI:
    """계좌 정보 API"""
    
    def __init__(self, client: KiwoomAPIClient):
        self.client = client
    
    async def get_balance(self, account_no: str) -> Dict[str, Any]:
        """계좌 잔고 조회 (kt00005)"""
        params = {
            "acnt_no": account_no
        }
        
        response = await self.client.request("kt00005", params)
        
        # 잔고 정보 파싱
        positions = []
        for item in response["body"]["positions"]:
            positions.append({
                "symbol": item["stk_cd"],
                "name": item["stk_nm"],
                "quantity": int(item["hld_qty"]),
                "avg_price": float(item["avg_buy_prc"]),
                "current_price": float(item["cur_prc"]),
                "pnl": float(item["evlu_pft"]),
                "pnl_rate": float(item["evlu_pft_rt"])
            })
        
        return {
            "total_assets": float(response["body"]["tot_evlu_prica"]),
            "cash": float(response["body"]["dncl_blce"]),
            "positions": positions
        }
    
    async def get_orders(
        self, 
        account_no: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """주문 내역 조회 (kt00007)"""
        params = {
            "acnt_no": account_no,
            "strt_dt": start_date,
            "end_dt": end_date,
            "ord_tp": "0",  # 전체
            "excg_tp": "0"  # 전체
        }
        
        # 연속조회 처리
        handler = ContinuousQueryHandler(self.client)
        return await handler.fetch_all("kt00007", params)
```

## 6. WebSocket 실시간 데이터

### 6.1 WebSocket 연결

```python
class KiwoomWebSocket:
    """키움 WebSocket 클라이언트"""
    
    def __init__(self, oauth_manager: OAuth2Manager):
        self.oauth_manager = oauth_manager
        self.ws_url = "wss://api.kiwoom.com/ws"
        self.subscriptions = {}
    
    async def connect(self):
        """WebSocket 연결"""
        token = await self.oauth_manager.get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}"
        }
        
        self.ws = await websockets.connect(
            self.ws_url, 
            extra_headers=headers
        )
        
        # 메시지 수신 태스크 시작
        asyncio.create_task(self._message_handler())
    
    async def subscribe_quote(self, symbols: List[str]):
        """실시간 시세 구독 (0B)"""
        for symbol in symbols:
            message = {
                "header": {
                    "api_id": "0B",
                    "tr_type": "1"  # 등록
                },
                "body": {
                    "stk_cd": symbol
                }
            }
            
            await self.ws.send(json.dumps(message))
            self.subscriptions[symbol] = "0B"
    
    async def _message_handler(self):
        """메시지 처리"""
        async for message in self.ws:
            data = json.loads(message)
            await self._process_message(data)
```

### 6.2 실시간 데이터 처리

```python
class RealtimeDataProcessor:
    """실시간 데이터 처리기"""
    
    def __init__(self):
        self.handlers = {
            "0B": self._handle_quote,      # 체결
            "0C": self._handle_orderbook,  # 호가
            "00": self._handle_order,      # 주문체결
            "04": self._handle_balance     # 잔고
        }
        self.event_bus = EventBus()
    
    async def process(self, api_id: str, data: Dict):
        """실시간 데이터 처리"""
        handler = self.handlers.get(api_id)
        if handler:
            await handler(data)
    
    async def _handle_quote(self, data: Dict):
        """체결 데이터 처리"""
        quote = {
            "symbol": data["stk_cd"],
            "price": float(data["cur_prc"]),
            "volume": int(data["trde_qty"]),
            "time": data["trde_tm"]
        }
        
        await self.event_bus.publish("quote_update", quote)
```

## 7. 에러 처리

### 7.1 API 에러 코드

```python
class APIErrorHandler:
    """API 에러 처리기"""
    
    ERROR_CODES = {
        "E0001": "인증 실패",
        "E0002": "권한 없음",
        "E0003": "요청 한도 초과",
        "E0004": "잘못된 파라미터",
        "E0005": "시스템 점검 중"
    }
    
    @classmethod
    def handle_error(cls, response: Dict) -> None:
        """API 에러 처리"""
        if "error" in response:
            error_code = response["error"]["code"]
            error_msg = response["error"]["message"]
            
            known_error = cls.ERROR_CODES.get(error_code)
            if known_error:
                raise APIError(f"{known_error}: {error_msg}", error_code)
            else:
                raise APIError(f"Unknown error: {error_msg}", error_code)
```

### 7.2 재시도 로직

```python
class RetryPolicy:
    """재시도 정책"""
    
    def __init__(
        self, 
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        retry_codes: List[int] = [429, 500, 502, 503, 504]
    ):
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.retry_codes = retry_codes
    
    async def execute(self, func: Callable, *args, **kwargs):
        """재시도 로직 실행"""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except APIError as e:
                last_exception = e
                
                if e.status_code not in self.retry_codes:
                    raise
                
                if attempt < self.max_retries:
                    delay = self.backoff_factor ** attempt
                    logger.warning(
                        f"Retry {attempt + 1}/{self.max_retries} "
                        f"after {delay}s for error: {e}"
                    )
                    await asyncio.sleep(delay)
        
        raise last_exception
```

## 8. 캐싱 전략

### 8.1 API 응답 캐싱

```python
class APICache:
    """API 응답 캐시"""
    
    def __init__(self):
        self.cache = {}
        self.ttl = {
            "ka10001": 3600,    # 종목정보: 1시간
            "ka10081": 300,     # 일봉: 5분
            "ka10080": 60,      # 분봉: 1분
            "kt00001": 10       # 예수금: 10초
        }
    
    def get_cache_key(self, api_id: str, params: Dict) -> str:
        """캐시 키 생성"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{api_id}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    async def get(self, api_id: str, params: Dict) -> Optional[Dict]:
        """캐시 조회"""
        key = self.get_cache_key(api_id, params)
        
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires_at"]:
                return entry["data"]
        
        return None
    
    async def set(self, api_id: str, params: Dict, data: Dict):
        """캐시 저장"""
        key = self.get_cache_key(api_id, params)
        ttl = self.ttl.get(api_id, 60)
        
        self.cache[key] = {
            "data": data,
            "expires_at": datetime.now() + timedelta(seconds=ttl)
        }
```

## 9. 성능 최적화

### 9.1 배치 요청

```python
class BatchRequestHandler:
    """배치 요청 처리기"""
    
    def __init__(self, client: KiwoomAPIClient):
        self.client = client
    
    async def fetch_multiple_stocks(
        self, 
        symbols: List[str],
        api_id: str = "ka10001"
    ) -> Dict[str, Dict]:
        """여러 종목 동시 조회"""
        tasks = []
        
        for symbol in symbols:
            params = {"stk_cd": symbol}
            task = self.client.request(api_id, params)
            tasks.append(task)
        
        # 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 결과 매핑
        data = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {symbol}: {result}")
                continue
            data[symbol] = result
        
        return data
```

### 9.2 연결 풀링

```python
class ConnectionPool:
    """HTTP 연결 풀"""
    
    def __init__(self, max_connections: int = 20):
        self.connector = aiohttp.TCPConnector(
            limit=max_connections,
            ttl_dns_cache=300
        )
        self.session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """세션 가져오기"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                connector=self.connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def close(self):
        """연결 종료"""
        if self.session:
            await self.session.close()
```

## 10. 테스트 및 디버깅

### 10.1 Mock API 사용

```python
class MockAPIClient(KiwoomAPIClient):
    """테스트용 Mock API 클라이언트"""
    
    def __init__(self):
        super().__init__(None)
        self.use_mock = True
        self.mock_responses = self._load_mock_responses()
    
    async def request(self, api_id: str, params: Dict) -> Dict:
        """Mock 응답 반환"""
        if api_id in self.mock_responses:
            return self.mock_responses[api_id]
        
        # 실제 Mock API 호출
        return await super().request(api_id, params, use_mock=True)
```

### 10.2 API 로깅

```python
class APILogger:
    """API 호출 로거"""
    
    def __init__(self):
        self.logger = logging.getLogger("api_client")
    
    async def log_request(self, api_id: str, params: Dict):
        """요청 로깅"""
        self.logger.info(
            "API Request",
            extra={
                "api_id": api_id,
                "params": self._sanitize_params(params)
            }
        )
    
    async def log_response(
        self, 
        api_id: str, 
        response: Dict,
        duration: float
    ):
        """응답 로깅"""
        self.logger.info(
            "API Response",
            extra={
                "api_id": api_id,
                "status": response.get("status"),
                "duration_ms": duration * 1000
            }
        )
    
    def _sanitize_params(self, params: Dict) -> Dict:
        """민감정보 제거"""
        sanitized = params.copy()
        sensitive_fields = ["password", "pin", "secret"]
        
        for field in sensitive_fields:
            if field in sanitized:
                sanitized[field] = "***"
        
        return sanitized
```

---

**버전**: 1.0.0  
**작성일**: 2024-01-12  
**API 명세서**: kiwoom_api_final.json (178개 API)