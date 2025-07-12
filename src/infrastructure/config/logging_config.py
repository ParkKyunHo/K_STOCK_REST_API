"""
로깅 설정 모듈
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Any

import structlog
import yaml
from pythonjsonlogger import jsonlogger


def load_config() -> Dict[str, Any]:
    """설정 파일 로드"""
    config_path = Path(__file__).parent.parent.parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(config: Dict[str, Any] = None) -> None:
    """로깅 시스템 설정"""
    if config is None:
        config = load_config()
    
    log_config = config.get("logging", {})
    
    # 로그 디렉토리 생성
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.get("level", "INFO")))
    
    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 포맷터 설정
    formatter = logging.Formatter(
        log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    
    # 콘솔 핸들러
    if log_config.get("handlers", {}).get("console", {}).get("enabled", True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(
            getattr(logging, log_config["handlers"]["console"].get("level", "INFO"))
        )
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_config = log_config.get("handlers", {}).get("file", {})
    if file_config.get("enabled", True):
        log_file = file_config.get("path", "logs/kiwoom_backtest.log")
        
        # RotatingFileHandler 설정
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=file_config.get("max_size_mb", 100) * 1024 * 1024,
            backupCount=file_config.get("backup_count", 10),
            encoding="utf-8"
        )
        file_handler.setLevel(
            getattr(logging, file_config.get("level", "INFO"))
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # 구조화된 로깅 설정
    if log_config.get("handlers", {}).get("structured", {}).get("enabled", False):
        setup_structured_logging()


def setup_structured_logging() -> None:
    """구조화된 로깅 설정 (structlog)"""
    structlog.configure(
        processors=[
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> logging.Logger:
    """로거 인스턴스 생성"""
    return logging.getLogger(name)


def setup_json_logging() -> None:
    """JSON 형식 로깅 설정"""
    json_formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # 모든 핸들러에 JSON 포맷터 적용
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(json_formatter)


class LoggerAdapter(logging.LoggerAdapter):
    """컨텍스트 정보를 포함한 로거 어댑터"""
    
    def process(self, msg, kwargs):
        """로그 메시지에 컨텍스트 정보 추가"""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def create_logger_with_context(name: str, **context) -> LoggerAdapter:
    """컨텍스트 정보를 포함한 로거 생성"""
    logger = get_logger(name)
    return LoggerAdapter(logger, context)


# 로깅 레벨 설정 헬퍼 함수
def set_log_level(logger_name: str, level: str) -> None:
    """특정 로거의 로그 레벨 설정"""
    logger = logging.getLogger(logger_name)
    logger.setLevel(getattr(logging, level.upper()))


def disable_third_party_loggers() -> None:
    """써드파티 라이브러리의 과도한 로깅 비활성화"""
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("websockets").setLevel(logging.WARNING)


# 모듈 임포트 시 자동 설정
setup_logging()
disable_third_party_loggers()