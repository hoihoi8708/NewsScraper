import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from collections import Counter
import konlpy.tag
import matplotlib.pyplot as plt
from urllib import parse   # url encoding
import datetime

# Windows 환경의 경우 matplotlib 한글 글꼴 설정

from matplotlib import font_manager, rc
font_name = font_manager.FontProperties(fname="C:/Windows/Fonts/malgun.ttf").get_name()
rc('font', family=font_name)



# 제거할 패턴 정의
Except_Words = [
    r'\D+}\s\s',
    r'\[\D+\]',
    r'Copyrights\D+',
    r'사진\=뉴스타파',
    r'\/뉴시스',
    r'\/뉴스타파',
    r'뉴스타파 캡처',
    r'<사진>',
    r'사진\=',
    r'캡처',
    r'.\w{3} 동아닷컴 기자 \D+',
    r'.\w{3} \w+@donga.com\D+',
    r'.(\s)\w+@donga.com\D+',
    r'.\w{2}\/\w{3} 기자 \w+@hani.co.kr',
    r'\w{3} \w{3} \w{3} 기자 \w+@hani.co.kr',
    r'\w{3} 기자 \w+@hani.co.kr',
    r'▶ \D+',
    r'\w{3} 기자 \w+@kyunghyang.com',
    r'\w{3}·\w{3} 기자  \w+@kyunghyang.com',
    r'\t',
    '윤민혁 기자']

# 치환할 패턴 정의
#other_words1 = ['양 회장','양씨', '양진호 회장', '양진호씨', '양진호 씨']

Other_Words1 = []
Replace_Words1 = []

# 5대 일간지 별 기사수집할 언론사와 그 key 값
Name_News = {
    # key : 언론사
    "chosun" : "조선일보",
    "donga" : "동아일보",
    "hankyoreh" : "한겨레",   # '한겨레언론사 선정', '한겨례'
    "kyunghyang" : "경향신문",
    "joongang" : "중앙일보"
}

Name_Pos = {
    "Noun" : "명사",
    "Adjective" : "형용사",
    "Verb" : "동사"
}

Stop_Words = [
    '재테크','배포','금지', '기자', 'co','kr','나가기','페이스북','com', '.kr', '뉴스1', '이나', '면서'
]


# 네이버 뉴스 기사 크롤링 하고 품사별 빈도수 분석하는 클래스
class NaverNews:
    # 네이버 뉴스 검색 URL
    Page_Url = "https://search.naver.com/search.naver?&where=news&query={keyword}&sm=tab_pge&sort=0&photo=0&field=0&reporter_article=&pd=3&ds={ds1}&de={de1}&docid=&nso=so:r,p:from{ds2}to{de2},a:all&mynews=1&cluster_rank=33&start={start}&refresh_start=0"

    # 생성자,  검색어가 매개변수
    def __init__(self, searchword, day_start=None, day_end=None):
        self.searchword = searchword
        self.url_news = {}  # 크롤링할 기사들의 URL 을 담을 dict,  일간지 별로 담을 예정
        self.cookies = {
            'news_my_status': '1',  # 반드시 값은 '문자열' 이거나 byte-like string 이어야 한다
            'news_office_checked': "1032,1020,1023,1025,1028"  # 5개신문사 (조선, 중앙, 동앙, 한겨레, 경향)
        }
        self.header = {
            "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
        }

        # 검색종료일
        if not day_end:
            self.day_end = datetime.datetime.now()  # 디폴트로 '오늘' 이 검색 종료일
        else:
            self.day_end = datetime.datetime.strptime(day_end, '%Y-%m-%d')

        # 검색시작일
        if not day_start:
            self.day_start = self.day_end - datetime.timedelta(days=30)  # 디폴트 : 종료일기준 30일 전이 검색 시작일로
        else:
            self.day_start = datetime.datetime.strptime(day_start, '%Y-%m-%d')

        # 신문사별 로 담을 기사 dict
        self.news_article = {}

    # 기사출처 (source_text)를 받으면 해당 언론사 key 값 리턴
    def getsource(self, source_text):
        for key in Name_News:
            if Name_News[key] in source_text:
                return key  # 분류는 key 값으로 할것이다.   ('chosun', 'donga', ...)

    # 신문사별로 news url 담기
    def add_news_url(self, source_key, url):
        if source_key not in self.url_news: self.url_news[source_key] = []  # 신문사별 key
        if url not in self.url_news[source_key]:  # 중복되는 url 은 배제
            self.url_news[source_key].append(url)

    # 페이징 하면 url 읽어오기
    def read_page_url(self, start):
        # 검색어(searchword) 와 페이지 표시할 기사 시작 번호(start) 를 사용하여 페이지의 url 문자열 만들기
        page_url = NaverNews.Page_Url.format(keyword=parse.quote(self.searchword), start=start,
                                             ds1=self.day_start.strftime('%Y.%m.%d'),
                                             de1=self.day_end.strftime('%Y.%m.%d'),
                                             ds2=self.day_start.strftime('%Y%m%d'), de2=self.day_end.strftime('%Y%m%d'))
        self.header['referer'] = page_url  # 위 페이지 url 을 heeader 정보 referer 에 담아야 크롤링이 된다.

        # 페이지 요청 (request) 고 파싱
        response = requests.get(page_url, cookies=self.cookies, headers=self.header)
        dom = BeautifulSoup(response.text, "lxml")

        # 상단 페이징 정보 출력
        print(dom.select_one("div.title_desc.all_my > span").text)

        news_list = dom.select("#main_pack > div.news.mynews.section._prs_nws > ul > li")

        for news in news_list:
            title = news.select_one("dl > dt > a").text.strip()

            # '네이버뉴스 url' 을 가져와야 한다    (언론사 url 이 아니라)
            news_url = news.select_one("dl > dd.txt_inline > a._sp_each_url").attrs['href'].strip()

            source = news.select_one("dl > dd.txt_inline > span._sp_each_source").text.strip()

            # 언론사 출처
            source_key = self.getsource(source)

            #         print(source, source_key)
            #       print(title, news_url, source_key, source)

            # 신문사별 뉴스 url 들 만들기
            self.add_news_url(source_key, news_url)

        # 다음 페이지 여부 체크
        if dom.select_one("div.paging > a.next"):
            return True
        else:
            return False

    # 모든 기사에 대한 url 수집
    def read_all_page_url(self, article_num, page_articles):
        print("검색어:", self.searchword)
        print("검색기간:", self.day_start.strftime('%Y-%m-%d'), "~", self.day_end.strftime('%Y-%m-%d'))
        print("기사 URL 을 수집합니다...")

        while True:
            result = self.read_page_url(article_num)  # 한 페이지 url
            if not result: break  # 더이상 페
            article_num += page_articles

    #  특정 url 의 기사 본문 읽어 들이기,  전처리 포함
    def get_article(self, url):
        print("기사 CRAWLING:", url)

        # Obtain three types of information about a news article
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'lxml')

        # <script> <style> 제거 (전처리)
        for s in soup(['script', 'style']):
            s.decompose()

        # 뉴스제목, 제공자, 뉴스본문
        # news_title = soup.title.text.strip()
        # publisher = soup.find('meta', attrs={'name':'twitter:creator'}).get('content').strip()

        news_content = soup.find('div', attrs={'id': 'articleBodyContents'})  # 일반 뉴스
        if not news_content: news_content = soup.find('div', attrs={'id': 'articeBody'})  # 연예 뉴스  (심지어 id 오타까지...)
        if not news_content: news_content = soup.find('div', attrs={'id': 'newsEndContents'})  # 스포츠 뉴스

        #     print("news_content:", news_content)

        # 뉴스본문에 대한 전처리
        # 각 line별 strip()
        lines = [
            line.strip()
            for line in news_content.get_text().splitlines()
        ]
        news_content = ''.join(lines)

        # 구두점 제거    (. 마침표는 그대로 둠)
        news_content = news_content.replace(',', ' '). \
            replace("'", " ").replace('·', ' ').replace('=', ' ').replace('\t', ' ').replace('\"', '')

        # 제거 패턴
        for ex_word in Except_Words:
            news_content = re.sub(ex_word, '', news_content)

        # 치환 패턴
        for other_word in Other_Words1:
            news_content = re.sub(other_word, '', news_content)

        # return news_title, publisher, news_content
        return news_content

    # 수집한 기사 URL 의 모든 기사 본문들을 읽어 들인다.
    def get_all_articles(self):
        count_article = 0  # 몇개의 기사 읽어 들였는지 카운트
        for newspaper in self.url_news:
            print(Name_News[newspaper])  # 어느 신문사의 뉴스 인지 출력
            url_list = self.url_news[newspaper]
            for url in url_list:  # 그 신문사의 뉴스들의 url 들을 하나하나 끄집어 내어 크롤링 시작.
                if not newspaper in self.news_article: self.news_article[newspaper] = []
                self.news_article[newspaper].append(self.get_article(url))
                count_article += 1

        # 다 크롤링 한후 몇개의 기사를 읽어 들였는지 출력
        print("─" * 30)
        print("읽은 기사 개수: ", count_article)

    #
    def analyze_article(self):
        twitter = konlpy.tag.Twitter()  # Twitter 어휘소 분석기

        print("품사별 단어 분석 시작...")
        for newspaper in self.news_article:

            # '신문사별'  기사들 뭉치기
            article = "".join(self.news_article[newspaper])

            # 기사의 어휘소 분석
            twitter_morphs = twitter.pos(article)

            #     print(newspaper)
            #     print(twitter_morphs)

            # 품사별 분리
            for pos in Name_Pos:  # "Noun", "Adjective", "Verb"   검색할 품사들

                print(Name_News[newspaper], Name_Pos[pos])

                pos_words = []

                for mal in twitter_morphs:  # mal <= (단어, 품사)
                    # 찾고자 하는 품사이고   길이가 1개 보다 큰 단어들, StopWords 에 포함되지 않은 단어들만 필터링
                    if pos == mal[1] and len(mal[0]) > 1 and (mal[0] not in Stop_Words):
                        pos_words.append(mal[0])  # 단어 추가

                pos_counter = Counter(pos_words)  # 해당 품사의 단어 빈도수 파악

                # print(pos_counter)
                # print(pos_counter.most_common(20))

                # 그래프 작성을 위해 DaraFrame 만들기
                df_freq = pd.DataFrame(columns=["word", "count"])

                for freq_words in pos_counter.most_common(20):  # 최다 빈도수 상위 20개만 추출
                    # for freq_words in pos_counter:
                    df_freq.loc[len(df_freq)] = (freq_words[0], freq_words[1])

                df_freq = df_freq.set_index("word")  # 기존의 index 없애고 word 컬럼을 index로 변경
                df_freq.to_excel(Name_News[newspaper] + "_" + Name_Pos[pos] + ".xlsx", encoding="euc-kr")  # 엑셀 저장

                # 그래프 작성
                plt.rcParams["figure.figsize"] = (14, 5)  # 그래프의 가로 세로 사이즈

                ax = df_freq.plot(kind="bar")
                ax.set_ylim(0, df_freq['count'][0] + 10)  # y축 값 범위,  실제 출력되는 값 보고 조정해야함
                ax.set_title(Name_News[newspaper] + " " + Name_Pos[pos])  # 그래프 제목 : 신문사명 + 품사명
                ax.set_xlabel("")
                ax.set_ylabel("빈도수")
                ax.legend().set_visible(False)  # 범례없애기

                for i in ax.patches:  # 그래프에 해당 숫자 값 표시
                    ax.text(
                        i.get_x() - .08,  # 표시 x좌표
                        i.get_height() + .5,  # 표시 y좌표
                        i.get_height(),  # 표시할 값
                        fontsize=12,
                        color='black'
                    )

                # 그래프를 이미지 파일로 저장.  파일명  ;  신문사명_품사명.png
                ax.get_figure().savefig(Name_News[newspaper] + "_" + Name_Pos[pos] + ".png", dpi=200)





