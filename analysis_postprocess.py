from __future__ import annotations

from typing import Any, Dict, Optional


def send_record_and_upload(
    api_client,
    json_data: Dict[str, Any],
    video_path: str,
    exercise_label: str = "운동",
) -> Optional[Dict[str, Any]]:
    """
    운동 기록을 서버로 전송하고 필요 시 영상 업로드까지 수행합니다.

    Args:
        api_client: RepitAPIClient 인스턴스 (또는 호환 객체)
        json_data: 운동 기록 JSON 데이터
        video_path: 로컬 분석 영상 경로
        exercise_label: 로그 출력용 운동 이름

    Returns:
        API 응답 딕셔너리 또는 None (토큰이 없거나 오류가 발생한 경우)
    """
    if not api_client:
        print("ℹ️  토큰이 없어 서버 전송과 영상 업로드를 생략합니다.")
        return None

    print(f"API로 {exercise_label} 운동 기록을 전송 중...")

    try:
        api_result = api_client.create_record(json_data)
        if api_result.get("success"):
            print(f"✓ API 전송 성공: {api_result.get('message', '성공')}")
            record_id = api_result.get("data", {}).get("result", {}).get("record_id")
            if record_id:
                print(f"  저장된 기록 ID: {record_id}")
                print("Presigned URL을 받아 영상을 업로드합니다...")
                video_upload_result = api_client.upload_record_video(record_id, video_path)
                api_result["video_upload"] = video_upload_result
                if video_upload_result.get("success"):
                    print("  ✓ 영상 업로드 완료 및 확정")
                else:
                    print(f"  ✗ 영상 업로드 실패: {video_upload_result.get('message', '사유 미상')}")
            else:
                print("⚠️  API 응답에 record_id가 없어 영상 업로드를 생략합니다.")
        else:
            print(f"✗ API 전송 실패: {api_result.get('message', '알 수 없는 오류')}")
        return api_result
    except Exception as exc:  # pylint: disable=broad-except
        print(f"✗ API 전송 중 오류 발생: {exc}")
        return {"success": False, "message": str(exc)}

