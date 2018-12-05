import datetime
from NewsScraper import NaverNews

def main():
    #     keyword = '우울증'   # 뉴스 검색할 키워드
    keyword = None  # 검색 키둬드
    day_start = None  # 검색 시작일
    day_end = None  # 검색 종료일

    # 키워드 입력
    while True:
        keyword = input("검색어 입력:").strip()
        if len(keyword) < 2:
            print('검색어는 2글자 이상이어야 합니다')
            continue
        break;

    # 검색 시작일 입력
    day_start = input('검색시작일 입력 YYYY-mm-dd , Enter 치시면 현재일부터 30일간의 기사를 검색합니다: ').strip()

    # 입력된게 없으면 '현재일'
    if not day_start or len(day_start) == 0:
        # day_start = datetime.datetime.now()

        myNaver = NaverNews(keyword)

    else:
        day_end = input(
            '검색종료일 입력 YYYY-mm-dd, Enter 치시면 {day_start} 이후 30일간의 기사를 검색합니다: '.format(day_start=day_start)).strip()

        if not day_end or len(day_end) == 0:
            day_end = datetime.datetime.strptime(day_start, '%Y-%m-%d') + datetime.timedelta(days=30)
            day_end = datetime.datetime.strftime(day_end, '%Y-%m-%d')

        myNaver = NaverNews(keyword, day_start, day_end)

    myNaver.read_all_page_url(1, 10)  # 1번 기사부터 10개씩.  기사 url 수집
    myNaver.get_all_articles()  # 기사 본문 수집
    myNaver.analyze_article()  # 기사 어휘 분석


if __name__ == '__main__':
    main()