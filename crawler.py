from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import datetime
import httpx
import os
from urllib import parse
import asyncio
from bs4 import BeautifulSoup
import markdownify

mcp = FastMCP("crawler")


async def _start(data_url,
            data_headers):
    try:

        # async with aiohttp.ClientSession() as session:
        #     today_yyyymm = datetime.datetime.today().strftime("%Y%m") 
        #     data_params = {
        #         "reqData": {
        #             "inqirePd": today_yyyymm
        #             }
        #     }
        
        #     async with session.post(data_url, json=data_params, headers=data_headers) as response:
        #         response.raise_for_status()
        #         response_data = await response.json()
        #         return response_data['schdulList']

        today_yyyymm = datetime.datetime.today().strftime("%Y%m")
        data_params = {
            "reqData": {
                "inqirePd": today_yyyymm
            }
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(data_url, json=data_params, headers=data_headers)
            response.raise_for_status()
            response_data = response.json()
            return response_data['schdulList']

    except Exception as e:
        return f"예상치 못한 오류 발생: {e}"

async def _transform_address(jiyeok: str) -> list:
    client_id = os.environ.get('X_NCP_APIGW_API_KEY_ID')
    client_pw = os.environ.get('X_NCP_APIGW_API_KEY')
    naver_map_api_url = 'https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode?query='

    add_lists = await _address_api(jiyeok)
    result = set()

    headers = {
        'X-NCP-APIGW-API-KEY-ID': client_id,
        'X-NCP-APIGW-API-KEY': client_pw
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for add in add_lists:
                add_urlenc = parse.quote(add)
                url = naver_map_api_url + add_urlenc

                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                response_body = resp.json()

                if response_body.get('addresses'):
                    sido = response_body['addresses'][0]['addressElements'][0]['shortName']
                    result.add(sido)
        return list(result)

    except Exception as e:
        return f"예상치 못한 오류 발생: {e}"


async def _address_api(keyword,
                    **kwargs):
    urls = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
    confmKey = os.environ.get('JUSO_API_KEY') # 필수 값 승인키
    
    params = {
        'keyword': keyword,
        'confmKey': confmKey,
        'resultType': 'json'
    }
    
    if kwargs: # 필수 값이 아닌 변수를 params에 추가
        for key, value in kwargs.items():
            params[key] = value
    params_str = parse.urlencode(params) # dict를 파라미터에 맞는 포맷으로 변경
    
    url = '{}?{}'.format(urls, params_str)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(urls, params=params)
            response.raise_for_status()
            result = response.json()

            status = result['results']['common']['errorMessage']
            roadAddr_list = []

            if status == '정상':
                for juso in result['results']['juso']:
                    roadAddr_list.append(juso['jibunAddr'])

            return list(set(roadAddr_list))

    except Exception as e:
        return f"예상치 못한 오류 발생: {e}"

def _filtering(
    house_type: list,
    jiyeok: str,
    data_list: list
) -> list:
    new_data_list = []
    for data in data_list:
        # 집 필터 / 지역 필터
        if house_type and jiyeok:
            if data['SUBSCRPT_AREA_CODE_NM'] in jiyeok and data['HOUSE_SECD'] in house_type:
                new_data_list.append(data)
        # 집은 필터 / 지역은 전체
        elif house_type and not jiyeok:
            if data['HOUSE_SECD'] in house_type:
                new_data_list.append(data)
        # 집은 전체 / 지역은 필터
        elif not house_type and jiyeok:
            if data['SUBSCRPT_AREA_CODE_NM'] in jiyeok:
                new_data_list.append(data)
        # 집과 지역 전체
        else:
            new_data_list.append(data)

    return new_data_list

def _parsing_data(data):
    result = {
        "title": data["HOUSE_NM"],
        "jiyeok": data["SUBSCRPT_AREA_CODE_NM"],
        "date": data["IN_DATE"],
        "house_manage_code": data["HOUSE_MANAGE_NO"],
        "house_pblanc_code": data["PBLANC_NO"],
        "house_secd": data["HOUSE_SECD"]
    }
    
    return result

async def _post_handler(data, info_url):
    extract_data = _parsing_data(data)
    # 파일 이름
    file_name = f'{extract_data["title"]}_{extract_data["jiyeok"]}_{extract_data["date"]}.pdf'
    
    # 세부내용 url로 데이터 post
    detail_params = {
        "houseManageNo": extract_data["house_manage_code"],
        "pblancNo": extract_data["house_pblanc_code"],
        "houseSecd": extract_data["house_secd"],
        "gvPgmId": "AIB01M01"
    }
    detail_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    }
    
    if extract_data["house_secd"] == "01" or extract_data["house_secd"] == "09":
        detail_url = info_url[0]
    elif extract_data["house_secd"] == "04" or extract_data["house_secd"] == "06" or extract_data["house_secd"] == "11":
        detail_url = info_url[1]
    else:
        detail_url = info_url[2]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(detail_url, data=detail_params, headers=detail_headers)
            response.raise_for_status()
            html_content = response.text
            md_content = markdownify.markdownify(html_content)
            
            soup = BeautifulSoup(html_content, 'html.parser')
            link_tag = soup.find("a", class_="radius_btn")
            down_link = link_tag.get("href") if link_tag else None
            
            return {
                "data_hmno": extract_data,
                "md_content": md_content,
                "pdf_url": down_link
            }

    except Exception as e:
        return f"예상치 못한 오류 발생: {e}"

@mcp.tool(
  name="get_result",
  description="대한민국의 아파트의 청약, 민간사전청약아파트, 민간임대오피스텔 등의 정보를 수집할 수 있는 tool입니다."
)
async def get_result(
    # user_query:str,
    house_type:str,
    jiyeok:str):
    """
    대한민국의 아파트의 청약, 민간사전청약아파트, 민간임대오피스텔 등의 정보를 수집할 수 있는 tool입니다.

    Args:
        house_type: 아파트, 민간사전청약아파트, 민간임대오피스텔, 공공지원민간임대 중 선택합니다. 특정 유형을 선택할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "아파트", "민간사전청약아파트", "민간임대오피스텔", "공공지원민간임대")
        jiyeok: 지역 이름을 추출합니다. 특정 지역을 추출할 수 없다면 '전체'를 선택하세요. (e.g. "전체", "서울특별시", "대구광역시", "전라남도", "부산광역시")
    """

    load_dotenv()       # tool 호출했을 때 환경변수 Load

    info_url: list = [
        "https://www.applyhome.co.kr/ai/aia/selectAPTLttotPblancDetail.do", # se : 01 or 09
        "https://www.applyhome.co.kr/ai/aia/selectAPTRemndrLttotPblancDetailView.do", # se : 04 or 06 or 11
        "https://www.applyhome.co.kr/ai/aia/selectPRMOLttotPblancDetailView.do"
    ]
    
    data_headers: dict[str, str] = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    }

    data_url: str = "https://www.applyhome.co.kr/ai/aib/selectSubscrptCalender.do"

    type_keys: dict[str, list] = {
        "아파트": ["01","02", "03", "06", "07", "11"],
        "민간사전청약아파트": ["08", "09", "10"],
        "민간임대오피스텔": ["05"],
        "공공지원민간임대": ["04"],
    }

    jiyeok_keys: dict[str, list] = {
        "서울특별시": ["서울"],
        "광주광역시": ["광주"],
        "대구광역시": ["대구"],
        "대전광역시": ["대전"],
        "부산광역시": ["부산"],
        "세종특별자치시": ["세종"],
        "울산광역시": ["울산"],
        "인천광역시": ["인천"],

        "강원특별자치도": ["강원"],
        "경기도": ["경기"],
        "경상남도": ["경남"],
        "경상북도": ["경북"],
        "전라남도": ["전남"],
        "전라북도": ["전북"],
        "제주특별자치도": ["제주"],
        "충청남도": ["충남"],
        "충청북도": ["충북"],
    }

    enum_jiyeok : str = "서울 광주 대구 대전 부산 세종 울산 인천 강원 경기 경북 \
        경남 전남 전북 제주 충남 충북"

    data_list = await _start(data_url,
                       data_headers)

    house_type_list = []
    jiyeok_list = []
    
    if jiyeok in enum_jiyeok:
        jiyeok_list = [jiyeok]
    else:
        jiyeok = await _transform_address(jiyeok=jiyeok)        
    
    if house_type != "전체":
        h_type_key = type_keys[house_type]
        house_type_list.extend(h_type_key)
    if jiyeok != "전체" and not jiyeok_list:
        for sido in jiyeok: 
            jiyeok_key = jiyeok_keys[sido]
            jiyeok_list.extend(jiyeok_key)

    data_list = _filtering(house_type=house_type_list,
                                jiyeok=jiyeok_list,
                                data_list=data_list)

    posts = await asyncio.gather(
        *[_post_handler(data, info_url) for data in data_list]
    )

    return posts

if __name__ == "__main__":
    print("MCP Server Start")
    mcp.run("stdio")