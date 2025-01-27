import time
import datetime
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def go_direct_page(driver, page_number, timeout=30):
    """
    자바스크립트로 goPage('page_number')를 직접 호출하여 해당 페이지로 즉시 이동.
    이동 후, 목록(div.list_table)이 표시될 때까지 대기.
    """
    try:
        old_html = driver.page_source

        # (1) JS로 페이지 이동
        driver.execute_script(f"goPage('{page_number}')")

        # (2) page_source가 바뀔 때까지 대기
        WebDriverWait(driver, timeout).until(
            lambda d: d.page_source != old_html
        )

        # (3) 목록(div.list_table) 나타날 때까지 대기
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table"))
        )

        print(f"[진행] go_direct_page: {page_number}번 페이지 이동 완료.")
        return True
    except Exception as e:
        print(f"[오류] go_direct_page({page_number}) 실패: {e}")
        return False


def go_to_next_page(driver, page_number, timeout=30):
    """
    목록 페이지 하단에 있는 해당 페이지 번호(예: '321')의 링크 텍스트를 직접 찾고 클릭.
    이동 실패 시, 자바스크립트 호출(= go_direct_page 방식)로 재시도.
    이동 후, 목록(div.list_table)이 표시될 때까지 대기.
    """
    try:
        # (A) 우선 해당 페이지 번호의 링크가 표시될 때까지 대기
        link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.LINK_TEXT, str(page_number)))
        )
        link.click()

        # (B) 페이지 로딩 완료 대기
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table"))
        )

        print(f"[진행] go_to_next_page: {page_number}번 페이지로 이동 완료.")
        return True

    except Exception as e:
        print(f"[오류] go_to_next_page({page_number}) 링크 클릭 실패: {e}")
        print(f"[안내] {page_number}번 페이지로 직접 이동(자바스크립트) 시도 중...")

        # (C) 만약 링크 클릭에 실패하면 자바스크립트 방식을 재시도
        try:
            return go_direct_page(driver, page_number, timeout=timeout)
        except Exception as ee:
            print(f"[오류] go_to_next_page({page_number}) 자바스크립트 재시도도 실패: {ee}")
            return False


def scrape_smes_counseling(start_page=1801, end_page=2410):
    """
    1) 첫 페이지(start_page)로는 go_direct_page()를 사용하여 바로 이동
    2) 이후 페이지부터 end_page까지는 go_to_next_page()를 사용해 순차 이동
    3) 각 페이지의 목록 -> 상세 -> 뒤로가기 -> 다음 목록... 순서로 처리
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # chrome_options.add_argument("--headless")  # 필요시 주석 해제

    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    collected_data = []

    try:
        # (A) 목록 페이지(초기화면)
        list_url = "https://www.smes.go.kr/bizlink/counselingCase/counselingCaseList.do"
        driver.get(list_url)

        # 로딩 대기
        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # (B) 시작 페이지로 바로 이동
        if start_page > 1:
            moved = go_direct_page(driver, start_page, timeout=40)
            if not moved:
                print(f"[오류] 시작 페이지({start_page}) 이동 실패. 종료.")
                return pd.DataFrame()
        else:
            # 만약 start_page=1 이면, 이미 1번 페이지가 표시되어 있을 수 있음
            pass

        # (C) start_page ~ end_page 순회
        for page_number in range(start_page, end_page + 1):
            print(f"[진행] [페이지 {page_number}] 목록 처리 중...")

            # 혹시 루프가 처음(=start_page) 이외의 페이지라면,
            # go_to_next_page()로 순차 이동
            if page_number > start_page:
                moved = go_to_next_page(driver, page_number)
                if not moved:
                    print(f"[오류] {page_number}번 페이지 이동 실패. 크롤링 중단.")
                    break

            # (C-1) 목록 로드 확인
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table"))
                )
            except Exception as e:
                print(f"[오류] [페이지 {page_number}] div.list_table 로딩 실패: {e}")
                continue

            # (C-2) 아이템 수집
            items = driver.find_elements(By.CSS_SELECTOR, "a[onclick^='javascript:goView']")
            if not items:
                print(f"[안내] [페이지 {page_number}] 목록이 없습니다.")
                continue

            print(f"[디버그] [페이지 {page_number}] 목록 항목 수: {len(items)}")

            # 상세 페이지 크롤링
            for idx in range(len(items)):
                try:
                    # 매번 find_elements 재호출 (뒤로가기 후 stale 방지)
                    items = driver.find_elements(By.CSS_SELECTOR, "a[onclick^='javascript:goView']")
                    item = items[idx]

                    # 클릭 가능 대기
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a[onclick^='javascript:goView']"))
                    )
                    item.click()

                    # 상세 페이지 로딩 대기
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.view_table"))
                    )

                    detail_html = driver.page_source
                    detail_soup = BeautifulSoup(detail_html, "html.parser")

                    table = detail_soup.select_one("table")
                    if not table:
                        print("[안내] 상세 페이지에 테이블이 없습니다.")
                        driver.back()
                        continue

                    rows = table.select("tr")
                    data_dict = {}
                    for row in rows:
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            key = th.get_text(strip=True)
                            val = td.get_text(strip=True)
                            data_dict[key] = val

                    # 예시 키
                    question = data_dict.get("질문", "")
                    answer = data_dict.get("답변", "")

                    row_data = {
                        "분류": data_dict.get("분류", ""),
                        "공개여부": data_dict.get("공개여부", ""),
                        "제목": data_dict.get("제목", ""),
                        "작성일": data_dict.get("작성일", ""),
                        "작성자": data_dict.get("작성자", ""),
                        "조회수": data_dict.get("조회수", ""),
                        "질문": question,
                        "답변": answer,
                        # 필요하면 추가 필드
                        "기업경영***": data_dict.get("기업경영***", ""),
                        "첨부파일": data_dict.get("첨부파일", ""),
                    }
                    collected_data.append(row_data)
                    print(f"[수집 완료] {row_data}")

                    # 상세 -> 뒤로가기
                    driver.back()

                    # 목록 페이지 로딩 대기
                    WebDriverWait(driver, 20).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table"))
                    )

                except Exception as e:
                    print(f"[오류] [페이지 {page_number}] 상세 처리 중 오류(idx={idx}): {e}")
                    driver.back()
                    continue

    finally:
        driver.quit()

    # 결과 DataFrame 변환
    df = pd.DataFrame(collected_data)
    return df


if __name__ == "__main__":
    # 예시: 321부터 500까지
    df = scrape_smes_counseling(start_page=2001, end_page=2410)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_name = f"smes_counseling_data_{timestamp}.csv"
    df.to_csv(csv_name, index=False, encoding="utf-8-sig")
    print("크롤링 완료 및 데이터 저장 완료.")
