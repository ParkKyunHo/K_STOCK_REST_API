# 키움 REST API 최종 추출 리포트

## 전체 통계
- 총 API 수: 178
- 완전한 정보를 가진 API: 175
- 총 요청 파라미터: 683
- 총 응답 파라미터: 3399

## 파라미터가 많은 주요 API (10개 이상)
- ka10001: 주식기본정보요청 (요청: 1, 응답: 45)
- ka10002: 주식거래원요청 (요청: 1, 응답: 37)
- ka10003: 체결정보요청 (요청: 1, 응답: 13)
- ka10004: 주식호가요청 (요청: 1, 응답: 69)
- ka10005: 주식일주월시분요청 (요청: 1, 응답: 18)
- ka10006: 주식시분요청 (요청: 1, 응답: 10)
- ka10007: 시세표성정보요청 (요청: 1, 응답: 124)
- ka10008: 주식외국인종목별매매동향 (요청: 1, 응답: 12)
- ka10010: 업종프로그램요청 (요청: 1, 응답: 18)
- ka10011: 신주인수권전체시세요청 (요청: 1, 응답: 13)

## 주요 API 상세 샘플

### au10001: 접근토큰 발급
- URL: `POST /oauth2/token`
- Content-Type: application/json;charset=UTF-8

#### Request Body (3 parameters)
- `grant_type`: grant_type (String, Y)
- `appkey`: 앱키 (String, Y)
- `secretkey`: 시크릿키 (String, Y)

#### Response Body (3 fields)
- `expires_dt`: 만료일 (String)
- `token_type`: 토큰타입 (String)
- `token`: 접근토큰 (String)

### kt10000: 주식 매수주문
- URL: `POST /api/dostk/ordr`
- Content-Type: application/json;charset=UTF-8

#### Request Body (6 parameters)
- `dmst_stex_tp`: 국내거래소구분 (String, Y)
- `stk_cd`: 종목코드 (String, Y)
- `ord_qty`: 주문수량 (String, Y)
- `ord_uv`: 주문단가 (String, N)
- `trde_tp`: 매매구분 (String, Y)
- ... 외 1개

#### Response Body (2 fields)
- `ord_no`: 주문번호 (String)
- `dmst_stex_tp`: 국내거래소구분 (String)

### ka10081: 주식일봉차트조회요청
- URL: `POST /api/dostk/chart`
- Content-Type: application/json;charset=UTF-8

#### Request Body (3 parameters)
- `stk_cd`: 종목코드 (String, Y)
- `base_dt`: 기준일자 (String, Y)
- `upd_stkpc_tp`: 수정주가구분 (String, Y)

#### Response Body (16 fields)
- `stk_cd`: 종목코드 (String)
- `stk_dt_pole_chart_qry`: 주식일봉차트조회 (LIST)
- `- cur_prc`: 현재가 (String)
- `- trde_qty`: 거래량 (String)
- `- trde_prica`: 거래대금 (String)
- ... 외 11개
