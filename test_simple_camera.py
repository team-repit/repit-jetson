#!/usr/bin/env python3
"""
간단한 카메라 테스트 - OpenCV 창이 제대로 표시되는지 확인
"""

import cv2
import time

def test_simple_camera():
    """간단한 카메라 테스트"""
    print("🔍 간단한 카메라 테스트 시작...")
    
    # 카메라 초기화
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ 카메라를 열 수 없습니다.")
        return False
    
    # 카메라 설정
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("✅ 카메라 열기 성공")
    print("📹 카메라 창이 표시됩니다. 'q'를 누르면 종료됩니다.")
    
    start_time = time.time()
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break
        
        # 현재 시간 표시
        elapsed = time.time() - start_time
        cv2.putText(frame, f'Time: {elapsed:.1f}s', (10, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 창 표시
        cv2.namedWindow('Simple Camera Test', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Simple Camera Test', 640, 480)
        cv2.imshow('Simple Camera Test', frame)
        
        # 키 입력 처리
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("'q'를 눌러 종료합니다.")
            break
        
        # 10초 후 자동 종료
        if elapsed > 10:
            print("10초가 경과하여 자동 종료됩니다.")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("✅ 카메라 테스트 완료")
    return True

if __name__ == "__main__":
    test_simple_camera() 