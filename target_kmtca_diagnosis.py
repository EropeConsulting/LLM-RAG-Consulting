from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import csv
import time


def scrape_kmtca_diagnosis_institutions(output_csv='kmtca_diagnosis_institutions.csv', total_pages=24):
    """
    '한국경영기술지도사회' 기업진단기관 검색 페이지(?p=147)에서
    업체명, 대표자명, 주소, 연락처를 페이지별로 수집하여 CSV로 저장.
    """
    # 1) 크롬 드라이버 세팅 (webdriver-manager 사용 예시)
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("headless")  # 창 없이 실행하려면 주석 해제
    driver = webdriver.Chrome(service=service, options=options)

    base_url = "https://www.kmtca.or.kr/?p=147&page={}"
    all_data = []

    for page in range(1, total_pages + 1):
        print(f"[+] Now scraping page {page}/{total_pages}...")

        # 각 페이지로 이동
        driver.get(base_url.format(page))
        # 자바스크립트 로딩 대기 시간 (필요에 따라 조정)
        time.sleep(2)

        # 현재 페이지의 HTML 소스 가져오기
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # 테이블 찾기
        table = soup.find("table")
        if not table:
            print(f"  - 테이블을 찾지 못했습니다. (page={page})")
            continue

        tbody = table.find("tbody")
        if not tbody:
            print(f"  - tbody를 찾지 못했습니다. (page={page})")
            continue

        # 행별로 데이터(업체명, 대표자명, 주소, 연락처) 추출
        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            # 실제 컬럼 수가 5개 이상인지 확인 (비고 컬럼까지 있는 경우)
            # 여기서는 4개만 사용(업체명, 대표자명, 주소, 연락처)
            if len(cols) < 4:
                continue

            업체명 = cols[0].get_text(strip=True)
            대표자명 = cols[1].get_text(strip=True)
            주소 = cols[2].get_text(strip=True)
            연락처 = cols[3].get_text(strip=True)

            all_data.append([업체명, 대표자명, 주소, 연락처])

    # 브라우저 종료
    driver.quit()

    # CSV로 저장 (utf-8-sig: Excel 한글 깨짐 방지)
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["업체명", "대표자명", "주소", "연락처"])
        writer.writerows(all_data)

    print(f"[완료] 총 {len(all_data)}개의 행을 '{output_csv}'에 저장했습니다.")


if __name__ == "__main__":
    scrape_kmtca_diagnosis_institutions()
