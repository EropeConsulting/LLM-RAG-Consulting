from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import csv
import time

def scrape_kmtca_consulting_firms(output_csv='kmtca_consulting.csv', total_pages=147):
    """
    '한국경영기술지도사회' 컨설팅사 검색 페이지(?p=146)에서
    업체명, 대표자명, 주소, 연락처를 페이지별로 수집하여 CSV로 저장.
    """
    # 1) 크롬 드라이버 세팅 (webdriver-manager 사용 예시)
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("headless")  # 브라우저 창 표시 없이 진행하려면 주석 해제
    driver = webdriver.Chrome(service=service, options=options)

    all_data = []
    base_url = "https://www.kmtca.or.kr/?p=146&page={}"

    for page in range(1, total_pages + 1):
        print(f"[+] Now scraping page {page}/{total_pages}...")
        driver.get(base_url.format(page))
        # 페이지 렌더링 대기 (필요에 따라 조정)
        time.sleep(2)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # 테이블 요소 찾기 (사이트 HTML 구조에 따라 수정 가능)
        table = soup.find("table")
        if not table:
            print(f"    테이블을 찾지 못했습니다. (page={page})")
            continue

        tbody = table.find("tbody")
        if not tbody:
            print(f"    tbody를 찾지 못했습니다. (page={page})")
            continue

        # 행(tr)별로 데이터(업체명, 대표자명, 주소, 연락처) 파싱
        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            # 실제로 테이블 열이 4개인지 확인 (필요시 조정)
            if len(cols) < 4:
                continue

            업체명 = cols[0].get_text(strip=True)
            대표자명 = cols[1].get_text(strip=True)
            주소 = cols[2].get_text(strip=True)
            연락처 = cols[3].get_text(strip=True)

            all_data.append([업체명, 대표자명, 주소, 연락처])

    # 크롬 브라우저 종료
    driver.quit()

    # 수집 데이터 CSV로 저장 (Excel에서 한글이 안 깨지도록 utf-8-sig)
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["업체명", "대표자명", "주소", "연락처"])
        writer.writerows(all_data)

    print(f"[완료] 총 {len(all_data)}개의 행을 '{output_csv}'에 저장했습니다.")

if __name__ == "__main__":
    # 기본적으로 총 147페이지 (1467개 / 페이지당 10개)라 가정
    scrape_kmtca_consulting_firms()
