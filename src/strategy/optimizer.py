# -*- coding: utf-8 -*-
"""
전략 최적화 모듈
"""
import asyncio
import logging
from itertools import product
from typing import Any, Dict, List, Optional, Type, Tuple
from datetime import datetime, timedelta
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

from .base import BaseStrategy, StrategyConfig, StrategyContext


class ParameterGrid:
    """파라미터 그리드 생성기"""
    
    def __init__(self, param_grid: Dict[str, List[Any]]):
        """
        파라미터 그리드 초기화
        
        Args:
            param_grid: 파라미터 그리드 딕셔너리
                예: {
                    'short_period': [10, 20, 30],
                    'long_period': [50, 100, 200],
                    'threshold': [0.1, 0.2, 0.3]
                }
        """
        self.param_grid = param_grid
        self.combinations = list(self._generate_combinations())
    
    def _generate_combinations(self):
        """파라미터 조합 생성"""
        keys = list(self.param_grid.keys())
        values = [self.param_grid[k] for k in keys]
        
        for combination in product(*values):
            yield dict(zip(keys, combination))
    
    def __len__(self) -> int:
        """총 조합 수"""
        return len(self.combinations)
    
    def __iter__(self):
        """반복자"""
        return iter(self.combinations)
    
    def get_combination(self, index: int) -> Dict[str, Any]:
        """특정 인덱스의 조합"""
        return self.combinations[index]


class OptimizationResult:
    """최적화 결과"""
    
    def __init__(
        self,
        best_params: Dict[str, Any],
        best_score: float,
        all_results: List[Dict[str, Any]],
        optimization_metric: str,
        total_combinations: int,
        execution_time: float
    ):
        self.best_params = best_params
        self.best_score = best_score
        self.all_results = all_results
        self.optimization_metric = optimization_metric
        self.total_combinations = total_combinations
        self.execution_time = execution_time
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 변환"""
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "optimization_metric": self.optimization_metric,
            "total_combinations": self.total_combinations,
            "execution_time": self.execution_time,
            "results_count": len(self.all_results)
        }
    
    def get_top_results(self, n: int = 10) -> List[Dict[str, Any]]:
        """상위 N개 결과"""
        sorted_results = sorted(
            self.all_results,
            key=lambda x: x.get(self.optimization_metric, float('-inf')),
            reverse=True
        )
        return sorted_results[:n]
    
    def get_parameter_analysis(self) -> Dict[str, Dict[str, float]]:
        """파라미터별 성과 분석"""
        analysis = {}
        
        # 각 파라미터별로 평균 성과 계산
        for result in self.all_results:
            params = result.get('parameters', {})
            score = result.get(self.optimization_metric, 0)
            
            for param_name, param_value in params.items():
                if param_name not in analysis:
                    analysis[param_name] = {}
                
                if param_value not in analysis[param_name]:
                    analysis[param_name][param_value] = []
                
                analysis[param_name][param_value].append(score)
        
        # 평균값 계산
        for param_name in analysis:
            for param_value in analysis[param_name]:
                scores = analysis[param_name][param_value]
                analysis[param_name][param_value] = {
                    'mean': sum(scores) / len(scores),
                    'max': max(scores),
                    'min': min(scores),
                    'count': len(scores)
                }
        
        return analysis


class StrategyOptimizer:
    """전략 파라미터 최적화"""
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        optimization_metric: str = "sharpe_ratio"
    ):
        """
        최적화기 초기화
        
        Args:
            strategy_class: 최적화할 전략 클래스
            data: 백테스트 데이터
            optimization_metric: 최적화 지표
        """
        self.strategy_class = strategy_class
        self.data = data
        self.optimization_metric = optimization_metric
        self.logger = logging.getLogger(__name__)
        
        # 지원되는 최적화 지표
        self.supported_metrics = [
            "total_return", "annualized_return", "sharpe_ratio",
            "sortino_ratio", "calmar_ratio", "max_drawdown",
            "win_rate", "profit_factor"
        ]
        
        if optimization_metric not in self.supported_metrics:
            raise ValueError(f"Unsupported metric: {optimization_metric}")
    
    async def optimize(
        self,
        param_grid: Dict[str, List[Any]],
        cv_folds: int = 5,
        test_size: float = 0.2,
        n_jobs: int = 1,
        verbose: bool = True
    ) -> OptimizationResult:
        """
        그리드 서치 최적화
        
        Args:
            param_grid: 파라미터 그리드
            cv_folds: 교차 검증 폴드 수
            test_size: 테스트 데이터 비율
            n_jobs: 병렬 작업 수
            verbose: 진행상황 출력 여부
            
        Returns:
            최적화 결과
        """
        start_time = datetime.now()
        
        # 파라미터 그리드 생성
        grid = ParameterGrid(param_grid)
        total_combinations = len(grid)
        
        if verbose:
            self.logger.info(f"Starting optimization with {total_combinations} combinations")
        
        # 데이터 분할
        train_data, test_data = self._split_data(self.data, test_size)
        
        # 병렬 최적화 실행
        if n_jobs == 1:
            results = await self._optimize_sequential(grid, train_data, cv_folds, verbose)
        else:
            results = await self._optimize_parallel(grid, train_data, cv_folds, n_jobs, verbose)
        
        # 최적 파라미터 찾기
        best_result = max(
            results,
            key=lambda x: x.get(self.optimization_metric, float('-inf'))
        )
        
        # 테스트 데이터로 최종 검증
        if len(test_data) > 0:
            test_result = await self._backtest_single(
                best_result['parameters'],
                test_data
            )
            best_result['test_performance'] = test_result
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        optimization_result = OptimizationResult(
            best_params=best_result['parameters'],
            best_score=best_result[self.optimization_metric],
            all_results=results,
            optimization_metric=self.optimization_metric,
            total_combinations=total_combinations,
            execution_time=execution_time
        )
        
        if verbose:
            self.logger.info(
                f"Optimization completed in {execution_time:.2f} seconds. "
                f"Best {self.optimization_metric}: {best_result[self.optimization_metric]:.4f}"
            )
        
        return optimization_result
    
    async def walk_forward_optimization(
        self,
        param_grid: Dict[str, List[Any]],
        optimization_window: int = 252,  # 1년
        test_window: int = 63,           # 3개월
        step_size: int = 21              # 1개월
    ) -> List[Dict[str, Any]]:
        """
        Walk-Forward 최적화
        
        Args:
            param_grid: 파라미터 그리드
            optimization_window: 최적화 윈도우 크기 (일)
            test_window: 테스트 윈도우 크기 (일)
            step_size: 이동 단계 크기 (일)
            
        Returns:
            Walk-Forward 결과 리스트
        """
        results = []
        data_length = len(self.data)
        
        # 윈도우 이동
        start_idx = 0
        while start_idx + optimization_window + test_window <= data_length:
            # 최적화 기간
            opt_end_idx = start_idx + optimization_window
            opt_data = self.data.iloc[start_idx:opt_end_idx]
            
            # 테스트 기간
            test_start_idx = opt_end_idx
            test_end_idx = test_start_idx + test_window
            test_data = self.data.iloc[test_start_idx:test_end_idx]
            
            self.logger.info(
                f"Walk-Forward window: {start_idx}-{opt_end_idx} (opt), "
                f"{test_start_idx}-{test_end_idx} (test)"
            )
            
            # 해당 기간 최적화
            temp_optimizer = StrategyOptimizer(
                self.strategy_class,
                opt_data,
                self.optimization_metric
            )
            
            opt_result = await temp_optimizer.optimize(
                param_grid,
                cv_folds=3,  # Walk-Forward에서는 폴드 수 감소
                test_size=0.0,  # 별도 테스트 데이터 사용
                verbose=False
            )
            
            # 테스트 기간 성과 측정
            test_performance = await self._backtest_single(
                opt_result.best_params,
                test_data
            )
            
            results.append({
                "optimization_period": (start_idx, opt_end_idx),
                "test_period": (test_start_idx, test_end_idx),
                "best_params": opt_result.best_params,
                "optimization_score": opt_result.best_score,
                "test_performance": test_performance
            })
            
            start_idx += step_size
        
        return results
    
    async def _optimize_sequential(
        self,
        grid: ParameterGrid,
        data: pd.DataFrame,
        cv_folds: int,
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """순차 최적화"""
        results = []
        
        for i, params in enumerate(grid):
            if verbose and i % 10 == 0:
                self.logger.info(f"Processing combination {i+1}/{len(grid)}")
            
            try:
                # 교차 검증
                cv_scores = await self._cross_validate(params, data, cv_folds)
                
                # 평균 성과 계산
                avg_score = sum(cv_scores) / len(cv_scores)
                
                result = {
                    "parameters": params,
                    self.optimization_metric: avg_score,
                    "cv_scores": cv_scores,
                    "cv_std": pd.Series(cv_scores).std()
                }
                
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"Error optimizing params {params}: {e}")
                continue
        
        return results
    
    async def _optimize_parallel(
        self,
        grid: ParameterGrid,
        data: pd.DataFrame,
        cv_folds: int,
        n_jobs: int,
        verbose: bool
    ) -> List[Dict[str, Any]]:
        """병렬 최적화"""
        # 프로세스 풀 사용 (CPU 집약적 작업)
        with ProcessPoolExecutor(max_workers=n_jobs) as executor:
            # 작업 제출
            futures = {}
            for i, params in enumerate(grid):
                future = executor.submit(
                    self._backtest_worker,
                    params,
                    data,
                    cv_folds
                )
                futures[future] = (i, params)
            
            # 결과 수집
            results = []
            completed = 0
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    
                    completed += 1
                    if verbose and completed % 10 == 0:
                        self.logger.info(f"Completed {completed}/{len(grid)} combinations")
                        
                except Exception as e:
                    i, params = futures[future]
                    self.logger.error(f"Error in combination {i} {params}: {e}")
        
        return results
    
    def _backtest_worker(
        self,
        params: Dict[str, Any],
        data: pd.DataFrame,
        cv_folds: int
    ) -> Dict[str, Any]:
        """워커 프로세스용 백테스트 함수"""
        # 동기 버전으로 실행
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            cv_scores = loop.run_until_complete(
                self._cross_validate(params, data, cv_folds)
            )
            
            avg_score = sum(cv_scores) / len(cv_scores)
            
            return {
                "parameters": params,
                self.optimization_metric: avg_score,
                "cv_scores": cv_scores,
                "cv_std": pd.Series(cv_scores).std()
            }
            
        finally:
            loop.close()
    
    async def _cross_validate(
        self,
        params: Dict[str, Any],
        data: pd.DataFrame,
        cv_folds: int
    ) -> List[float]:
        """교차 검증"""
        scores = []
        fold_size = len(data) // cv_folds
        
        for fold in range(cv_folds):
            # 검증 데이터 분할
            val_start = fold * fold_size
            val_end = (fold + 1) * fold_size if fold < cv_folds - 1 else len(data)
            
            train_data = pd.concat([
                data.iloc[:val_start],
                data.iloc[val_end:]
            ])
            val_data = data.iloc[val_start:val_end]
            
            # 백테스트 실행
            result = await self._backtest_single(params, train_data)
            score = result.get(self.optimization_metric, 0)
            scores.append(score)
        
        return scores
    
    async def _backtest_single(
        self,
        params: Dict[str, Any],
        data: pd.DataFrame
    ) -> Dict[str, Any]:
        """단일 백테스트 실행"""
        try:
            # 전략 생성
            config = StrategyConfig(
                name=f"{self.strategy_class.__name__}_test",
                parameters=params
            )
            strategy = self.strategy_class(config)
            
            # 간단한 백테스트 시뮬레이션
            # 실제로는 BacktestEngine을 사용해야 함
            
            # 기본 성과 지표 계산
            returns = data['close'].pct_change().dropna()
            
            if len(returns) == 0:
                return {self.optimization_metric: 0}
            
            # 간단한 성과 지표 계산
            total_return = (1 + returns).prod() - 1
            annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
            volatility = returns.std() * (252 ** 0.5)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            max_drawdown = (returns.cumsum().expanding().max() - returns.cumsum()).max()
            
            return {
                "total_return": total_return,
                "annualized_return": annualized_return,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "volatility": volatility,
                "win_rate": (returns > 0).mean(),
                "profit_factor": returns[returns > 0].sum() / abs(returns[returns < 0].sum()) if (returns < 0).sum() != 0 else float('inf'),
                "sortino_ratio": annualized_return / (returns[returns < 0].std() * (252 ** 0.5)) if (returns < 0).std() > 0 else 0,
                "calmar_ratio": annualized_return / max_drawdown if max_drawdown > 0 else 0
            }
            
        except Exception as e:
            self.logger.error(f"Backtest error for params {params}: {e}")
            return {self.optimization_metric: float('-inf')}
    
    def _split_data(
        self,
        data: pd.DataFrame,
        test_size: float
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """데이터 분할"""
        if test_size <= 0:
            return data, pd.DataFrame()
        
        split_idx = int(len(data) * (1 - test_size))
        train_data = data.iloc[:split_idx]
        test_data = data.iloc[split_idx:]
        
        return train_data, test_data


class BayesianOptimizer:
    """베이지안 최적화 (고급 최적화)"""
    
    def __init__(
        self,
        strategy_class: Type[BaseStrategy],
        data: pd.DataFrame,
        optimization_metric: str = "sharpe_ratio"
    ):
        """베이지안 최적화기 초기화"""
        self.strategy_class = strategy_class
        self.data = data
        self.optimization_metric = optimization_metric
        self.logger = logging.getLogger(__name__)
    
    async def optimize(
        self,
        param_bounds: Dict[str, Tuple[float, float]],
        n_iter: int = 50,
        init_points: int = 10
    ) -> OptimizationResult:
        """
        베이지안 최적화 실행
        
        Args:
            param_bounds: 파라미터 범위 딕셔너리
            n_iter: 최적화 반복 횟수
            init_points: 초기 탐색 점 수
            
        Returns:
            최적화 결과
        """
        # scikit-optimize나 optuna 같은 라이브러리 필요
        # 여기서는 기본 구현만 제공
        
        self.logger.warning("Bayesian optimization requires additional dependencies")
        raise NotImplementedError("Bayesian optimization not implemented yet")