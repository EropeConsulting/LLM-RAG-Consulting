import time
import datetime
import pandas as pd
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def extract_detail_data(detail_soup):
    """
    상세 페이지에서 질문과 답변 데이터를 추출
    """
    data_dict = {}

    # 질문 데이터 수집
    question_section = detail_soup.select_one("div.question_con pre")
    if question_section:
        data_dict["질문"] = question_section.get_text(strip=True)

    # 답변 데이터 수집 (여러 답변 수집)
    answers = detail_soup.select("div.reply_con pre")
    if answers:
        data_dict["답변"] = "\n\n".join(answer.get_text(strip=True) for answer in answers)

    return data_dict

def go_direct_page(driver, page_number, timeout=10):
    """
    자바스크립트로 페이지 이동
    """
    try:
        old_html = driver.page_source
        driver.execute_script(f"goPage('{page_number}')")
        WebDriverWait(driver, timeout).until(lambda d: d.page_source != old_html)
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbl-list01 tbody"))
        )
        print(f"[진행] go_direct_page: {page_number}번 페이지 이동 완료.")
        return True
    except Exception as e:
        print(f"[오류] go_direct_page({page_number}) 실패: {e}")
        return False

def go_to_next_page(driver, page_number, timeout=5):
    """
    페이지 번호 클릭하여 이동
    """
    try:
        link = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.LINK_TEXT, str(page_number)))
        )
        link.click()
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbl-list01 tbody"))
        )
        print(f"[진행] go_to_next_page: {page_number}번 페이지로 이동 완료.")
        return True
    except Exception as e:
        print(f"[오류] go_to_next_page({page_number}) 실패: {e}")
        print(f"[안내] {page_number}번 페이지로 직접 이동 시도 중...")
        return go_direct_page(driver, page_number, timeout)

def scrape_problem_data(start_page=501, end_page=522):
    """
    게시판 및 상세 페이지 데이터 수집
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    collected_data = []

    try:
        list_url = "https://www.smes.go.kr/bizlink/problem/problemView.do"
        driver.get(list_url)

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        for page_number in range(start_page, end_page + 1):
            print(f"[진행] [페이지 {page_number}] 데이터 수집 중...")
            if page_number > start_page:
                if not go_to_next_page(driver, page_number):
                    print(f"[오류] {page_number}번 페이지 이동 실패. 수집 중단.")
                    break

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbl-list01 tbody"))
                )
                rows = driver.find_elements(By.CSS_SELECTOR, "table.tbl-list01 tbody tr")
                if not rows:
                    print(f"[안내] [페이지 {page_number}] 목록이 비어 있습니다.")
                    continue

                for idx in range(len(rows)):
                    try:
                        rows = driver.find_elements(By.CSS_SELECTOR, "table.tbl-list01 tbody tr")
                        row = rows[idx]

                        # 분야 데이터 추출
                        field = row.find_element(By.CSS_SELECTOR, "td:nth-child(2) strong").text.strip()

                        # 상담내용 데이터 추출
                        content = row.find_element(By.CSS_SELECTOR, "td.al p.fld_q").text.strip()

                        # 상세 페이지 이동
                        detail_link = row.find_element(By.CSS_SELECTOR, "td.al a")
                        driver.execute_script("arguments[0].click();", detail_link)

                        # 상세 페이지 데이터 수집
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.question_con"))
                        )
                        detail_html = driver.page_source
                        detail_soup = BeautifulSoup(detail_html, "html.parser")

                        data_dict = extract_detail_data(detail_soup)

                        row_data = {
                            "분야": field,
                            "상담내용": content,
                            "질문": data_dict.get("질문", ""),
                            "답변": data_dict.get("답변", ""),
                        }
                        collected_data.append(row_data)
                        print(f"[수집 완료] {row_data}")
                        driver.back()

                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tbl-list01 tbody"))
                        )

                    except Exception as e:
                        print(f"[오류] [페이지 {page_number}] 상세 처리 중 오류(idx={idx}): {e}")
                        driver.back()

            except Exception as e:
                print(f"[오류] [페이지 {page_number}] 목록 처리 중 오류: {e}")

    finally:
        driver.quit()

    df = pd.DataFrame(collected_data)
    return df

if __name__ == "__main__":
    df = scrape_problem_data(start_page=501, end_page=522)

    if not df.empty:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_name = f"smes_problem_data_{timestamp}.csv"
        df.to_csv(csv_name, index=False, encoding="utf-8-sig")
        print(f"[완료] 데이터 저장 완료: {csv_name}")
    else:
        print("[안내] 데이터가 수집되지 않았습니다.")
