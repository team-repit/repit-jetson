#!/usr/bin/env python3
"""
젯슨에서 실행하기 위한 경로 설정 스크립트
"""

import os
import sys

def get_jetson_info():
    """젯슨 환경 정보 확인"""
    print("🚀 젯슨 환경 정보 확인")
    print("=" * 40)
    
    # 현재 디렉토리
    current_dir = os.getcwd()
    print(f"현재 작업 디렉토리: {current_dir}")
    
    # 홈 디렉토리
    home_dir = os.path.expanduser("~")
    print(f"홈 디렉토리: {home_dir}")
    
    # 사용자명
    username = os.path.expanduser("~").split("/")[-1]
    print(f"사용자명: {username}")
    
    # 권장 프로젝트 경로
    recommended_path = os.path.join(home_dir, "repit")
    print(f"권장 프로젝트 경로: {recommended_path}")
    
    # 절대 경로 예시
    absolute_path = os.path.abspath(".")
    print(f"현재 절대 경로: {absolute_path}")
    
    print("\n" + "=" * 40)
    print("📋 젯슨에서 실행하기 위한 절차:")
    print("1. 이 정보를 복사해서 젯슨에서 참고하세요")
    print("2. 젯슨에서 권장 경로에 프로젝트를 복사하세요")
    print("3. create_desktop_file.py를 실행하세요")
    
    return {
        "current_dir": current_dir,
        "home_dir": home_dir,
        "username": username,
        "recommended_path": recommended_path,
        "absolute_path": absolute_path
    }

def create_jetson_desktop_file(target_path=None):
    """젯슨용 데스크톱 파일 생성"""
    if target_path is None:
        target_path = os.path.expanduser("~/repit")
    
    print(f"\n🔧 젯슨용 데스크톱 파일 생성 (경로: {target_path})")
    
    # 데스크톱 파일 내용 (젯슨용)
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Re:PiT
Comment=운동 자세 분석 GUI 애플리케이션
Exec=python3 {target_path}/main_pyside6.py
Icon={target_path}/ui_pyside6/logo.png
Terminal=false
StartupNotify=true
Categories=Education;Sports;
Keywords=exercise;fitness;squat;analysis;re:pit;
"""
    
    # 데스크톱 파일 경로
    desktop_file = os.path.join(target_path, "repit.desktop")
    
    try:
        with open(desktop_file, 'w', encoding='utf-8') as f:
            f.write(desktop_content)
        
        print(f"✅ 젯슨용 데스크톱 파일 생성됨: {desktop_file}")
        return desktop_file
    except Exception as e:
        print(f"❌ 데스크톱 파일 생성 실패: {e}")
        return None

def create_jetson_launcher(target_path=None):
    """젯슨용 런처 스크립트 생성"""
    if target_path is None:
        target_path = os.path.expanduser("~/repit")
    
    print(f"\n🔧 젯슨용 런처 스크립트 생성 (경로: {target_path})")
    
    launcher_content = f"""#!/bin/bash
# Re:PiT 젯슨 런처 스크립트

# 프로젝트 디렉토리로 이동
cd "{target_path}"

# 가상환경 활성화 (있는 경우)
if [ -d "app-env-pyside6" ]; then
    source app-env-pyside6/bin/activate
    echo "✅ PySide6 가상환경 활성화됨"
elif [ -d "app-env" ]; then
    source app-env/bin/activate
    echo "✅ 기본 가상환경 활성화됨"
fi

# Re:PiT 앱 실행
echo "🚀 Re:PiT 시작 중..."
python3 main_pyside6.py

echo "👋 Re:PiT이 종료되었습니다."
"""
    
    launcher_path = os.path.join(target_path, "launch_repit.sh")
    
    try:
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        
        # 실행 권한 부여
        os.chmod(launcher_path, 0o755)
        print(f"✅ 젯슨용 런처 스크립트 생성됨: {launcher_path}")
        return launcher_path
    except Exception as e:
        print(f"❌ 런처 스크립트 생성 실패: {e}")
        return None

def main():
    """메인 함수"""
    print("🚀 젯슨용 Re:PiT 설정 도구")
    print("=" * 50)
    
    # 젯슨 정보 확인
    jetson_info = get_jetson_info()
    
    # 사용자 입력 받기
    print(f"\n💡 권장 경로: {jetson_info['recommended_path']}")
    custom_path = input("젯슨에서 사용할 경로를 입력하세요 (엔터시 권장 경로 사용): ").strip()
    
    if not custom_path:
        custom_path = jetson_info['recommended_path']
    
    # 젯슨용 파일들 생성
    desktop_file = create_jetson_desktop_file(custom_path)
    launcher_file = create_jetson_launcher(custom_path)
    
    if desktop_file and launcher_file:
        print("\n" + "=" * 50)
        print("🎉 젯슨용 설정 완료!")
        print(f"\n📁 프로젝트 경로: {custom_path}")
        print(f"📄 데스크톱 파일: {desktop_file}")
        print(f"🚀 런처 스크립트: {launcher_file}")
        
        print("\n📋 젯슨에서 실행할 명령어들:")
        print(f"1. 프로젝트 복사: scp -r . {jetson_info['username']}@젯슨IP:{custom_path}")
        print(f"2. 젯슨 접속: ssh {jetson_info['username']}@젯슨IP")
        print(f"3. 설정 실행: cd {custom_path} && python3 setup_jetson_path.py")
        print(f"4. 앱 실행: ./launch_repit.sh")
    else:
        print("❌ 설정 실패")

if __name__ == "__main__":
    main()
