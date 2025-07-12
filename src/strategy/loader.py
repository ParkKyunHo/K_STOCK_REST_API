# -*- coding: utf-8 -*-
"""
전략 로더 - 플러그인 시스템
"""
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import sys
import traceback

from .base import BaseStrategy, StrategyConfig, StrategyFactory


class StrategyLoader:
    """전략 동적 로더"""
    
    def __init__(self, strategy_dirs: List[str] = None):
        """
        전략 로더 초기화
        
        Args:
            strategy_dirs: 전략 디렉토리 목록
        """
        self.strategy_dirs = strategy_dirs or [
            "plugins/strategies",
            "src/strategy/examples",
            "strategies"
        ]
        self.logger = logging.getLogger(__name__)
        self.loaded_strategies: Dict[str, Type[BaseStrategy]] = {}
        self.load_errors: Dict[str, str] = {}
    
    def load_all_strategies(self) -> Dict[str, Type[BaseStrategy]]:
        """
        모든 전략 로드
        
        Returns:
            로드된 전략 딕셔너리 {이름: 클래스}
        """
        self.loaded_strategies.clear()
        self.load_errors.clear()
        
        for strategy_dir in self.strategy_dirs:
            if Path(strategy_dir).exists():
                self._load_strategies_from_directory(strategy_dir)
        
        # 팩토리에 등록
        for name, strategy_class in self.loaded_strategies.items():
            StrategyFactory.register(name, strategy_class)
        
        self.logger.info(
            f"Loaded {len(self.loaded_strategies)} strategies, "
            f"{len(self.load_errors)} errors"
        )
        
        return self.loaded_strategies
    
    def load_strategy_from_file(self, file_path: str) -> Optional[Type[BaseStrategy]]:
        """
        파일에서 단일 전략 로드
        
        Args:
            file_path: 전략 파일 경로
            
        Returns:
            로드된 전략 클래스 또는 None
        """
        try:
            strategy_class = self._load_strategy_class_from_file(Path(file_path))
            if strategy_class:
                self.loaded_strategies[strategy_class.__name__] = strategy_class
                StrategyFactory.register(strategy_class.__name__, strategy_class)
                self.logger.info(f"Loaded strategy: {strategy_class.__name__}")
                return strategy_class
            
        except Exception as e:
            self.load_errors[file_path] = str(e)
            self.logger.error(f"Failed to load strategy from {file_path}: {e}")
        
        return None
    
    def reload_strategy(self, name: str) -> bool:
        """
        전략 재로드
        
        Args:
            name: 전략 이름
            
        Returns:
            재로드 성공 여부
        """
        if name not in self.loaded_strategies:
            return False
        
        try:
            # 모듈 재로드
            strategy_class = self.loaded_strategies[name]
            module = inspect.getmodule(strategy_class)
            
            if module:
                importlib.reload(module)
                
                # 새로운 클래스 찾기
                for obj_name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseStrategy) and 
                        obj != BaseStrategy and
                        obj.__name__ == name):
                        
                        self.loaded_strategies[name] = obj
                        StrategyFactory.register(name, obj)
                        self.logger.info(f"Reloaded strategy: {name}")
                        return True
            
        except Exception as e:
            self.logger.error(f"Failed to reload strategy {name}: {e}")
        
        return False
    
    def validate_strategy(self, strategy_class: Type[BaseStrategy]) -> List[str]:
        """
        전략 유효성 검사
        
        Args:
            strategy_class: 전략 클래스
            
        Returns:
            검증 오류 목록
        """
        errors = []
        
        try:
            # 필수 메서드 확인
            required_methods = [
                'name', 'version', 'description', 'parameters',
                'generate_signals', 'validate_parameters'
            ]
            
            for method in required_methods:
                if not hasattr(strategy_class, method):
                    errors.append(f"Missing required method: {method}")
            
            # 임시 인스턴스 생성하여 기본 검증
            try:
                temp_config = StrategyConfig(name="test")
                temp_instance = strategy_class(temp_config)
                
                # 프로퍼티 접근 테스트
                if hasattr(temp_instance, 'name'):
                    _ = temp_instance.name
                if hasattr(temp_instance, 'version'):
                    _ = temp_instance.version
                if hasattr(temp_instance, 'description'):
                    _ = temp_instance.description
                if hasattr(temp_instance, 'parameters'):
                    _ = temp_instance.parameters
                
            except Exception as e:
                errors.append(f"Instance creation failed: {e}")
                
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return errors
    
    def get_strategy_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        전략 정보 조회
        
        Args:
            name: 전략 이름
            
        Returns:
            전략 정보 딕셔너리
        """
        if name not in self.loaded_strategies:
            return None
        
        strategy_class = self.loaded_strategies[name]
        
        try:
            # 임시 인스턴스로 정보 추출
            temp_config = StrategyConfig(name=name)
            temp_instance = strategy_class(temp_config)
            
            info = {
                "name": name,
                "class_name": strategy_class.__name__,
                "module": strategy_class.__module__,
                "file": inspect.getfile(strategy_class),
                "doc": strategy_class.__doc__ or "",
                "version": getattr(temp_instance, 'version', 'Unknown'),
                "description": getattr(temp_instance, 'description', ''),
                "parameters": getattr(temp_instance, 'parameters', {}),
                "validation_errors": self.validate_strategy(strategy_class)
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get info for strategy {name}: {e}")
            return None
    
    def list_loaded_strategies(self) -> List[str]:
        """로드된 전략 목록"""
        return list(self.loaded_strategies.keys())
    
    def get_load_errors(self) -> Dict[str, str]:
        """로드 오류 목록"""
        return self.load_errors.copy()
    
    def _load_strategies_from_directory(self, directory: str):
        """디렉토리에서 전략 로드"""
        strategy_dir = Path(directory)
        
        if not strategy_dir.exists():
            self.logger.warning(f"Strategy directory not found: {directory}")
            return
        
        self.logger.info(f"Loading strategies from: {directory}")
        
        # Python 파일 찾기
        for file_path in strategy_dir.rglob("*.py"):
            # 내부 파일 제외
            if file_path.name.startswith("_"):
                continue
            
            try:
                strategy_class = self._load_strategy_class_from_file(file_path)
                if strategy_class:
                    name = strategy_class.__name__
                    
                    # 중복 확인
                    if name in self.loaded_strategies:
                        self.logger.warning(f"Duplicate strategy name: {name}")
                        continue
                    
                    # 유효성 검사
                    validation_errors = self.validate_strategy(strategy_class)
                    if validation_errors:
                        error_msg = f"Validation errors: {', '.join(validation_errors)}"
                        self.load_errors[str(file_path)] = error_msg
                        self.logger.error(f"Strategy validation failed for {name}: {error_msg}")
                        continue
                    
                    self.loaded_strategies[name] = strategy_class
                    self.logger.debug(f"Loaded strategy: {name} from {file_path}")
                
            except Exception as e:
                self.load_errors[str(file_path)] = str(e)
                self.logger.error(f"Failed to load strategy from {file_path}: {e}")
                self.logger.debug(traceback.format_exc())
    
    def _load_strategy_class_from_file(self, file_path: Path) -> Optional[Type[BaseStrategy]]:
        """파일에서 전략 클래스 로드"""
        try:
            # 모듈 스펙 생성
            module_name = f"strategy_{file_path.stem}_{hash(str(file_path))}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if spec is None or spec.loader is None:
                return None
            
            # 모듈 로드
            module = importlib.util.module_from_spec(spec)
            
            # 시스템 모듈에 추가 (상대 import 지원)
            sys.modules[module_name] = module
            
            try:
                spec.loader.exec_module(module)
            finally:
                # 모듈 정리 (메모리 누수 방지)
                if module_name in sys.modules:
                    del sys.modules[module_name]
            
            # BaseStrategy 서브클래스 찾기
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, BaseStrategy) and 
                    obj != BaseStrategy and
                    obj.__module__ == module_name):
                    return obj
            
        except Exception as e:
            self.logger.error(f"Error loading strategy from {file_path}: {e}")
            raise
        
        return None


class StrategyManager:
    """전략 관리자"""
    
    def __init__(self, loader: StrategyLoader = None):
        """
        전략 관리자 초기화
        
        Args:
            loader: 전략 로더 (없으면 기본 로더 생성)
        """
        self.loader = loader or StrategyLoader()
        self.logger = logging.getLogger(__name__)
        self._strategy_cache: Dict[str, BaseStrategy] = {}
    
    def initialize(self):
        """전략 관리자 초기화"""
        self.loader.load_all_strategies()
        self.logger.info("Strategy manager initialized")
    
    def get_strategy(self, name: str, config: StrategyConfig = None) -> Optional[BaseStrategy]:
        """
        전략 인스턴스 생성
        
        Args:
            name: 전략 이름
            config: 전략 설정
            
        Returns:
            전략 인스턴스
        """
        try:
            if config is None:
                config = StrategyConfig(name=name)
            
            return StrategyFactory.create(name, config)
            
        except Exception as e:
            self.logger.error(f"Failed to create strategy {name}: {e}")
            return None
    
    def list_available_strategies(self) -> List[Dict[str, Any]]:
        """
        사용 가능한 전략 목록
        
        Returns:
            전략 정보 리스트
        """
        strategies = []
        
        for name in self.loader.list_loaded_strategies():
            info = self.loader.get_strategy_info(name)
            if info:
                strategies.append(info)
        
        return strategies
    
    def get_strategy_by_category(self) -> Dict[str, List[str]]:
        """
        카테고리별 전략 분류
        
        Returns:
            카테고리별 전략 딕셔너리
        """
        categories = {}
        
        for name in self.loader.list_loaded_strategies():
            info = self.loader.get_strategy_info(name)
            if info:
                # 기본 카테고리 설정
                category = "기타"
                
                # 이름이나 설명에서 카테고리 추론
                name_lower = name.lower()
                desc_lower = info.get('description', '').lower()
                
                if any(keyword in name_lower or keyword in desc_lower 
                       for keyword in ['ma', 'moving', 'average', '이동평균']):
                    category = "추세추종"
                elif any(keyword in name_lower or keyword in desc_lower 
                         for keyword in ['rsi', 'stoch', 'momentum', '모멘텀']):
                    category = "모멘텀"
                elif any(keyword in name_lower or keyword in desc_lower 
                         for keyword in ['bollinger', 'volatility', '변동성']):
                    category = "변동성"
                elif any(keyword in name_lower or keyword in desc_lower 
                         for keyword in ['arbitrage', '차익거래']):
                    category = "차익거래"
                
                if category not in categories:
                    categories[category] = []
                categories[category].append(name)
        
        return categories
    
    def reload_all_strategies(self):
        """모든 전략 재로드"""
        self.loader.load_all_strategies()
        self._strategy_cache.clear()
        self.logger.info("All strategies reloaded")
    
    def validate_all_strategies(self) -> Dict[str, List[str]]:
        """
        모든 전략 유효성 검사
        
        Returns:
            전략별 검증 오류 딕셔너리
        """
        validation_results = {}
        
        for name, strategy_class in self.loader.loaded_strategies.items():
            errors = self.loader.validate_strategy(strategy_class)
            if errors:
                validation_results[name] = errors
        
        return validation_results