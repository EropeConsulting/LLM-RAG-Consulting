from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import csv
import time

def scrape_kmtca_consultants_selenium(output_csv='kmtca_consultants.csv', total_pages=334):
    # 1) 크롬드라이버 설정
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # options.add_argument("headless")  # 필요 시 헤드리스 모드
    driver = webdriver.Chrome(service=service, options=options)

    all_data = []

    # 2) 각 페이지를 직접 URL로 접근
    base_url = "https://www.kmtca.or.kr/?p=145&page={}"
    for page in range(1, total_pages+1):
        print(f"[+] Now scraping page {page}/{total_pages}...")
        driver.get(base_url.format(page))
        time.sleep(2)  # 페이지 렌더링 기다리기 (필요 시 조정)

        # 3) BeautifulSoup 파싱
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        table = soup.find("table")
        if not table:
            print(f"    테이블을 찾지 못했습니다. (page={page})")
            continue

        tbody = table.find("tbody")
        if not tbody:
            print(f"    tbody를 찾지 못했습니다. (page={page})")
            continue

        rows = tbody.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 6:
                continue
            구분 = cols[0].get_text(strip=True)
            지도분야 = cols[1].get_text(strip=True)
            이름 = cols[2].get_text(strip=True)
            소속컨설팅사 = cols[3].get_text(strip=True)
            이메일 = cols[4].get_text(strip=True)
            연락처 = cols[5].get_text(strip=True)
            all_data.append([구분, 지도분야, 이름, 소속컨설팅사, 이메일, 연락처])

    # 4) 브라우저 종료
    driver.quit()

    # 5) CSV 저장 (utf-8-sig 로 Excel에서 한글 안 깨지게)
    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["구분", "지도분야", "이름", "소속컨설팅사", "E-Mail", "연락처"])
        writer.writerows(all_data)

    print(f"수집 완료! 총 {len(all_data)}개의 행을 '{output_csv}'에 저장했습니다.")


if __name__ == "__main__":
    scrape_kmtca_consultants_selenium()
