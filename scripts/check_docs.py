#!/usr/bin/env python
"""
문서 일관성 및 업데이트 확인 스크립트
"""
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def check_project_status():
    """PROJECT_STATUS.md 최신 업데이트 확인"""
    status_file = Path("docs/PROJECT_STATUS.md")
    if not status_file.exists():
        print("❌ PROJECT_STATUS.md 파일이 없습니다!")
        return False
    
    content = status_file.read_text(encoding='utf-8')
    
    # 날짜 패턴 찾기
    date_pattern = r"최종 업데이트: (\d{4}-\d{2}-\d{2})"
    match = re.search(date_pattern, content)
    
    if match:
        last_update = datetime.strptime(match.group(1), "%Y-%m-%d")
        today = datetime.now()
        days_diff = (today - last_update).days
        
        if days_diff > 2:
            print(f"⚠️  PROJECT_STATUS.md가 {days_diff}일 전에 마지막으로 업데이트되었습니다.")
            return False
        else:
            print("✅ PROJECT_STATUS.md가 최신입니다.")
            return True
    else:
        print("❌ PROJECT_STATUS.md에서 업데이트 날짜를 찾을 수 없습니다.")
        return False


def check_todo_in_claude():
    """CLAUDE.md의 현재 작업 확인"""
    claude_file = Path("CLAUDE.md")
    if not claude_file.exists():
        print("❌ CLAUDE.md 파일이 없습니다!")
        return False
    
    content = claude_file.read_text(encoding='utf-8')
    
    # 현재 작업 섹션 찾기
    if "현재 작업 중인 내용" in content:
        print("✅ CLAUDE.md에 현재 작업이 정의되어 있습니다.")
        return True
    else:
        print("⚠️  CLAUDE.md에 현재 작업 섹션이 없습니다.")
        return False


def check_workflow_exists():
    """WORKFLOW.md 존재 확인"""
    workflow_file = Path("docs/WORKFLOW.md")
    if workflow_file.exists():
        print("✅ WORKFLOW.md가 존재합니다.")
        return True
    else:
        print("❌ WORKFLOW.md가 없습니다! 작업 프로세스 문서가 필요합니다.")
        return False


def check_test_coverage():
    """테스트 커버리지 파일 확인"""
    coverage_file = Path(".coverage")
    if coverage_file.exists():
        mod_time = datetime.fromtimestamp(coverage_file.stat().st_mtime)
        age_minutes = (datetime.now() - mod_time).seconds / 60
        
        if age_minutes < 30:
            print("✅ 최근 테스트 커버리지가 존재합니다.")
            return True
        else:
            print("⚠️  테스트 커버리지가 오래되었습니다.")
            return False
    else:
        print("⚠️  테스트 커버리지 파일이 없습니다.")
        return False


def check_todos():
    """TODO 주석 검색"""
    todo_count = 0
    for root, dirs, files in os.walk("src"):
        # __pycache__ 디렉토리 제외
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                content = file_path.read_text(encoding='utf-8')
                todos = re.findall(r"# TODO:.*", content)
                todo_count += len(todos)
                
                if todos:
                    print(f"📌 {file_path}: {len(todos)}개의 TODO")
                    for todo in todos[:3]:  # 최대 3개만 표시
                        print(f"   - {todo.strip()}")
    
    if todo_count > 0:
        print(f"\n⚠️  총 {todo_count}개의 TODO가 발견되었습니다.")
    else:
        print("✅ TODO가 없습니다.")
    
    return todo_count == 0


def main():
    """메인 실행 함수"""
    print("📚 문서 일관성 검사")
    print("==================")
    
    checks = [
        ("프로젝트 상태", check_project_status),
        ("CLAUDE.md 작업", check_todo_in_claude),
        ("작업 프로세스", check_workflow_exists),
        ("테스트 커버리지", check_test_coverage),
        ("TODO 검색", check_todos),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name} 확인 중...")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {name} 확인 중 오류: {e}")
            results.append(False)
    
    # 결과 요약
    print("\n" + "=" * 40)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ 모든 검사 통과! ({passed}/{total})")
        return 0
    else:
        print(f"⚠️  일부 검사 실패 ({passed}/{total})")
        print("\n다음 사항을 확인하세요:")
        print("1. PROJECT_STATUS.md 업데이트")
        print("2. CLAUDE.md 현재 작업 업데이트")
        print("3. TODO 항목 처리")
        return 1


if __name__ == "__main__":
    sys.exit(main())