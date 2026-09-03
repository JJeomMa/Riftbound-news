# Riftbound 새 소식 → 디스코드 자동 알림

playriftbound.com 한국어 새 소식 페이지(`/ko-kr/news/`)를 15분마다 확인해서,
새 글이 올라오면 디스코드 채널에 자동으로 올려주는 GitHub Actions 봇입니다.
디스코드 봇 토큰 없이 **웹훅(Webhook)** 만으로 동작합니다.

## 1. 디스코드 웹훅 만들기

1. 알림을 받고 싶은 디스코드 채널 → 채널 설정(톱니바퀴) → **연동(Integrations)**
2. **웹후크(Webhooks)** → **새 웹후크(New Webhook)** 생성
3. 이름/채널 확인 후 **웹후크 URL 복사(Copy Webhook URL)**
   (`https://discord.com/api/webhooks/...` 형태의 URL)

## 2. GitHub 저장소 만들기

1. GitHub에서 새 저장소(Public/Private 상관없음)를 만듭니다.
2. 이 폴더(`riftbound-discord-bot`) 안의 파일들을 그대로 저장소에 업로드/푸시합니다.
   (구조 그대로 유지: `scripts/`, `.github/workflows/`, `requirements.txt` 등)

## 3. 웹훅 URL을 저장소 Secret으로 등록

1. 저장소 → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** 클릭
3. Name: `DISCORD_WEBHOOK_URL`
4. Value: 1번에서 복사한 웹훅 URL 붙여넣기 → 저장

## 4. 실행 확인

1. 저장소 → **Actions** 탭 → 좌측에 `Riftbound News Watcher` 워크플로우 선택
2. **Run workflow** 버튼으로 수동 실행 (Actions가 비활성화되어 있다면 먼저 활성화)
   - **첫 실행은 디스코드에 아무것도 올리지 않습니다.** 현재 있는 글들을
     "이미 본 글"로만 기록해서, 과거 글이 한꺼번에 쏟아지는 걸 막기 위함입니다.
3. 이후부터는 15분마다 자동 실행되며, 새 글이 생기면 그때부터 디스코드에 올라옵니다.
   - 새 글이 여러 개 한 번에 올라온 경우, 오래된 글부터 순서대로 전송됩니다.

## 참고 사항

- GitHub Actions의 `schedule`은 정확히 15분 간격이 아니라 GitHub 서버 사정에 따라
  몇 분 정도 늦게 실행될 수 있습니다 (공식적으로 알려진 제약사항).
- 확인한 글 목록은 `data/seen_news.json`에 저장되고, 실행할 때마다 자동으로
  커밋되어 저장소에 남습니다. 이 파일을 지우면 다음 실행이 "첫 실행"으로
  처리되어 현재 글들이 다시 기준선으로 잡힙니다(알림은 안 뜸).
- 사이트의 HTML 구조가 바뀌면 글 제목/설명 추출이 어색해질 수 있습니다.
  이 경우 Actions 실행 로그를 보고 알려주시면 파싱 로직을 조정해 드릴 수 있어요.
- 무료 GitHub 계정 기준으로 Public 저장소는 Actions 사용 시간 제한이 사실상
  거의 없고, Private 저장소는 매달 무료 사용량(분) 안에서 사용하시면 됩니다.
