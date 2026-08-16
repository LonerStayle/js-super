#!/usr/bin/env python3
import iterm2

async def main(connection):
    app = await iterm2.async_get_app(connection)
    
    resume_message = "이어서 계속 진행해줘"
    target_keyword = "hit your session limit"
    
    matched_count = 0

    for window in app.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                try:
                    # 세션 화면 버퍼 가져오기
                    screen = await session.async_get_screen_contents()
                    lines = [screen.line(i).string for i in range(screen.number_of_lines)]
                    
                    # [핵심] 전체가 아닌 '가장 최근 맨 아래 20줄'만 추출
                    recent_lines = lines[-20:] if len(lines) >= 20 else lines
                    recent_text = "\n".join(recent_lines)

                    # 현재 화면 최하단에 리밋 문구가 떠 있는 경우에만 전송
                    if target_keyword in recent_text:
                        await session.async_send_text(f"{resume_message}\r")
                        matched_count += 1
                        print(f"[전송 완료] 세션 ID: {session.session_id}")
                except Exception as e:
                    print(f"[오류 발생] 세션 {session.session_id}: {e}")

    print(f"총 {matched_count}개의 세션에 재개 메시지를 보냈습니다.")

iterm2.run_until_complete(main)