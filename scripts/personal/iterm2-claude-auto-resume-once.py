#!/usr/bin/env python3
import iterm2
import asyncio
import re
from datetime import datetime, time

handled_sessions = set()
scheduled_sessions = set()

async def wait_and_resume(target_hour, session, resume_message):
    session_id = session.session_id
    now = datetime.now()
    target_time = datetime.combine(now.date(), time(hour=target_hour, minute=0, second=5))
    
    delay = (target_time - now).total_seconds()
    if delay > 0:
        print(f"[{session_id}] {target_hour}시까지 예약 대기 ({int(delay)}초 남음)")
        await asyncio.sleep(delay)
    
    if session_id in handled_sessions:
        return

    try:
        # 리셋 시점에 화면 최하단 7줄 재검증 (계정 전환 등으로 이미 사용 중인지 확인)
        screen = await session.async_get_screen_contents()
        lines = [screen.line(i).string for i in range(screen.number_of_lines)]
        bottom_text = "\n".join(lines[-7:])

        if "hit your session limit" in bottom_text:
            handled_sessions.add(session_id)
            # 엔터 입력을 위해 \r 전송
            await session.async_send_text(f"{resume_message}\r")
            print(f"[{session_id}] 제한 해제 시간 도달 -> 1회 재개 메시지 전송 성공!")
        else:
            print(f"[{session_id}] 작업 상태 변경 감지됨 -> 전송을 건너뜁니다.")
    except Exception as e:
        print(f"[{session_id}] 오류 발생: {e}")

async def monitor_session(session):
    session_id = session.session_id
    resume_message = "이어서 계속 진행해줘"
    time_pattern = re.compile(r"resets\s+(\d{1,2})(am|pm)", re.IGNORECASE)

    # 3초 주기로 화면을 검사하는 안전한 비동기 루프
    while True:
        if session_id in handled_sessions or session_id in scheduled_sessions:
            break

        try:
            screen = await session.async_get_screen_contents()
            lines = [screen.line(i).string for i in range(screen.number_of_lines)]
            recent_text = "\n".join(lines[-10:])
            
            if "hit your session limit" in recent_text:
                match = time_pattern.search(recent_text)
                if match:
                    hour = int(match.group(1))
                    ampm = match.group(2).lower()
                    if ampm == "pm" and hour < 12:
                        hour += 12
                    elif ampm == "am" and hour == 12:
                        hour = 0
                    
                    scheduled_sessions.add(session_id)
                    print(f"[{session_id}] 리밋 감지됨! {hour}시 자동 재개 예약 등록")
                    asyncio.create_task(wait_and_resume(hour, session, resume_message))
                    break
        except Exception:
            pass

        await asyncio.sleep(3)

async def main(connection):
    app = await iterm2.async_get_app(connection)
    print("Claude 리밋 자동 재개 모니터링 데몬 시작됨.")
    
    for window in app.windows:
        for tab in window.tabs:
            for session in tab.sessions:
                asyncio.create_task(monitor_session(session))

iterm2.run_forever(main)