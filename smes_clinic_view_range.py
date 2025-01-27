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
    상세 페이지에서 데이터를 추출
    """
    data_dict = {}

    # "테마" 데이터 수집
    theme_section = detail_soup.select_one("th:-soup-contains('테마')")
    if theme_section:
        theme_td = theme_section.find_next("td")
        if theme_td:
            data_dict["테마"] = theme_td.get_text(strip=True)

    # "수행 전" 데이터 수집
    before_section = detail_soup.find("th", string="수행 전")
    if before_section:
        before_td = before_section.find_next("td", class_="tdlast-child")
        if before_td:
            data_dict["수행 전"] = before_td.get_text(" ", strip=True).replace("\n", " ")

    # "수행 후" 데이터 수집
    after_section = detail_soup.find("th", string="수행 후")
    if after_section:
        after_td = after_section.find_next("td", class_="tdlast-child")
        if after_td:
            data_dict["수행 후"] = after_td.get_text(" ", strip=True).replace("\n", " ")

    # "수행내용" 데이터 수집
    content_section = detail_soup.find("th", string="수행내용")
    if content_section:
        content_td = content_section.find_next("td", class_="tdlast-child")
        if content_td:
            data_dict["수행내용"] = content_td.get_text(" ", strip=True).replace("\n", " ")

    # "현장클리닉 전***" 데이터 수집
    clinic_before_section = detail_soup.select_one("th:-soup-contains('현장클리닉 전***')")
    if clinic_before_section:
        clinic_before_td = clinic_before_section.find_next("td")
        if clinic_before_td:
            data_dict["현장클리닉 전***"] = clinic_before_td.get_text(" ", strip=True).replace("\n", " ")

    # "현장클리닉 후***" 데이터 수집
    clinic_after_section = detail_soup.select_one("th:-soup-contains('현장클리닉 후***')")
    if clinic_after_section:
        clinic_after_td = clinic_after_section.find_next("td")
        if clinic_after_td:
            data_dict["현장클리닉 후***"] = clinic_after_td.get_text(" ", strip=True).replace("\n", " ")

    # 기타 데이터 수집
    sections = {
        "개선과제": "th:-soup-contains('개선과제')",
        "해결방안": "th:-soup-contains('해결방안')",
        "향후 추진사항 및 사후관리방안": "th:-soup-contains('향후 추진사항 및 사후관리방안')",
        "특이사항": "h3.h3title:-soup-contains('특이사항')",
    }

    for key, selector in sections.items():
        element = detail_soup.select_one(selector)
        if element:
            next_td = element.find_next("td", class_="tdlast-child") or element.find_next("td")
            if next_td:
                data_dict[key] = next_td.get_text(" ", strip=True).replace("\n", " ")

    # "사후관리방안" 데이터 수집
    follow_up_section = detail_soup.select_one("h3.h3title:-soup-contains('사후관리방안')")
    if follow_up_section:
        follow_up_td = follow_up_section.find_next("td", class_="tdlast tdlast-child")
        if follow_up_td:
            data_dict["사후관리방안"] = follow_up_td.get_text(" ", strip=True).replace("\n", " ")

    return data_dict

def go_direct_page(driver, page_number, timeout=30):
    """
    자바스크립트로 goPage('page_number')를 직접 호출하여 해당 페이지로 즉시 이동.
    """
    try:
        old_html = driver.page_source
        driver.execute_script(f"goPage('{page_number}')")
        WebDriverWait(driver, timeout).until(lambda d: d.page_source != old_html)
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
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table"))
        )
        print(f"[진행] go_to_next_page: {page_number}번 페이지로 이동 완료.")
        return True
    except Exception as e:
        print(f"[오류] go_to_next_page({page_number}) 실패: {e}")
        print(f"[안내] {page_number}번 페이지로 직접 이동(자바스크립트) 시도 중...")
        return go_direct_page(driver, page_number, timeout)

def scrape_smes_clinic(start_page=1, end_page=57):
    """
    목록 및 상세 페이지 데이터 수집
    """
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    driver.implicitly_wait(10)

    collected_data = []

    try:
        list_url = "https://www.smes.go.kr/bizlink/clinicCase/clinicCaseList.do"
        driver.get(list_url)

        WebDriverWait(driver, 30).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        for page_number in range(start_page, end_page + 1):
            print(f"[진행] [페이지 {page_number}] 목록 처리 중...")
            if page_number > start_page:
                if not go_to_next_page(driver, page_number):
                    print(f"[오류] {page_number}번 페이지 이동 실패. 크롤링 중단.")
                    break

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table tbody"))
                )
                rows = driver.find_elements(By.CSS_SELECTOR, "div.list_table tbody tr")
                if not rows:
                    print(f"[안내] [페이지 {page_number}] 목록이 없습니다.")
                    continue

                for idx in range(len(rows)):
                    try:
                        rows = driver.find_elements(By.CSS_SELECTOR, "div.list_table tbody tr")
                        row = rows[idx]

                        # 분야 데이터 추출
                        field = row.find_element(By.CSS_SELECTOR, "td:nth-child(2)").text.strip()

                        # 상세 페이지 이동
                        detail_link = row.find_element(By.CSS_SELECTOR, "td.text_left[onclick^='javascript:goView']")
                        driver.execute_script("arguments[0].click();", detail_link)

                        # 상세 페이지 데이터 수집
                        WebDriverWait(driver, 30).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.view_table"))
                        )
                        detail_html = driver.page_source
                        detail_soup = BeautifulSoup(detail_html, "html.parser")

                        data_dict = extract_detail_data(detail_soup)

                        row_data = {
                            "분야": field,
                            "테마": data_dict.get("테마", ""),
                            "수행 전": data_dict.get("수행 전", ""),
                            "수행 후": data_dict.get("수행 후", ""),
                            "수행내용": data_dict.get("수행내용", ""),
                            "현장클리닉 전***": data_dict.get("현장클리닉 전***", ""),
                            "현장클리닉 후***": data_dict.get("현장클리닉 후***", ""),
                            "개선과제": data_dict.get("개선과제", ""),
                            "해결방안": data_dict.get("해결방안", ""),
                            "향후 추진사항 및 사후관리방안": data_dict.get("향후 추진사항 및 사후관리방안", ""),
                            "특이사항": data_dict.get("특이사항", ""),
                            "사후관리방안": data_dict.get("사후관리방안", ""),
                        }
                        collected_data.append(row_data)
                        print(f"[수집 완료] {row_data}")
                        driver.back()

                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "div.list_table tbody"))
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
    df = scrape_smes_clinic(start_page=1, end_page=57)

    if not df.empty:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_name = f"smes_clinic_data_{timestamp}.csv"
        df.to_csv(csv_name, index=False, encoding="utf-8-sig")
        print(f"[완료] 데이터 저장 완료: {csv_name}")
    else:
        print("[안내] 데이터가 수집되지 않았습니다.")
